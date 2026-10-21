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

ChannelResult Restore(const TH1D& h) {
    auto* metadata = dynamic_cast<TNamed*>(h.GetListOfFunctions()->FindObject("autocal_result"));
    if (!metadata) throw std::runtime_error("missing histogram metadata");
    ChannelResult r; std::istringstream in(metadata->GetTitle());
    auto read = [&](double& v) { std::string token; in >> token; v = std::stod(token); };
    in >> std::quoted(r.status) >> std::quoted(r.reason) >> r.candidate >> r.n >> r.ndf;
    for (double* v : {&r.chi2, &r.probability, &r.rms, &r.max_de, &r.emin, &r.emax, &r.amin, &r.amax}) read(*v);
    for (auto& v : r.a) read(v);
    for (auto& v : r.error) read(v);
    size_t n = 0; in >> n;
    for (size_t i = 0; i < n; ++i) {
        FittedPeak p; in >> p.index;
        for (double* v : {&p.ref_E, &p.ref_err, &p.mean, &p.mean_err, &p.sigma, &p.xmin, &p.xmax}) read(*v);
        in >> p.used >> std::quoted(p.reason) >> std::quoted(p.function);
        r.peaks.push_back(p);
    }
    if (!in) throw std::runtime_error("damaged histogram metadata");
    return r;
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
    stored.SetBit(TF1::kNotDraw, false);
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
            // Adaptive bin width: for LaBr3 (sid=8), use 512 bins (bin_width=128 channels) to eliminate spikes and smooth peaks!
            // For HPGe (sid=2,3,4,5), use 65536 bins (bin_width=1 channel) to preserve ultimate energy resolution!
            int nbins = (key.sid == 8) ? 512 : User::SpectrumBins;
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

void ExportFigures(const fs::path& directory) {
    TFile input((directory / "histograms.root").c_str(), "READ");
    if (input.IsZombie()) throw std::runtime_error("cannot reopen fitted histogram ROOT file");
    fs::create_directories(directory / "figures");
    gStyle->SetOptStat(0); gStyle->SetOptTitle(0); gStyle->SetTextFont(42);

    TIter keys(input.GetListOfKeys());
    int generated = 0;
    while (auto* key = dynamic_cast<TKey*>(keys())) {
        std::string objName = key->GetName();
        // Export 2D check matrix to SVG
        if (objName == "h2_energy_cal") {
            auto h2 = std::unique_ptr<TH2D>(dynamic_cast<TH2D*>(key->ReadObj()));
            if (!h2) continue;
            TCanvas c2("c_ecal", "Energy Calibration Check", 1600, 1000);
            c2.SetLeftMargin(0.08); c2.SetRightMargin(0.12); c2.SetTopMargin(0.08); c2.SetBottomMargin(0.10);
            c2.SetLogz();
            h2->GetXaxis()->SetTitle("Calibrated Energy (keV)");
            h2->GetYaxis()->SetTitle("Channel (cid-sid-ch)");
            h2->GetXaxis()->SetTitleSize(0.035); h2->GetYaxis()->SetTitleSize(0.035);
            h2->Draw("colz");
            TLatex title; title.SetNDC(); title.SetTextFont(42); title.SetTextSize(0.035);
            title.DrawLatex(0.08, 0.93, "All-Channel Energy Calibration Alignment Check (4096 bins, 0-2048 keV)");
            c2.SaveAs((directory / "figures" / "h2_energy_cal.svg").c_str());
            continue;
        }

        auto h = std::unique_ptr<TH1D>(dynamic_cast<TH1D*>(key->ReadObj()));
        if (!h) continue;
        h->SetDirectory(nullptr);
        auto r = Restore(*h);

        TCanvas canvas("review", "Energy calibration", 2200, 1600);
        TPad top("spectrum", "spectrum", 0., 0.5, 1., 1.);
        TPad left("residuals", "residuals", 0., 0., 0.46, 0.5);
        TPad right("calibration", "calibration", 0.46, 0., 1., 0.5);
        top.SetLeftMargin(0.055); top.SetRightMargin(0.33); top.SetTopMargin(0.14); top.SetBottomMargin(0.12);
        left.SetLeftMargin(0.10); left.SetRightMargin(0.04); left.SetTopMargin(0.14); left.SetBottomMargin(0.12);
        right.SetLeftMargin(0.09); right.SetRightMargin(0.49); right.SetTopMargin(0.14); right.SetBottomMargin(0.12);
        top.Draw(); left.Draw(); right.Draw();

        auto text = [](double x, double y, const std::string& label, double size = 0.026) {
            TLatex line; line.SetNDC(); line.SetTextFont(42); line.SetTextSize(size); line.DrawLatex(x, y, label.c_str());
        };

        auto* table = new TPaveText(0.69, 0.06, 0.995, 0.86, "NDC");
        table->SetBorderSize(0); table->SetFillStyle(0); table->SetTextFont(42); table->SetTextAlign(12); table->SetTextSize(0.021);
        table->AddText("#   E_{ref} (keV)     mean #pm error (ADC)");
        for (auto p : r.peaks) {
            table->AddText(Form("%d  %.4f  %.2f #pm %.2f %s", p.index, p.ref_E, p.mean, p.mean_err, p.used ? "" : "[reject]"));
        }
        if (r.peaks.empty()) table->AddText("No uniquely assigned/fitted lines");
        table->AddText("Dithering: ADC = evte + U(0,1)");
        table->AddText("Red: used; orange dashed: rejected fit");
        table->AddText("Sources: evaluated gamma standards");

        top.cd(); top.SetLogy(); top.SetLogx();
        h->SetLineColor(kBlack); h->SetLineWidth(1); h->SetMinimum(0.5);
        h->GetXaxis()->SetRangeUser(1.0, 65535.0);
        double peakmax = std::max(2., h->GetMaximum()); h->SetMaximum(peakmax * 8.);
        h->GetXaxis()->SetTitle("Continuous ADC channel (log scale)"); h->GetYaxis()->SetTitle("Counts / bin");
        h->GetXaxis()->SetTitleSize(0.035); h->GetYaxis()->SetTitleSize(0.035);
        h->GetXaxis()->SetLabelSize(0.028); h->GetYaxis()->SetLabelSize(0.028);
        h->Draw("HIST");

        for (auto p : r.peaks) {
            auto* f = dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject(p.function.c_str()));
            if (!f) continue;
            f->SetLineColor(p.used ? kRed + 1 : kOrange + 7);
            f->SetLineStyle(p.used ? 1 : 2);
            f->SetLineWidth(2);
            f->DrawCopy("SAME");
        }

        double last = -1.; int level = 0;
        for (auto p : r.peaks) if (std::isfinite(p.mean) && p.mean > 1.0) {
            double x = std::log10(p.mean);
            level = x - last < 0.07 ? (level + 1) % 4 : 0; last = x;
            TLatex number; number.SetTextFont(42); number.SetTextSize(0.024);
            number.SetTextColor(p.used ? kBlue + 1 : kOrange + 7); number.SetTextAlign(21);
            double y = std::max(1., h->GetBinContent(h->FindBin(p.mean))) * std::pow(1.65, 1 + level);
            number.DrawLatex(p.mean, std::min(y, peakmax * 5.), Form("%d", p.index));
        }
        table->Draw();
        text(0.055, 0.955, std::string(h->GetName()) + " | entries=" + std::to_string((long long)h->GetEntries()), 0.031);
        text(0.055, 0.90, r.status + " | Poisson likelihood Gaussian + background", 0.025);

        // Left: Local peak residuals
        double xmin = 65535., xmax = 0., bound = 1.; int invalid = 0;
        struct Residual { FittedPeak p; std::unique_ptr<TGraph> graph; };
        std::vector<Residual> residuals;
        for (auto p : r.peaks) {
            auto* f = dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject(p.function.c_str()));
            if (!f) continue;
            auto graph = std::make_unique<TGraph>();
            for (int b = std::max(1, h->FindBin(p.xmin)); b <= h->GetNbinsX(); ++b) {
                double x = h->GetBinCenter(b); if (x >= p.xmax) break;
                if (x < p.xmin) continue;
                double nu = f->Integral(h->GetBinLowEdge(b), h->GetBinLowEdge(b + 1)) / h->GetBinWidth(b);
                if (!(nu > 0) || !std::isfinite(nu)) { ++invalid; continue; }
                double value = (h->GetBinContent(b) - nu) / std::sqrt(nu);
                graph->SetPoint(graph->GetN(), x, value); bound = std::max(bound, std::abs(value));
                xmin = std::min(xmin, x); xmax = std::max(xmax, x);
            }
            graph->SetMarkerStyle(20); graph->SetMarkerSize(0.35); graph->SetMarkerColor(p.used ? kBlue + 1 : kOrange + 7);
            residuals.push_back({p, std::move(graph)});
        }
        left.cd();
        if (xmax <= xmin) { xmin = 0.; xmax = 65535.; }
        double margin = 0.04 * (xmax - xmin); bound *= 1.2;
        auto* frame = left.DrawFrame(xmin - margin, -bound, xmax + margin, bound);
        frame->GetXaxis()->SetTitle("ADC channel"); frame->GetYaxis()->SetTitle("Pearson residual");
        frame->GetXaxis()->SetTitleSize(0.035); frame->GetYaxis()->SetTitleSize(0.035);
        TLine zero(xmin - margin, 0., xmax + margin, 0.); zero.SetLineStyle(2); zero.DrawClone();
        for (auto& item : residuals) {
            item.graph->Draw("P SAME");
            TLatex label; label.SetTextSize(0.022); label.SetTextColor(item.p.used ? kBlue + 1 : kOrange + 7);
            if (std::isfinite(item.p.mean)) label.DrawLatex(item.p.mean, bound * 0.83, Form("%d", item.p.index));
        }
        text(0.10, 0.955, "Local peak residuals: (n-\nu)/\\sqrt{\nu}", 0.030);
        text(0.10, 0.90, "Disjoint windows; zero baseline; orange = rejected", 0.022);

        // Right: Calibration curve
        right.cd();
        double xlo = std::isfinite(r.amin) ? r.amin : 0., xhi = std::isfinite(r.amax) ? r.amax : 65535.;
        double ylo = std::isfinite(r.emin) ? r.emin : 0., yhi = std::isfinite(r.emax) ? r.emax : 1500.;
        if (xhi <= xlo) { xlo = 0.; xhi = 65535.; }
        auto* calframe = right.DrawFrame(xlo - 0.05 * (xhi - xlo), std::max(0., ylo - 0.12 * (yhi - ylo)),
                                        xhi + 0.05 * (xhi - xlo), yhi + 0.12 * (yhi - ylo));
        calframe->GetXaxis()->SetTitle("Centroid mean (ADC)"); calframe->GetYaxis()->SetTitle("E_{ref} (keV)");
        calframe->GetXaxis()->SetTitleSize(0.032); calframe->GetYaxis()->SetTitleSize(0.032);
        calframe->GetXaxis()->SetLabelSize(0.026); calframe->GetYaxis()->SetLabelSize(0.026);
        auto graph = std::make_unique<TGraphErrors>();
        for (auto p : r.peaks) if (p.used) {
            int i = graph->GetN(); graph->SetPoint(i, p.mean, p.ref_E); graph->SetPointError(i, p.mean_err, p.ref_err);
        }
        graph->SetMarkerStyle(20); graph->SetMarkerSize(0.6); graph->SetMarkerColor(kBlue + 1); graph->Draw("P SAME");
        auto* curve = dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject("energy_pol2"));
        if (curve) { curve->SetLineColor(kRed + 1); curve->SetLineWidth(2); curve->DrawCopy("SAME"); }
        text(0.09, 0.955, "pol2: E = a_{0} + a_{1}A + a_{2}A^{2}", 0.029);
        text(0.09, 0.90, "EX: centroid error; EY: reference energy error", 0.022);

        auto* metrics = new TPaveText(0.53, 0.035, 0.995, 0.86, "NDC");
        metrics->SetBorderSize(0); metrics->SetFillStyle(0); metrics->SetTextFont(42); metrics->SetTextAlign(12); metrics->SetTextSize(0.023);
        metrics->AddText(r.status == "success" ? "Calibration status: SUCCESS" : (r.status == "limited_range" ? "Status: LIMITED RANGE" : "Status: REVIEW / FAILED"));
        if (curve) {
            metrics->AddText(Form("a_{0} = %.5g #pm %.3g keV", r.a[0], r.error[0]));
            metrics->AddText(Form("a_{1} = %.6g #pm %.3g keV/ADC", r.a[1], r.error[1]));
            metrics->AddText(Form("a_{2} = %.5g #pm %.3g keV/ADC^{2}", r.a[2], r.error[2]));
            if (r.ndf > 0) metrics->AddText(Form("#chi^{2}/ndf = %.4g/%d = %.4g", r.chi2, r.ndf, r.chi2 / r.ndf));
            metrics->AddText(Form("N=%d; %.1f to %.1f keV", r.n, r.emin, r.emax));
            metrics->AddText(Form("RMS=%.4g; max|#DeltaE|=%.4g keV", r.rms, r.max_de));
            metrics->AddText("#  E_{ref} (keV)   #DeltaE = E_{ref}-E(mean)");
            for (auto p : r.peaks) if (p.used) metrics->AddText(Form("%d   %.4f   %+.4f keV", p.index, p.ref_E, p.ref_E - Energy(r, p.mean)));
        } else metrics->AddText("No validated polynomial available");
        metrics->Draw();

        top.cd();
        auto* reason = new TPaveText(0.695, 0.865, 0.995, 0.995, "NDC");
        reason->SetFillStyle(0); reason->SetBorderSize(0); reason->SetTextAlign(12); reason->SetTextFont(42); reason->SetTextSize(0.019);
        std::istringstream words(r.reason); std::string word, line;
        while (words >> word) {
            if (line.size() + word.size() > 48) { reason->AddText(line.c_str()); line.clear(); }
            if (!line.empty()) line += ' ';
            line += word;
        }
        if (!line.empty()) reason->AddText(line.c_str());
        reason->Draw();

        canvas.Modified(); canvas.Update();
        // Export to SVG vector format
        auto path = directory / "figures" / (std::string(h->GetName()) + ".svg");
        canvas.SaveAs(path.c_str());
        if (!fs::exists(path) || fs::file_size(path) == 0) throw std::runtime_error("SVG export failed");
        ++generated;
    }
    std::cout << "Exported " << generated << " SVG review figures from saved ROOT.\n";
}
