# Automated Energy Calibration for Gamma-Ray Spectroscopy

This program performs automated energy calibration for HPGe / Clover and auxiliary gamma detectors from decoded experimental event trees.

## Design and Features

1. **Automatic Channel Discovery**: Dynamically identifies all active hardware channels `(cid, sid, ch)` from the event tree without hardcoded channel counts or module assumptions.
2. **Standard Source Library**: Reference gamma lines and emission intensities are stored in `sources.csv` using IAEA-TECDOC-619 evaluated standards for $^{152}\text{Eu}$ and $^{133}\text{Ba}$.
3. **Robust Peak Identification**: Combines ROOT `TSpectrum` candidate detection with combinatorial coarse linear matching to identify true gamma lines and eliminate background/noise artifacts.
4. **Gaussian + Linear Background Fitting**: Fits each matched line with `gaus(0) + pol1(3)` using binned Poisson likelihood, extracting accurate peak centroids and statistical uncertainties.
5. **Quadratic Polynomial Calibration**: Fits `E(A) = a0 + a1*A + a2*A^2` using ROOT `TGraphErrors` with peak centroid uncertainties on the horizontal axis and reference energy uncertainties on the vertical axis.
6. **Physical Validation**: Enforces positive slope (`dE/dA > 0`) across the entire active energy range, checks calibration residual RMS and maximum deviation, and identifies channels with limited degrees of freedom or matching failures.
7. **Three-Panel Review Graphics**: Directly produces publication-ready three-panel PNG figures from the ROOT histograms for inspection:
   - **Top**: Channel energy spectrum with overlaid peak fits and reference line identification.
   - **Bottom-Left**: Local peak fit Pearson residuals `(n - \nu)/\sqrt{\nu}` across fit windows.
   - **Bottom-Right**: Calibration curve with data points, error bars, `pol2` fit, and summary metrics.

## Directory Structure

- `main.cc`: Program entry point.
- `autocal.hh`, `autocal.cc`: Calibration pipeline, ROOT I/O, CSV export, and figure generation.
- `peakfinder.hh`, `peakfinder.cc`: Object-oriented peak finder and local peak fitting engine.
- `UserDefine.hh`: Input/output paths, source selection, exclusion list, and algorithm parameters.
- `sources.csv`: Evaluated reference gamma energies and intensities.
- `Makefile`: Standard compilation rules using `root-config`.

## Build and Execution

```bash
# Build executable
make -C calibration/energy/autocal

# Run calibration from workspace root
./calibration/energy/autocal/autocal
```

## Output Deliverables

Output files are placed in `calibration/energy/run/`:
- `calibration.csv`: Calibration polynomial coefficients (`a0`, `a1`, `a2`), parameter errors, `chi2/ndf`, peak count, energy range, RMS residual, max residual, and channel status.
- `histograms.root`: Channel raw histograms containing serialized `TF1` peak fit functions.
- `figures/cid<C>_sid<S>_ch<H>.png`: Three-panel inspection figures for all discovered channels.
