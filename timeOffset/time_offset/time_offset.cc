#include "time_offset.hh"
#include <TFile.h>
#include <TTree.h>
#include <TLeaf.h>
#include <TF1.h>
#include <TFitResult.h>
#include <TFitResultPtr.h>
#include <TNamed.h>
#include <TParameter.h>
#include <algorithm>
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

namespace fs = std::filesystem;
namespace
{
    // Fail explicitly rather than emit a plausible but incomplete calibration.
    void Require(bool ok, const std::string &message)
    {
        if (!ok)
            throw std::runtime_error(message);
    }
    // Timestamp ticks follow the decoder, not the ADC sampling period.
    int Tick(int sr)
    {
        if (sr == 125 || sr == 250)
            return 8;
        if (sr == 100 || sr == 500)
            return 10;
        throw std::runtime_error("Unsupported sr: " + std::to_string(sr));
    }
    // Stable channel identity, including modules 0 through 16.
    std::string Name(int id)
    {
        return "c" + std::to_string(id / 272) + "_s" + std::to_string(id / 16 % 17) +
               "_ch" + std::to_string(id % 16);
    }
    struct Shape
    {
        double low = 0, high = 0, background = 0, peak = 0, second = 0;
        bool signal = false, two = false;
    };
    // Smooth the 2 ns spectrum over 50 ns so clock-comb gaps are not extra peaks.
    Shape FindShape(const TH1D &h)
    {
        const int n = h.GetNbinsX();
        std::vector<double> y(n + 1, 0), sorted;
        for (int i = 1; i <= n; ++i)
        {
            int a = std::max(1, i - 12), b = std::min(n, i + 12);
            y[i] = h.Integral(a, b) / (b - a + 1);
            sorted.push_back(y[i]);
        }
        std::sort(sorted.begin(), sorted.end());
        double bg = sorted[sorted.size() / 2];
        int p = int(std::max_element(y.begin() + 1, y.end()) - y.begin());
        Shape s;
        s.background = bg * 12; // Expected counts per 24 ns bin.
        s.peak = h.GetBinCenter(p);
        double height = y[p] - bg;
        if (h.GetEntries() < 100 || height < std::max(1.0, 5 * std::sqrt((bg + 1) / 25)))
            return s;
        s.signal = true;
        int q = p;
        // Require a resolved valley and >=72 ns separation for a second seed.
        for (int i = 2; i < n; ++i)
        {
            if (std::abs(i - p) < 36 || y[i] < y[i - 1] || y[i] <= y[i + 1])
                continue;
            double valley = *std::min_element(y.begin() + std::min(i, p), y.begin() + std::max(i, p) + 1);
            if (y[i] - bg > 0.2 * height && valley - bg < 0.85 * (std::min(y[i], y[p]) - bg) && (q == p || y[i] > y[q]))
                q = i;
        }
        s.two = q != p;
        s.second = h.GetBinCenter(q);
        int l = std::min(p, q), r = std::max(p, q);
        const double tail = bg + std::max(0.05 * height, 2 * std::sqrt((bg + 1) / 25));
        while (l > 1 && y[l] > tail)
            --l;
        while (r < n && y[r] > tail)
            ++r;
        // Extend into sidebands; snap to coarse-bin edges within +/-1992 ns.
        s.low = std::max(-1992.0, 24 * std::floor((h.GetBinCenter(l) - 96) / 24));
        s.high = std::min(1992.0, 24 * std::ceil((h.GetBinCenter(r) + 96) / 24));
        return s;
    }
    struct Fit
    {
        std::unique_ptr<TF1> function;
        int status = -1, covariance = 0;
        double bic = std::numeric_limits<double>::infinity();
        bool valid = false;
    };
    // Fit bin-averaged counts with Poisson likelihood; a positive linear background.
    Fit FitModel(TH1D &h, const Shape &s, bool two)
    {
        Fit out;
        int bg = two ? 6 : 3;
        // Positive endpoint values parameterize exactly the same family as pol1.
        std::string formula = two ? "gaus(0)+gaus(3)" : "gaus(0)";
        formula += "+[" + std::to_string(bg) + "]*(" + std::to_string(s.high) + "-x)/(" +
                   std::to_string(s.high - s.low) + ")+[" + std::to_string(bg + 1) + "]*(x-(" +
                   std::to_string(s.low) + "))/(" + std::to_string(s.high - s.low) + ")";
        out.function.reset(new TF1(two ? "double_gauss_pol1" : "gauss_pol1", formula.c_str(), s.low, s.high));
        TF1 &f = *out.function;
        double amplitude = std::max(1.0, h.GetMaximum() - s.background);
        for (int j = 0; j < (two ? 2 : 1); ++j)
        {
            int k = 3 * j;
            f.SetParameter(k, amplitude * (j ? 0.6 : 1));
            f.SetParLimits(k, 0, 10 * h.GetMaximum() + 10);
            f.SetParameter(k + 1, j ? s.second : s.peak);
            f.SetParLimits(k + 1, s.low + 12, s.high - 12);
            f.SetParameter(k + 2, 36);
            f.SetParLimits(k + 2, 6, (s.high - s.low) / 2);
        }
        for (int k = bg; k < bg + 2; ++k)
        {
            f.SetParameter(k, std::max(0.1, s.background));
            f.SetParLimits(k, 0, 10 * h.GetMaximum() + 10);
        }
        // N avoids attaching rejected trials; S retains covariance; I averages bins.
        TFitResultPtr result = h.Fit(&f, "SQLIRN");
        out.status = int(result);
        if (!result.Get())
            return out;
        out.covariance = result->CovMatrixStatus();
        int bins = int(std::round((s.high - s.low) / 24));
        out.bic = 2 * result->MinFcnValue() + f.GetNpar() * std::log(double(bins));
        out.valid = out.status == 0 && out.covariance >= 2 && std::isfinite(out.bic);
        for (int j = 0; j < (two ? 2 : 1); ++j)
        {
            int k = 3 * j;
            double mu = f.GetParameter(k + 1), sigma = f.GetParameter(k + 2);
            out.valid &= f.GetParameter(k) > 3 * f.GetParError(k) &&
                         mu > s.low + 13 && mu < s.high - 13 && sigma > 6.1 && sigma < 0.49 * (s.high - s.low);
        }
        if (two)
            out.valid &= std::abs(f.GetParameter(1) - f.GetParameter(4)) > 24;
        return out;
    }
}

// Allocate spectra only for observed channels; retain every CsI hit, last Ge hit.
void TimeOffset::AddHit(int channel, Long64_t ns)
{
    auto &s = spectra[channel];
    if (!s.fine)
    {
        std::string name = Name(channel);
        s.fine.reset(new TH1D((name + "_2ns").c_str(),
                              (name + ";t_{ref}-t_{channel} [ns];Pairs / 2 ns").c_str(), 1999, -1999, 1999));
        s.coarse.reset(new TH1D((name + "_24ns").c_str(),
                                (name + ";t_{ref}-t_{channel} [ns];Pairs / 24 ns").c_str(), 166, -1992, 1992));
        s.fine->SetDirectory(nullptr);
        s.coarse->SetDirectory(nullptr);
    }
    ++s.hits;
    if (channel < 272)
    {
        ge[channel] = ns;
        present[channel] = true;
    }
    else
        csi.emplace_back(channel, ns);
}
// The fine histogram has integer differences at bin centers; coarse edges narrower.
void TimeOffset::Fill(int channel, Long64_t dt)
{
    if (std::abs(dt) > Window)
        return;
    spectra[channel].fine->Fill(double(dt));
    spectra[channel].coarse->Fill(double(dt));
}
// Close even the final event; never fill the reference against itself.
void TimeOffset::EndEvent()
{
    if (!active)
        return;
    ++events;
    if (present[Reference])
    {
        ++references;
        for (int i = 0; i < 272; ++i)
            if (present[i] && i != Reference)
                Fill(i, ge[Reference] - ge[i]);
        for (const auto &hit : csi)
            Fill(hit.first, ge[Reference] - hit.second);
    }
    present.fill(false);
    csi.clear();
    active = false;
}
// Export selected fits and diagnostics; invalid channels leave offset fields empty.
void TimeOffset::FitAndWrite(const std::string &csv)
{
    std::ofstream table(csv);
    Require(bool(table), "Cannot create CSV");
    table << std::setprecision(10);
    int observed = 0, accepted = 0, doubles = 0, failed = 0, weak = 0, poor = 0;
    table << "cid,sid,ch,hits,pairs,model,status,fit_status,covariance,low_ns,high_ns,mu1_ns,mu1_error_ns,sigma1_ns,mu2_ns,mu2_error_ns,sigma2_ns,offset_ns,offset_error_ns,bic,chi2,ndf,underflow_24ns,overflow_24ns\n";
    for (int id = 0; id < Channels; ++id)
    {
        auto &s = spectra[id];
        if (!s.fine)
            continue;
        ++observed;
        Shape shape = FindShape(*s.fine);
        Fit fit;
        bool two = false;
        std::string status = id == Reference ? "reference" : "no_peak";
        if (shape.signal && id != Reference)
        {
            fit = FitModel(*s.coarse, shape, false);
            if (shape.two)
            {
                Fit candidate = FitModel(*s.coarse, shape, true);
                if (candidate.valid && (!fit.valid || candidate.bic + 10 < fit.bic))
                {
                    fit = std::move(candidate);
                    two = true;
                }
            }
            status = fit.valid ? (two ? "double_peak_review" : "ok") : "fit_failed";
            if (fit.valid && fit.function->GetNDF() > 0 &&
                fit.function->GetChisquare() / fit.function->GetNDF() > 3)
            {
                status = two ? "double_poor_fit_review" : "poor_fit_review";
                ++poor;
            }
            TF1 *saved = static_cast<TF1 *>(fit.function->Clone("time_fit"));
            saved->SetLineColor(fit.valid ? 2 : 6);
            saved->SetNpx(1000);
            s.coarse->GetListOfFunctions()->Add(saved);
        }
        if (id != Reference)
        {
            if (!shape.signal)
                ++weak;
            else if (!fit.valid)
                ++failed;
            else
            {
                ++accepted;
                if (two)
                    ++doubles;
            }
        }
        table << id / 272 << ',' << id / 16 % 17 << ',' << id % 16 << ',' << s.hits << ','
              << s.fine->GetEntries() << ',' << (fit.function ? (two ? "double_gauss_pol1" : "gauss_pol1") : "none")
              << ',' << status << ',' << fit.status << ',' << fit.covariance << ',' << shape.low << ',' << shape.high;
        for (int j = 0; j < 2; ++j)
        {
            if (fit.function && (j == 0 || two))
            {
                TF1 &f = *fit.function;
                table << ',' << f.GetParameter(3 * j + 1) << ',' << f.GetParError(3 * j + 1) << ',' << f.GetParameter(3 * j + 2);
            }
            else
                table << ",,,";
        }
        if (id == Reference)
            table << ",0,0";
        else if (fit.valid)
        {
            TF1 &f = *fit.function;
            int k = two && f.GetParameter(3) > f.GetParameter(0) ? 4 : 1;
            table << ',' << f.GetParameter(k) << ',' << f.GetParError(k);
        }
        else
            table << ",,";
        if (fit.function)
            table << ',' << fit.bic << ',' << fit.function->GetChisquare() << ',' << fit.function->GetNDF();
        else
            table << ",,,";
        table << ',' << s.coarse->GetBinContent(0) << ',' << s.coarse->GetBinContent(167) << '\n';
        s.fine->Write();
        s.coarse->Write();
    }
    Require(bool(table), "CSV write failed");
    std::ofstream report(fs::path(csv).replace_extension(".md"));
    report << "# 单文件时间差拟合结果\n\n"
           << "- 观察通道：" << observed << "（参考通道若出现则包含在内）。\n"
           << "- 收敛且通过参数检查：" << accepted << "；其中双峰：" << doubles << "。\n"
           << "- 上述结果中 ROOT likelihood deviance/ndf > 3、需回查模型：" << poor << "。\n"
           << "- 无可靠峰：" << weak << "；拟合或参数检查失败：" << failed << "。\n"
           << "- 事件：" << events << "；含参考事件：" << references << "；时间倒序：" << regressions << "；地址筛除：" << rejected << "。\n\n"
           << "offset 为 t_ref-t_channel 峰中心（ns），加到目标时间；双峰选较高拟合分量，两个中心均保留。"
           << "误差为 ROOT 模型内参数标准误，不含模型选择、事件分组或 run 内漂移的系统误差。"
           << "review 表示候选结果需要查看谱形，非已验证标定；失败行留空 offset。\n\n"
           << "拟合函数已附在 24 ns 谱（time_fit），失败尝试以紫色显示。"
           << "详细模型、区间、峰宽、误差、BIC、chi2、自由度和溢出计数见同名 CSV；"
           << "输入路径与处理条数见同名 ROOT 元数据；方法及复现命令见 README.md。\n";
    Require(bool(report), "Report write failed");
    std::cout << "channels=" << observed << " fits=" << accepted << " double=" << doubles
              << " poor=" << poor << " no_peak=" << weak << " failed=" << failed << std::endl;
}
// Stream only five scalar branches; neither read waveforms nor alter the input.
void TimeOffset::Process(int run, const std::string &input, const std::string &output, Long64_t limit)
{
    Require(limit >= 0, "Negative entry limit");
    fs::path directory = fs::canonical(output);
    // Restrict outputs to the task tree, resolving symlinks before checking.
    fs::path task = fs::canonical("/proc/self/exe").parent_path().parent_path();
    fs::path relative = directory.lexically_relative(task);
    Require(!relative.empty() && *relative.begin() != "..", "Output must be inside the timeOffset task directory");
    const std::string root = (directory / ("time_offset_" + std::to_string(run) + ".root")).string();
    const std::string csv = (directory / ("time_offset_" + std::to_string(run) + ".csv")).string();
    Require(!fs::exists(root) && !fs::exists(csv) && !fs::exists(fs::path(csv).replace_extension(".md")),
            "Output already exists; use a new output directory");
    TFile source(input.c_str(), "READ");
    Require(!source.IsZombie(), "Cannot open input ROOT");
    auto *tree = dynamic_cast<TTree *>(source.Get("tree"));
    Require(tree != nullptr, "Missing tree");
    Hit hit;
    tree->SetBranchStatus("*", 0);
    for (const char *field : {"ts", "cid", "sid", "ch", "sr"})
    {
        auto *leaf = tree->GetLeaf(field);
        Require(leaf && leaf->GetLenStatic() == 1 && !leaf->GetLeafCount() &&
                    std::string(leaf->GetTypeName()) == (std::string(field) == "ts" ? "Long64_t" : "Short_t"),
                std::string("Invalid branch: ") + field);
        tree->SetBranchStatus(field, 1);
    }
    Require(tree->SetBranchAddress("ts", &hit.ts) >= 0 && tree->SetBranchAddress("cid", &hit.cid) >= 0 &&
                tree->SetBranchAddress("sid", &hit.sid) >= 0 && tree->SetBranchAddress("ch", &hit.ch) >= 0 &&
                tree->SetBranchAddress("sr", &hit.sr) >= 0,
            "Branch binding failed");
    Long64_t entries = tree->GetEntries(), count = limit ? std::min(limit, entries) : entries;
    for (Long64_t i = 0; i < count; ++i)
    {
        Require(tree->GetEntry(i) > 0, "Failed reading entry " + std::to_string(i));
        if (hit.cid < 0 || hit.cid > 1 || hit.sid < 0 || hit.sid > 16 || hit.ch < 0 || hit.ch > 15)
        {
            ++rejected;
            continue;
        }
        int tick = Tick(hit.sr);
        Require(hit.ts >= 0 && hit.ts <= std::numeric_limits<Long64_t>::max() / tick, "Timestamp overflow");
        Long64_t ns = hit.ts * tick;
        if (active && ns < previous)
        {
            ++regressions;
            EndEvent();
        }
        // Fixed anchor: this is the event/sort.cc grouping, not a sliding pair search.
        if (active && ns - start > Window)
            EndEvent();
        if (!active)
        {
            start = ns;
            active = true;
        }
        previous = ns;
        AddHit((hit.cid * 17 + hit.sid) * 16 + hit.ch, ns);
        if ((i + 1) % 10000000 == 0)
            std::cout << "Read " << i + 1 << " / " << count << std::endl;
    }
    EndEvent();
    TFile target(root.c_str(), "CREATE");
    Require(!target.IsZombie(), "Cannot create output ROOT");
    FitAndWrite(csv);
    TNamed("source", fs::canonical(input).c_str()).Write();
    TNamed("method", "fixed_start_1999ns; ref=0,2,5; dt=ref-target; Ge=last; CsI=all; no CFD/energy/offset; 24ns=[-1992,1992]").Write();
    TParameter<Long64_t>("input_entries", entries).Write();
    TParameter<Long64_t>("processed_entries", count).Write();
    TParameter<Long64_t>("events", events).Write();
    TParameter<Long64_t>("reference_events", references).Write();
    TParameter<Long64_t>("time_regressions", regressions).Write();
    TParameter<Long64_t>("rejected_addresses", rejected).Write();
    target.Close();
    std::cout << "events=" << events << " reference_events=" << references << " regressions=" << regressions
              << " rejected=" << rejected << "\n"
              << root << "\n"
              << csv << std::endl;
}
// Deterministic grouping/sign/duplicate and bin-width regression check.
void TimeOffset::SelfCheck()
{
    TimeOffset task;
    task.active = true;
    task.AddHit(Reference, 1000);
    task.AddHit(38, 900);
    task.AddHit(38, 920);
    task.AddHit(304, 1100);
    task.AddHit(304, 1120);
    task.EndEvent();
    assert(task.spectra[38].fine->GetEntries() == 1);
    assert(task.spectra[38].fine->GetBinContent(task.spectra[38].fine->FindBin(80)) == 1);
    assert(task.spectra[304].fine->GetEntries() == 2);
    assert(task.spectra[304].fine->GetBinContent(task.spectra[304].fine->FindBin(-120)) == 1);
    assert(task.spectra[Reference].fine->GetEntries() == 0);
    assert(task.spectra[38].fine->GetBinWidth(1) == 2 && task.spectra[38].coarse->GetBinWidth(1) == 24);
    assert(Tick(100) == 10 && Tick(250) == 8 && Tick(500) == 10);
    // Known synthetic two-Gaussian expectation tests shape seeds and ROOT fit recovery.
    TH1D fine("test_fine", "", 1999, -1999, 1999), coarse("test_coarse", "", 166, -1992, 1992);
    TF1 truth("truth", "gaus(0)+gaus(3)+[6]", -1999, 1999);
    truth.SetParameters(100, -180, 30, 70, 60, 35, 2);
    for (int i = 1; i <= fine.GetNbinsX(); ++i)
        fine.SetBinContent(i, truth.Integral(fine.GetBinLowEdge(i), fine.GetBinLowEdge(i + 1)) / 24);
    for (int i = 1; i <= coarse.GetNbinsX(); ++i)
        coarse.SetBinContent(i, truth.Integral(coarse.GetBinLowEdge(i), coarse.GetBinLowEdge(i + 1)) / 24);
    Shape shape = FindShape(fine);
    assert(shape.signal && shape.two);
    Fit fit = FitModel(coarse, shape, true);
    assert(fit.valid && std::abs(fit.function->GetParameter(1) + 180) < 2 && std::abs(fit.function->GetParameter(4) - 60) < 2);
    std::cout << "Self-check passed\n";
}
// CLI keeps one run per invocation; optional limit is for finite-sample checks.
int main(int argc, char **argv)
{
    try
    {
        if (argc == 2 && std::string(argv[1]) == "--self-check")
        {
            TimeOffset::SelfCheck();
            return 0;
        }
        if (argc < 4 || argc > 5)
        {
            std::cerr << "Usage: " << argv[0] << " RUN INPUT.root OUTPUT_DIRECTORY [MAX_ENTRIES]\n";
            return 2;
        }
        size_t used = 0;
        int run = std::stoi(argv[1], &used);
        Require(used == std::string(argv[1]).size() && run > 0, "Invalid run");
        Long64_t limit = 0;
        if (argc == 5)
        {
            limit = std::stoll(argv[4], &used);
            Require(used == std::string(argv[4]).size(), "Invalid limit");
        }
        TimeOffset task;
        task.Process(run, argv[2], argv[3], limit);
    }
    catch (const std::exception &e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
    return 0;
}
