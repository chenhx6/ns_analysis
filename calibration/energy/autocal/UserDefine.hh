#pragma once
#include <string>
#include <tuple>
#include <vector>

// Hardware identity; no detector type or fixed module/channel list is required.
struct ChannelID
{
    short cid, sid, ch;
    bool operator<(const ChannelID &b) const { return std::tie(cid, sid, ch) < std::tie(b.cid, b.sid, b.ch); }
    bool operator==(const ChannelID &b) const { return std::tie(cid, sid, ch) == std::tie(b.cid, b.sid, b.ch); }
};
namespace User
{
    inline const std::string InputFile = "/home/ys/data_401/data/chx_20260622/decode_data/data_C1_6082_notwave.root";
    inline const std::string OutputDir = "../"; // A new input-stem subdirectory is created or reused.
    inline const std::string SourceLibrary = "./sources.csv";
    inline const std::vector<std::string> Sources = {"152Eu", "133Ba"}; // Single source e.g. {"152Eu"} fully supported.
    inline const std::vector<ChannelID> ExcludedFitChannels = {};

    // 2D Calibration Check Matrix (TH2D h2_energy_cal) parameters
    constexpr int CheckMatrixBins = 4096;
    constexpr double CheckMatrixMin_keV = 0.0;
    constexpr double CheckMatrixMax_keV = 2048.0;

    // ADC Dithering for continuous spectra: ADC = evte + Uniform(0, 1)
    constexpr bool EnableDithering = true;
    constexpr unsigned int RandomSeed = 42;

    // Candidate rebin factors for multi-scale peak detection and fitting
    inline const std::vector<int> CandidateRebins = {1, 2, 4, 8, 16, 32, 64, 80, 128, 150};

    constexpr int SpectrumBins = 65536;    // Range [0, 65536).
    constexpr double NoiseCutoffADC = 50.; // Search threshold.
    constexpr int MaxCandidates = 60;
    constexpr double SearchThreshold = .015; // TSpectrum fraction of maximum.
    constexpr double MinPeakCounts = 10.;
    constexpr double MinProminenceSigma = 3.;      // Candidate excess / sqrt(peak + sideband).
    constexpr double MatchTolerance_keV = 4.0;     // Coarse linear matching initial tolerance.
    constexpr double MinGain = .01, MaxGain = 2.5; // keV/ADC.
    constexpr double MaxOffset_keV = 80.;
    constexpr double MinAnchorSpan_keV = 100.;
    constexpr double FitWindowSigma = 3.5;      // Half-window for Gaussian + linear fit.
    constexpr double MinAreaSignificance = 3.0; // Gaussian amplitude / error.

    // Practical physical calibration acceptance tolerances
    constexpr double MaxAbsResidual_keV = 1.5; // Target absolute residual for high-resolution HPGe
    constexpr double MaxRelativeFWHM = 0.25;   // Target relative residual / local FWHM (for scintillator/LaBr3)
    constexpr double CoverageFraction = .65;   // Fraction of selected source energy range required for success
}
