#include "plotexport.hh"
#include "autocal.hh"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include "TCanvas.h"
#include "TF1.h"
#include "TGraph.h"
#include "TGraphErrors.h"
#include "TH1D.h"
#include "TH2D.h"
#include "TKey.h"
#include "TLine.h"
#include "TLatex.h"
#include "TNamed.h"
#include "TPad.h"
#include "TPaveText.h"
#include "TStyle.h"
#include "TFile.h"

namespace fs = std::filesystem;
namespace {
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
        right.SetLeftMargin(0.09); right.SetRightMargin(0.36); right.SetTopMargin(0.14); right.SetBottomMargin(0.12);
        top.Draw(); left.Draw(); right.Draw();

        auto text = [](double x, double y, const std::string& label, double size = 0.026) {
            TLatex line; line.SetNDC(); line.SetTextFont(42); line.SetTextSize(size); line.DrawLatex(x, y, label.c_str());
        };

        auto* table = new TPaveText(0.69, 0.06, 0.995, 0.86, "NDC");
        table->SetBorderSize(0); table->SetFillStyle(0); table->SetTextFont(42); table->SetTextAlign(12); table->SetTextSize(0.016);
        table->AddText("peak  Eref (keV)  mean +/- err (ADC)");
        for (auto p : r.peaks) {
            table->AddText(Form("%d  E=%.1f  A=%.1f +/- %.1f %s", p.index, p.ref_E, p.mean, p.mean_err, p.used ? "" : "[reject]"));
        }
        if (r.peaks.empty()) table->AddText("No uniquely assigned/fitted lines");
        table->AddText("Dithering: ADC = evte + U(0,1)");
        table->AddText("Red: used; orange dashed: rejected fit");
        table->AddText("Sources: UserDefine.hh::Sources");

        top.cd(); top.SetLogy();
        h->SetLineColor(kBlack); h->SetLineWidth(1); h->SetMinimum(0.5);
        double display_max = 65535.0;
        if (std::isfinite(r.amax) && r.amax > 0.) display_max = std::min(65535.0, std::max(2000.0, 1.25 * r.amax));
        h->GetXaxis()->SetRangeUser(0.0, display_max);
        double peakmax = std::max(2., h->GetMaximum()); h->SetMaximum(peakmax * 8.);
        h->GetXaxis()->SetTitle("ADC channel"); h->GetYaxis()->SetTitle("Counts / bin");
        h->GetXaxis()->SetTitleSize(0.035); h->GetYaxis()->SetTitleSize(0.035);
        h->GetXaxis()->SetLabelSize(0.028); h->GetYaxis()->SetLabelSize(0.028);
        h->Draw("HIST");

        for (auto p : r.peaks) {
            auto* f = dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject(p.function.c_str()));
            if (!f) continue;
            f->SetLineColor(p.used ? kRed + 1 : kOrange + 7);
            f->SetLineStyle(p.used ? 1 : 2);
            f->SetLineWidth(1);
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
        text(0.10, 0.955, "Local peak residuals: Pearson r", 0.024);
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
        graph->SetMarkerStyle(20); graph->SetMarkerSize(1.0); graph->SetMarkerColor(kBlue + 1); graph->Draw("PZ SAME");
        auto* curve = dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject("energy_pol2"));
        if (curve) { curve->SetLineColor(kRed + 1); curve->SetLineWidth(1); curve->DrawCopy("SAME"); }
        text(0.09, 0.955, "pol2: E = a0 + a1 A + a2 A2", 0.024);
        text(0.09, 0.90, "EX: centroid error; EY: reference energy error", 0.022);

        auto* metrics = new TPaveText(0.68, 0.08, 0.995, 0.86, "NDC");
        metrics->SetBorderSize(0); metrics->SetFillStyle(0); metrics->SetTextFont(42); metrics->SetTextAlign(12); metrics->SetTextSize(0.014);
        metrics->AddText(r.status == "success" ? "Calibration status: SUCCESS" : (r.status == "limited_range" ? "Status: LIMITED RANGE" : "Status: REVIEW / FAILED"));
        if (curve) {
            metrics->AddText(Form("a0=%.5g +/- %.2g keV", r.a[0], r.error[0]));
            metrics->AddText(Form("a1=%.6g +/- %.2g keV/ADC", r.a[1], r.error[1]));
            metrics->AddText(Form("a2=%.5g +/- %.2g keV/ADC2", r.a[2], r.error[2]));
            if (r.ndf > 0) metrics->AddText(Form("chi2/ndf=%.3g/%d=%.3g", r.chi2, r.ndf, r.chi2 / r.ndf));
            metrics->AddText(Form("N=%d; %.1f-%.1f keV", r.n, r.emin, r.emax));
            metrics->AddText(Form("RMS=%.3g; max|dE|=%.3g keV", r.rms, r.max_de));
            metrics->AddText("peak  Eref  dE (keV)");
            for (auto p : r.peaks) if (p.used) metrics->AddText(Form("%d   %.1f   %+.2f", p.index, p.ref_E, p.ref_E - Energy(r, p.mean)));
        } else metrics->AddText("No validated polynomial available");
        metrics->Draw();

        top.cd();
        auto* reason = new TPaveText(0.055, 0.835, 0.68, 0.89, "NDC");
        reason->SetFillStyle(0); reason->SetBorderSize(0); reason->SetTextAlign(12); reason->SetTextFont(42); reason->SetTextSize(0.018);
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
