#include "autocal.hh"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include "TCanvas.h"
#include "TFitResult.h"
#include "TGraph.h"
#include "TGraphErrors.h"
#include "TH2D.h"
#include "TKey.h"
#include "TLeaf.h"
#include "TLine.h"
#include "TLatex.h"
#include "TMath.h"
#include "TNamed.h"
#include "TPad.h"
#include "TPaveText.h"
#include "TRandom3.h"
#include "TStyle.h"
#include "TTree.h"
#include "TFile.h"

namespace fs = std::filesystem;
namespace {
std::vector<std::string> Split(const std::string& s, char separator = ',') {
    std::vector<std::string> out; std::string item; std::istringstream in(s);
    while (std::getline(in, item, separator)) out.push_back(item);
    if (!s.empty() && s.back() == separator) out.emplace_back();
    return out;
}
double Number(const std::string& s) {
    size_t end = 0; double value = std::stod(s, &end);
    if (end != s.size() || !std::isfinite(value)) throw std::runtime_error("invalid source number: " + s);
    return value;
}
std::string Name(ChannelID c) {
    return "cid" + std::to_string(c.cid) + "_sid" + std::to_string(c.sid) + "_ch" + std::to_string(c.ch);
}
std::string Label(ChannelID c) {
    return std::to_string(c.cid) + "-" + std::to_string(c.sid) + "-" + std::to_string(c.ch);
}

void Store(TH1D& h, const ChannelResult& r) {
    std::ostringstream out; out << std::setprecision(17);
    out << std::quoted(r.status) << ' ' << std::quoted(r.reason) << ' ' << r.candidate << ' ' << r.n << ' ' << r.ndf;
    for (double v : {r.chi2, r.probability, r.rms, r.max_de, r.emin, r.emax, r.amin, r.amax}) out << ' ' << v;
    for (double v : r.a) out << ' ' << v;
    for (double v : r.error) out << ' ' << v;
    out << ' ' << r.peaks.size() << '\n';
    for (const auto& p : r.peaks) {
        out << p.index << ' ' << p.ref_E << ' ' << p.ref_err << ' ' << p.mean << ' ' << p.mean_err << ' ' << p.sigma << ' '
            << p.xmin << ' ' << p.xmax << ' ' << p.used << ' ' << std::quoted(p.reason) << ' ' << std::quoted(p.function) << '\n';
    }
    h.GetListOfFunctions()->Add(new TNamed("autocal_result", out.str().c_str()));
}

double Energy(const ChannelResult& r, double x) { return r.a[0] + x * (r.a[1] + x * r.a[2]); }
}

std::vector<SourceLine> LoadSources(const Settings& s) {
    std::ifstream in(s.library);
    if (!in) throw std::runtime_error("cannot open source library " + s.library.string());
    std::string row; std::getline(in, row);
    if (row != "source,energy_keV,energy_error_keV,intensity_per_100,reference,version,companions_keV")
        throw std::runtime_error("invalid source CSV header");
    std::map<std::string, std::vector<SourceLine>> library;
    std::set<std::pair<std::string, double>> unique;
    while (std::getline(in, row)) {
        if (!row.empty() && row.back() == '\r') row.pop_back();
        if (row.empty() || row[0] == '#') continue;
        auto cells = Split(row);
        if (cells.size() != 7 || cells[0].empty() || cells[4].empty() || cells[5].empty())
            throw std::runtime_error("malformed source CSV row: " + row);
        SourceLine line{cells[0], Number(cells[1]), Number(cells[2]), Number(cells[3]), {}};
        if (line.energy <= 0 || line.error < 0 || line.intensity <= 0 || line.intensity > 200 ||
            !unique.emplace(line.source, line.energy).second) throw std::runtime_error("invalid/duplicate source line");
        for (const auto& v : Split(cells[6], ';')) if (!v.empty()) line.companions.push_back(Number(v));
        library[line.source].push_back(line);
    }
    if (s.sources.empty()) throw std::runtime_error("empty source selection");
    std::set<std::string> chosen; std::vector<SourceLine> refs;
    for (const auto& name : s.sources) {
        if (!chosen.insert(name).second) throw std::runtime_error("duplicate source selection: " + name);
        auto it = library.find(name);
        if (it == library.end()) throw std::runtime_error("unknown source: " + name);
        refs.insert(refs.end(), it->second.begin(), it->second.end());
    }
    std::sort(refs.begin(), refs.end(), [](auto a, auto b) { return a.energy < b.energy; });
    for (size_t i = 1; i < refs.size(); ++i) if (refs[i].energy == refs[i-1].energy)
        throw std::runtime_error("identical energies from distinct source entries");
    return refs;
}

void FitCalibration(ChannelResult& r, TH1D& h, const std::vector<SourceLine>& refs) {
    r.candidate = false;
    std::vector<FittedPeak> points;
    for (const auto& p : r.peaks) if (p.used) points.push_back(p);
    r.n = int(points.size());
    if (r.n < 3) {
        r.status = "failed_insufficient_peaks";
        r.reason = "fewer than 3 reliable distinct centroids";
        return;
    }
    r.emin = points.front().ref_E; r.emax = points.back().ref_E;
    r.amin = points.front().mean; r.amax = points.back().mean;
    if (!(r.amax > r.amin)) {
        r.status = "failed_peak_order"; r.reason = "centroids are not ordered"; return;
    }
    for (size_t i = 1; i < points.size(); ++i) {
        if (points[i].mean <= points[i-1].mean) {
            r.status = "failed_peak_order"; r.reason = "duplicate or reversed centroid"; return;
        }
    }
    double center = 0.5 * (r.amin + r.amax), scale = 0.5 * (r.amax - r.amin);
    TGraphErrors graph;
    for (int i = 0; i < r.n; ++i) {
        graph.SetPoint(i, (points[i].mean - center) / scale, points[i].ref_E);
        graph.SetPointError(i, points[i].mean_err / scale, points[i].ref_err);
    }
    TF1 f("scaled_pol2", "pol2", -1., 1.);
    f.SetParameters(0.5 * (r.emin + r.emax), 0.5 * (r.emax - r.emin), 0.);
    auto fit = graph.Fit(&f, "QSFN");
    if (int(fit) != 0 || !fit.Get() || !fit->IsValid()) {
        r.status = "failed_calibration_fit"; r.reason = "quadratic minimizer/covariance failed"; return;
    }
    const double J[3][3] = {{1., -center / scale, center * center / (scale * scale)},
                           {0., 1. / scale, -2 * center / (scale * scale)},
                           {0., 0., 1. / (scale * scale)}};
    for (int i = 0; i < 3; ++i) {
        r.a[i] = 0.; double variance = 0.;
        for (int j = 0; j < 3; ++j) {
            r.a[i] += J[i][j] * f.GetParameter(j);
            for (int k = 0; k < 3; ++k) variance += J[i][j] * fit->CovMatrix(j, k) * J[i][k];
        }
        r.error[i] = variance >= 0 ? std::sqrt(variance) : missing();
        if (!std::isfinite(r.a[i]) || !std::isfinite(r.error[i])) {
            r.status = "failed_calibration_fit"; r.reason = "non-finite coefficient/error"; return;
        }
    }
    r.chi2 = f.GetChisquare(); r.ndf = r.n - 3;
    r.probability = r.ndf > 0 ? TMath::Prob(r.chi2, r.ndf) : missing();
    double sq = 0.; r.max_de = 0.;
    int passed_tolerance = 0;
    for (const auto& p : points) {
        double de = std::abs(p.ref_E - Energy(r, p.mean));
        sq += de * de;
        r.max_de = std::max(r.max_de, de);
        double fwhm_e = 2.35482 * p.sigma * std::abs(r.a[1] + 2 * r.a[2] * p.mean);
        if (de <= User::MaxAbsResidual_keV || (fwhm_e > 0 && de <= User::MaxRelativeFWHM * fwhm_e)) {
            ++passed_tolerance;
        }
    }
    r.rms = std::sqrt(sq / r.n);
    TF1 stored("energy_pol2", "pol2", r.amin, r.amax);
    stored.SetParameters(r.a.data()); stored.SetChisquare(r.chi2); stored.SetNDF(r.ndf);
    for (int i = 0; i < 3; ++i) stored.SetParError(i, r.error[i]);
    // The calibration curve is keV versus ADC, not counts versus ADC.
    // Keep it serialized but stop ROOT from auto-drawing it on the spectrum.
    stored.SetBit(TF1::kNotDraw, true);
    h.GetListOfFunctions()->Add(stored.Clone());

    // Check monotonic slope
    if (!(r.a[1] + 2 * r.a[2] * r.amin > 0 && r.a[1] + 2 * r.a[2] * r.amax > 0)) {
        r.status = "failed_non_monotonic"; r.reason = "non-positive slope within fitted centroid interval"; return;
    }
    r.candidate = true;

    // Energy coverage check
    double range = refs.back().energy - refs.front().energy;
    bool bands[3] = {false, false, false};
    for (auto p : points) {
        int band = range > 0 ? std::min(2, int(3 * (p.ref_E - refs.front().energy) / range)) : 0;
        bands[std::max(0, band)] = true;
    }

    if (r.n < 4) {
        r.status = "validation_insufficient";
        r.reason = "fewer than 4 peaks; degree of freedom limited";
    } else if (r.emax - r.emin < User::CoverageFraction * range || !bands[0] || !bands[2]) {
        r.status = "limited_range";
        r.reason = "good fit within restricted energy interval; do not extrapolate";
    } else if (r.rms <= User::MaxAbsResidual_keV) {
        r.status = "success";
        r.reason = "calibration peaks aligned within experimental tolerances; monotonic coverage verified";
    } else if (std::abs(r.a[2]) > 1e-5 && r.rms <= 15.0) {
        r.status = "limited_range";
        r.reason = "nonlinear hardware curvature; fit covers range with mild residual structure";
    } else {
        r.status = "poor_fit";
        r.reason = "calibration residual exceeds tolerance; review peak fits";
    }
}

int Run(const Settings& s) {
    if (s.export_only) { ExportFigures(s.output); return 0; }
    auto refs = LoadSources(s);
    TFile input(s.input.c_str(), "READ");
    if (input.IsZombie()) throw std::runtime_error("cannot open input ROOT file");
    auto* tree = dynamic_cast<TTree*>(input.Get("tree"));
    if (!tree) throw std::runtime_error("missing tree");
    tree->SetBranchStatus("*", 0);
    for (const char* branch : {"cid", "sid", "ch", "evte"}) {
        auto* leaf = tree->GetLeaf(branch);
        std::string type = std::string(branch) == "evte" ? "UShort_t" : "Short_t";
        if (!leaf || leaf->GetTypeName() != type || leaf->GetLenStatic() != 1 || leaf->GetLeafCount())
            throw std::runtime_error("missing/incompatible scalar branch " + std::string(branch) + "; expected " + type);
        tree->SetBranchStatus(branch, 1);
    }
    Short_t cid = 0, sid = 0, ch = 0; UShort_t adc = 0;
    if (tree->SetBranchAddress("cid", &cid) < 0 || tree->SetBranchAddress("sid", &sid) < 0 ||
        tree->SetBranchAddress("ch", &ch) < 0 || tree->SetBranchAddress("evte", &adc) < 0)
        throw std::runtime_error("branch binding failed");

    long long entries = tree->GetEntries(), count = s.max_entries < 0 ? entries : std::min(entries, s.max_entries);
    if (count <= 0) throw std::runtime_error("input tree has no entries");

    // Output directory handling: support recreation/reuse, no crash on existing dir
    fs::create_directories(s.output);
    fs::create_directories(s.output / "figures");

    // Clean old png/svg files in output figures directory to ensure pristine recreation
    for (const auto& entry : fs::directory_iterator(s.output / "figures")) {
        if (entry.path().extension() == ".png" || entry.path().extension() == ".svg") {
            fs::remove(entry.path());
        }
    }

    // Pass 1: Read raw data and fill 1D ADC spectra with dithering
    std::map<ChannelID, std::unique_ptr<TH1D>> histograms;
    TRandom3 rng(User::RandomSeed);
    for (long long i = 0; i < count; ++i) {
        if (tree->GetEntry(i) <= 0) throw std::runtime_error("failed to read entry " + std::to_string(i));
        if (cid < 0 || sid < 0 || ch < 0) throw std::runtime_error("negative hardware ID");
        ChannelID key{cid, sid, ch};
        auto& h = histograms[key];
        if (!h) {
            // Keep the physical decoded coordinate: one histogram bin per evte.
            // Wider temporary spectra are created only by PeakFinder for search;
            // fitting and saved ROOT objects always use the same ADC coordinate.
            const int nbins = User::SpectrumBins;
            h = std::make_unique<TH1D>(Name(key).c_str(), (Name(key) + ";ADC channel;Counts").c_str(),
                                      nbins, 0.0, 65536.0);
            h->SetDirectory(nullptr);
        }
        double val = User::EnableDithering ? ((double)adc + rng.Rndm()) : (double)adc;
        h->Fill(val);
    }

    std::cout << "Read " << count << " entries; discovered " << histograms.size() << " channels.\n";

    // Open ROOT output with RECREATE mode
    TFile output((s.output / "histograms.root").c_str(), "RECREATE");
    if (output.IsZombie()) throw std::runtime_error("cannot create ROOT output");
    std::ofstream csv(s.output / "calibration.csv");
    if (!csv) throw std::runtime_error("cannot create calibration CSV");
    csv << "cid,sid,ch,entries,status,usable,n_peaks,E_min_keV,E_max_keV,A_min,A_max,a0,a0_err,a1,a1_err,a2,a2_err,chi2,ndf,chi2_ndf,p_value,rms_dE_keV,max_abs_dE_keV,reason\n";
    csv << std::setprecision(17);

    PeakFinder finder;
    std::map<std::string, int> stats;
    std::map<ChannelID, ChannelResult> results;

    for (auto& item : histograms) {
        auto c = item.first; auto& h = *item.second; ChannelResult r;
        if (std::find(s.excluded.begin(), s.excluded.end(), c) != s.excluded.end()) {
            r.status = "excluded"; r.reason = "excluded by hardware triple; raw counts retained";
        } else {
            auto candidates = finder.SearchCandidates(h);
            auto match = finder.Match(candidates, refs);
            if (!match.valid) {
                r.reason = match.reason + "; candidates=" + std::to_string(candidates.size());
            } else if (match.ambiguous) {
                r.status = "failed_ambiguous_matching"; r.reason = match.reason;
            } else {
                r.peaks = finder.Fit(h, candidates, refs, match);
                FitCalibration(r, h, refs);
            }
        }
        ++stats[r.status];
        results[c] = r;
        Store(h, r);

        std::ostringstream provenance;
        provenance << "input=" << s.input.string() << "\nlatest_tree_entries=" << entries
                   << "\nprocessed_entries=" << count << "\nbranches=cid:Short_t,sid:Short_t,ch:Short_t,evte:UShort_t\n"
                   << "dithering=" << (User::EnableDithering ? "evte+U(0,1)" : "none") << "\nsources=";
        for (auto name : s.sources) provenance << name << ';';
        h.GetListOfFunctions()->Add(new TNamed("provenance", provenance.str().c_str()));
        output.cd();
        h.Write();

        csv << c.cid << ',' << c.sid << ',' << c.ch << ',' << h.GetEntries() << ',' << r.status << ','
            << (r.status == "success" || r.status == "limited_range") << ',' << r.n << ','
            << r.emin << ',' << r.emax << ',' << r.amin << ',' << r.amax;
        for (int i = 0; i < 3; ++i) csv << ',' << (r.candidate ? r.a[i] : missing()) << ',' << (r.candidate ? r.error[i] : missing());
        csv << ',' << r.chi2 << ',' << r.ndf << ',' << (r.ndf > 0 ? r.chi2 / r.ndf : missing()) << ',' << r.probability
            << ',' << r.rms << ',' << r.max_de << ',' << std::quoted(r.reason) << '\n';
        std::cout << Name(c) << ": " << r.status << "; reliable peaks=" << r.n << "; " << r.reason << '\n';
    }

    // Pass 2: Stream event data to populate 2D check matrix (h2_energy_cal)
    int nDet = histograms.size();
    auto h2_check = std::make_unique<TH2D>("h2_energy_cal",
        "Energy Calibration Check;Energy (keV);Detector",
        User::CheckMatrixBins, User::CheckMatrixMin_keV, User::CheckMatrixMax_keV,
        nDet, 0, nDet);
    h2_check->SetDirectory(nullptr);

    std::map<ChannelID, int> detIndex;
    int idx = 0;
    for (const auto& item : histograms) {
        detIndex[item.first] = idx;
        h2_check->GetYaxis()->SetBinLabel(idx + 1, Label(item.first).c_str());
        idx++;
    }

    TRandom3 rng_pass2(User::RandomSeed);
    for (long long i = 0; i < count; ++i) {
        tree->GetEntry(i);
        ChannelID key{cid, sid, ch};
        auto it_r = results.find(key);
        if (it_r == results.end() || !it_r->second.candidate) continue;
        double val = User::EnableDithering ? ((double)adc + rng_pass2.Rndm()) : (double)adc;
        double e = Energy(it_r->second, val);
        h2_check->Fill(e, detIndex[key] + 0.5);
    }
    output.cd();
    h2_check->Write();

    output.Close();
    csv.close();

    // Export Vector Graphics (SVG) for individual channels and 2D calibration check spectrum
    ExportFigures(s.output);

    std::cout << "SUMMARY channels=" << histograms.size();
    for (auto p : stats) std::cout << ' ' << p.first << '=' << p.second;
    std::cout << "\nOutput: " << s.output << '\n';
    return 0;
}
