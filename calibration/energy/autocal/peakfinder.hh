#pragma once
#include "UserDefine.hh"
#include <string>
#include <vector>
#include <utility>
#include <limits>
#include <memory>
#include "TH1D.h"
#include "TF1.h"

inline double missing() { return std::numeric_limits<double>::quiet_NaN(); }
struct SourceLine {
    std::string source;
    double energy=0, error=0, intensity=0;
    std::vector<double> companions; // Documented neighbouring emissions, keV.
};
struct PeakCandidate { double x=0, height=0, sigma=0; };
struct MatchResult {
    double offset=0, gain=0, a2=0, rms=0;
    bool valid=false, ambiguous=false;
    std::string reason;
    std::vector<std::pair<int,int>> pairs; // (reference index, candidate index), one to one.
};
struct FittedPeak {
    int index=0;
    double ref_E=0, ref_err=0, mean=missing(), mean_err=missing(), sigma=missing();
    double xmin=0, xmax=0;
    bool used=false;
    std::string reason, function;
};
// Owns candidate search, ambiguity checks and local Poisson Gaussian+pol1 fitting.
class PeakFinder {
public:
    std::vector<PeakCandidate> SearchCandidates(const TH1D& h) const;
    MatchResult Match(const std::vector<PeakCandidate>& candidates, const std::vector<SourceLine>& refs) const;
    std::vector<FittedPeak> Fit(TH1D& h, const std::vector<PeakCandidate>& candidates,
                                const std::vector<SourceLine>& refs, const MatchResult& match) const;
};
