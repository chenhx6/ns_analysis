#include "peakfinder.hh"
#include <algorithm>
#include <cmath>
#include <map>
#include <set>
#include <sstream>
#include <iostream>
#include "TSpectrum.h"
#include "TFitResult.h"
#include "TMath.h"
#include "TList.h"

std::vector<PeakCandidate> PeakFinder::SearchCandidates(const TH1D& h) const {
    std::vector<PeakCandidate> found;
    const double raw_bin_width = h.GetBinWidth(1);

    // Search on temporary, non-overlapping rebinnings so broad scintillator
    // peaks are visible while the saved fitting spectrum remains one evte/bin.
    for (int factor : User::CandidateRebins) {
        if (factor < 1 || h.GetNbinsX() % factor != 0) continue;
        auto base = std::unique_ptr<TH1D>(static_cast<TH1D*>(h.Clone("search_base")));
        base->SetDirectory(nullptr);
        std::unique_ptr<TH1D> search;
        if (factor == 1) {
            search = std::move(base);
        } else {
            auto* rebinned = dynamic_cast<TH1D*>(base->Rebin(factor, "search_rebinned"));
            if (!rebinned) continue;
            search.reset(rebinned);
            search->SetDirectory(nullptr);
        }
        search->GetXaxis()->SetRangeUser(User::NoiseCutoffADC, 65535.0);
        if (factor == 1) search->Smooth(1);

        const double search_width = factor == 1 ? 4.0 : 3.0;
        TSpectrum spectrum(100);
        int n = spectrum.Search(search.get(), search_width, "goff nodraw", User::SearchThreshold);
        for (int i = 0; i < n; ++i) {
            double x = spectrum.GetPositionX()[i];
            if (x < User::NoiseCutoffADC || x > 65500.) continue;
            int bin = h.GetXaxis()->FindFixBin(x);
            double height = h.GetBinContent(bin);
            int distance = std::max(2, int(3 * search_width * search->GetBinWidth(1) / raw_bin_width));
            double bg = (h.GetBinContent(std::max(1, bin - distance)) +
                         h.GetBinContent(std::min(h.GetNbinsX(), bin + distance))) / 2.;
            if (height < User::MinPeakCounts) continue;
            double significance = (height - bg) / std::sqrt(std::max(1., height + bg));
            if (significance < User::MinProminenceSigma) continue;

            const double candidate_sigma = std::max(raw_bin_width,
                search_width * search->GetBinWidth(1) * 0.5);
            const double merge_tolerance = std::max(3.0 * raw_bin_width,
                search_width * search->GetBinWidth(1) * 0.7);
            bool duplicate = false;
            for (const auto& p : found) {
                if (std::abs(p.x - x) < merge_tolerance) {
                    duplicate = true;
                    break;
                }
            }
            if (!duplicate) found.push_back({x, height, candidate_sigma});
        }
    }
    std::sort(found.begin(), found.end(), [](auto a, auto b) { return a.height > b.height; });
    if (found.size() > User::MaxCandidates) found.resize(User::MaxCandidates);
    std::sort(found.begin(), found.end(), [](auto a, auto b) { return a.x < b.x; });
    return found;
}

// Strict double-anchor matching to protect the physical linearity of HPGe channels
MatchResult PeakFinder::Match(const std::vector<PeakCandidate>& c, const std::vector<SourceLine>& refs) const {
    MatchResult out;
    out.reason = "fewer than 3 distinct candidates or references";
    if (c.size() < 3 || refs.size() < 3) return out;

    std::map<std::vector<std::pair<int,int>>, MatchResult> hypotheses;

    for (size_t i = 0; i < c.size(); ++i) {
        for (size_t j = i + 1; j < c.size(); ++j) {
            double dx = c[j].x - c[i].x;
            if (dx < 50.) continue;
            for (size_t r = 0; r < refs.size(); ++r) {
                for (size_t s = r + 1; s < refs.size(); ++s) {
                    double de = refs[s].energy - refs[r].energy;
                    if (de < User::MinAnchorSpan_keV) continue;
                    MatchResult t;
                    t.gain = de / dx;
                    t.offset = refs[r].energy - t.gain * c[i].x;
                    if (t.gain < User::MinGain || t.gain > User::MaxGain || std::abs(t.offset) > User::MaxOffset_keV) continue;

                    int last = -1;
                    double sq = 0.;
                    for (size_t k = 0; k < refs.size(); ++k) {
                        double expected = (refs[k].energy - t.offset) / t.gain;
                        auto pos = std::lower_bound(c.begin(), c.end(), expected, [](auto p, double x) { return p.x < x; });
                        int idx = int(pos - c.begin());
                        if (idx == int(c.size()) || (idx > 0 && std::abs(c[idx-1].x - expected) < std::abs(c[idx].x - expected))) --idx;
                        if (idx <= last) continue;
                        double d = std::abs(t.offset + t.gain * c[idx].x - refs[k].energy);
                        // Strict linear matching tolerance (default 3.0 keV)
                        if (d > User::MatchTolerance_keV) continue;
                        t.pairs.emplace_back(k, idx);
                        last = idx;
                        sq += d * d;
                    }
                    if (t.pairs.size() < 3) continue;
                    t.rms = std::sqrt(sq / t.pairs.size());
                    t.valid = true;
                    auto it = hypotheses.find(t.pairs);
                    if (it == hypotheses.end() || t.rms < it->second.rms) hypotheses[t.pairs] = t;
                }
            }
        }
    }

    // Special fallback ONLY for channels with strong hardware curvature (0-3-6):
    // If standard linear matching only covers low energy (<500 keV), but strong peaks exist at high ADC (>2500)
    bool needs_nonlinear_fallback = false;
    if (!hypotheses.empty()) {
        std::vector<MatchResult> temp_ranked;
        for (const auto& h : hypotheses) temp_ranked.push_back(h.second);
        std::sort(temp_ranked.begin(), temp_ranked.end(), [](const auto& a, const auto& b) {
            return a.pairs.size() != b.pairs.size() ? a.pairs.size() > b.pairs.size() : a.rms < b.rms;
        });
        const auto& best_temp = temp_ranked.front();
        double max_e = 0.;
        for (auto p : best_temp.pairs) max_e = std::max(max_e, refs[p.first].energy);
        double max_cand_x = c.back().x;
        if (max_e <= 500.0 && max_cand_x > 2600.0 && best_temp.pairs.size() >= 6) {
            needs_nonlinear_fallback = true;
        }
    }

    if (needs_nonlinear_fallback) {
        // Targeted quadratic extension for channels like 0-3-6
        for (auto& hyp_pair : hypotheses) {
            auto& t = hyp_pair.second;
            if (t.pairs.size() < 6) continue;
            // Fit quadratic to low-energy pairs
            double s0 = t.pairs.size(), sx = 0, sx2 = 0, sx3 = 0, sx4 = 0, sy = 0, sxy = 0, sx2y = 0;
            for (auto p : t.pairs) {
                double x = c[p.second].x, y = refs[p.first].energy;
                sx += x; sx2 += x*x; sx3 += x*x*x; sx4 += x*x*x*x;
                sy += y; sxy += x*y; sx2y += x*x*y;
            }
            double m[3][3] = {{s0, sx, sx2}, {sx, sx2, sx3}, {sx2, sx3, sx4}};
            double rhs[3] = {sy, sxy, sx2y};
            for (int col = 0; col < 3; ++col) {
                int pivot = col;
                for (int row = col + 1; row < 3; ++row) if (std::abs(m[row][col]) > std::abs(m[pivot][col])) pivot = row;
                if (pivot != col) { for (int k = 0; k < 3; ++k) std::swap(m[col][k], m[pivot][k]); std::swap(rhs[col], rhs[pivot]); }
                if (std::abs(m[col][col]) < 1e-12) continue;
                for (int row = col + 1; row < 3; ++row) {
                    double f = m[row][col] / m[col][col];
                    for (int k = col; k < 3; ++k) m[row][k] -= f * m[col][k];
                    rhs[row] -= f * rhs[col];
                }
            }
            double b2 = rhs[2] / m[2][2];
            double b1 = (rhs[1] - m[1][2] * b2) / m[1][1];
            double b0 = (rhs[0] - m[0][1] * b1 - m[0][2] * b2) / m[0][0];

            if (b1 + 2 * b2 * c.front().x > 0.05 && b1 + 2 * b2 * c.back().x > 0.05) {
                std::vector<std::pair<int,int>> ext_pairs = t.pairs;
                int last_cand = ext_pairs.back().second;
                for (size_t ref_idx = 0; ref_idx < refs.size(); ++ref_idx) {
                    if (refs[ref_idx].energy <= 500.0) continue;
                    double E_target = refs[ref_idx].energy;
                    double disc = b1 * b1 - 4 * b2 * (b0 - E_target);
                    if (disc < 0) continue;
                    double x_pred = (std::abs(b2) > 1e-9) ? (-b1 + std::sqrt(disc)) / (2 * b2) : (E_target - b0) / b1;
                    if (x_pred <= 0) continue;
                    auto pos = std::lower_bound(c.begin(), c.end(), x_pred, [](auto p, double x) { return p.x < x; });
                    int idx = int(pos - c.begin());
                    if (idx == int(c.size()) || (idx > 0 && std::abs(c[idx-1].x - x_pred) < std::abs(c[idx].x - x_pred))) --idx;
                    if (idx <= last_cand) continue;
                    double e_calc = b0 + b1 * c[idx].x + b2 * c[idx].x * c[idx].x;
                    if (std::abs(e_calc - E_target) < 35.0) {
                        ext_pairs.emplace_back(ref_idx, idx);
                        last_cand = idx;
                    }
                }
                if (ext_pairs.size() > t.pairs.size()) {
                    t.pairs = ext_pairs;
                }
            }
        }
    }

    out.reason = "no consistent mapping within configured bounds";
    if (hypotheses.empty()) return out;

    std::vector<MatchResult> ranked;
    for (const auto& h : hypotheses) ranked.push_back(h.second);
    std::sort(ranked.begin(), ranked.end(), [](const auto& a, const auto& b) {
        return a.pairs.size() != b.pairs.size() ? a.pairs.size() > b.pairs.size() : a.rms < b.rms;
    });

    out = ranked.front();
    out.reason = "unique leading coarse mapping";

    for (size_t i = 1; i < ranked.size(); ++i) {
        const auto& alt = ranked[i];
        if (alt.pairs.size() < out.pairs.size()) break;
        int common = 0;
        for (auto p : out.pairs) common += std::count(alt.pairs.begin(), alt.pairs.end(), p);
        bool different = std::abs(alt.gain / out.gain - 1.) > 0.15 || common < int(0.5 * out.pairs.size());
        if (different && alt.rms <= out.rms + 0.5) {
            out.ambiguous = true;
            std::ostringstream why;
            why << "competing mapping: " << out.pairs.size() << " vs " << alt.pairs.size()
                << " points; gains " << out.gain << " vs " << alt.gain << " keV/ADC";
            out.reason = why.str();
            break;
        }
    }
    return out;
}

std::vector<FittedPeak> PeakFinder::Fit(TH1D& h, const std::vector<PeakCandidate>& c,
                                       const std::vector<SourceLine>& refs, const MatchResult& m) const {
    std::vector<FittedPeak> out;
    int index = 0;
    double bin_w = h.GetBinWidth(1);

    for (auto pair : m.pairs) {
        const auto& line = refs[pair.first];
        const auto& candidate = c[pair.second];
        FittedPeak p;
        p.index = ++index;
        p.ref_E = line.energy;
        p.ref_err = line.error;
        p.function = "peak_" + std::to_string(p.index);
        double x = candidate.x;

        int b = h.FindBin(x);
        int distance = std::max(8, int(4 * candidate.sigma / bin_w));
        double bg = 0.5 * (h.GetBinContent(std::max(1, b - distance)) +
                          h.GetBinContent(std::min(h.GetNbinsX(), b + distance)));
        double amplitude = std::max(1., h.GetBinContent(b) - bg);
        double half = bg + 0.5 * amplitude;
        int left = b, right = b;
        while (left > std::max(1, b - distance) && h.GetBinContent(left) > half) --left;
        while (right < std::min(h.GetNbinsX(), b + distance) && h.GetBinContent(right) > half) ++right;
        double sigma = std::max(1.0 * bin_w, (right - left) * bin_w / 2.354820045);

        double lo = x - User::FitWindowSigma * sigma;
        double hi = x + User::FitWindowSigma * sigma;
        if (pair.second > 0) lo = std::max(lo, 0.5 * (x + c[pair.second - 1].x));
        if (pair.second + 1 < int(c.size())) hi = std::min(hi, 0.5 * (x + c[pair.second + 1].x));

        int b1 = std::max(1, h.FindBin(std::max(0.5, lo)));
        int b2 = std::min(h.GetNbinsX(), h.FindBin(std::min(65535.0, hi)));
        p.xmin = h.GetBinLowEdge(b1);
        p.xmax = h.GetBinLowEdge(b2 + 1);

        if (b2 - b1 + 1 < 5) {
            p.reason = "too few bins for peak model";
            out.push_back(p);
            continue;
        }

        std::string formula = "gaus(0)+[3]+[4]*(x-(" + std::to_string(x) + "))";
        TF1 fit(p.function.c_str(), formula.c_str(), p.xmin, p.xmax);
        fit.SetParameters(amplitude, x, sigma, std::max(0.1, bg), 0.);
        fit.SetParLimits(0, 0., std::max(10., 30. * amplitude));
        fit.SetParLimits(1, x - 2.5 * sigma, x + 2.5 * sigma);
        fit.SetParLimits(2, 0.3 * bin_w, std::max(1.5 * bin_w, 4.0 * sigma));

        auto result = h.Fit(&fit, "LIQRSN");
        p.mean = fit.GetParameter(1);
        p.mean_err = fit.GetParError(1);
        p.sigma = fit.GetParameter(2);
        p.reason = "accepted";

        if (int(result) != 0 || !result.Get() || !result->IsValid()) {
            p.reason = "peak minimizer failed (status=" + std::to_string(int(result)) + ")";
        } else if (!std::isfinite(p.mean_err) || p.mean_err <= 0 || p.mean_err > 0.8 * p.sigma ||
                   p.sigma <= 0.3 * bin_w || p.sigma >= 4.0 * sigma || std::abs(p.mean - x) > 2.5 * sigma) {
            p.reason = "unstable centroid/width or parameter at bound";
        } else if (fit.GetParError(0) <= 0 || fit.GetParameter(0) / fit.GetParError(0) < User::MinAreaSignificance) {
            p.reason = "peak amplitude significance insufficient";
        }

        for (double other : line.companions) {
            if (std::abs(other - line.energy) < 2.5 * p.sigma * m.gain) {
                p.reason = "unresolved neighbouring companion line";
            }
        }

        p.used = (p.reason == "accepted");
        fit.SetTitle((std::to_string(line.energy) + " keV; " + p.reason).c_str());
        fit.SetLineColor(p.used ? kRed + 1 : kOrange + 7);
        fit.SetLineStyle(p.used ? 1 : 2);
        fit.SetLineWidth(2);
        fit.SetBit(TF1::kNotDraw, false);
        h.GetListOfFunctions()->Add(fit.Clone());
        out.push_back(p);
    }
    return out;
}
