#pragma once
#include "peakfinder.hh"
#include <filesystem>
#include <array>
#include <map>

struct Settings {
    std::filesystem::path root, input, output, library;
    std::vector<std::string> sources=User::Sources;
    std::vector<ChannelID> excluded=User::ExcludedFitChannels;
    long long max_entries=-1;
    bool export_only=false;
};
struct ChannelResult {
    std::string status="failed_matching", reason;
    bool candidate=false;
    int n=0, ndf=0;
    double chi2=missing(), probability=missing(), rms=missing(), max_de=missing();
    double emin=missing(), emax=missing(), amin=missing(), amax=missing();
    std::array<double,3> a{missing(),missing(),missing()}, error{missing(),missing(),missing()};
    std::vector<FittedPeak> peaks;
};
// These functions also support the saved C++ development checks without requiring event files.
void FitCalibration(ChannelResult& r, TH1D& h, const std::vector<SourceLine>& refs);
std::vector<SourceLine> LoadSources(const Settings& settings);
void ExportFigures(const std::filesystem::path& output);
int Run(const Settings& settings);
