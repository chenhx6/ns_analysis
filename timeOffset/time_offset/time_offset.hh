#ifndef TIME_OFFSET_HH
#define TIME_OFFSET_HH

#include <RtypesCore.h>
#include <TH1D.h>
#include <array>
#include <memory>
#include <string>
#include <vector>

constexpr int Channels = 2 * 17 * 16;
constexpr int Reference = 2 * 16 + 5; // cid=0, sid=2, ch=5.
constexpr Long64_t Window = 1999;     // ns, relative to the first accepted hit.

struct Hit
{
    Long64_t ts = 0;
    Short_t cid = 0, sid = 0, ch = 0, sr = 0;
};
struct Spectrum
{
    std::unique_ptr<TH1D> fine, coarse;
    Long64_t hits = 0;
};

// One input tree, fixed-start event grouping, spectra and ROOT fits.
class TimeOffset
{
public:
    void Process(int run, const std::string &input, const std::string &output,
                 Long64_t limit = 0);
    static void SelfCheck();

private:
    void AddHit(int channel, Long64_t ns);
    void EndEvent();
    void Fill(int channel, Long64_t dt);
    void FitAndWrite(const std::string &csv);
    std::array<Spectrum, Channels> spectra;
    std::array<Long64_t, 17 * 16> ge{};
    std::array<bool, 17 * 16> present{};
    std::vector<std::pair<int, Long64_t>> csi;
    Long64_t start = 0, previous = 0;
    bool active = false;
    Long64_t events = 0, references = 0, regressions = 0, rejected = 0;
};
#endif
