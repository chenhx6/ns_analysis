#ifndef TIME_OFFSET_HH
#define TIME_OFFSET_HH

#include <RtypesCore.h>
#include <array>
#include <cstdint>
#include <deque>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <vector>

namespace time_offset {
constexpr Long64_t WindowNs = 1999;
constexpr int StatisticalBlocks = 16;
struct Hit {
    Long64_t ts = 0;
    Short_t cid = 0, sid = 0, ch = 0, sr = 0;
};
struct Address {
    int cid = 0, sid = 0, ch = 0;
    bool operator<(const Address& rhs) const { return std::tie(cid,sid,ch) < std::tie(rhs.cid,rhs.sid,rhs.ch); }
    bool operator==(const Address& rhs) const { return std::tie(cid,sid,ch) == std::tie(rhs.cid,rhs.sid,rhs.ch); }
    std::string name() const;
};
const Address Reference{0,2,5};
struct Slice {
    std::string file, id, group;
    int ge_run = 0, csi_run = 0;
    Long64_t begin = 0, end = 0, core_begin = 0, core_end = 0;
    Long64_t chunk = 100000, max_gap_ns = 1000000000, subslice_entries = 0;
    bool synthetic = false, ordered_blocks = true;
    Long64_t statistical_begin_ns = -1, statistical_end_ns = -1;
    std::string candidate_policy = "weighted";
};
struct Spectrum {
    std::array<std::uint64_t,1999> fine{};
    std::array<std::uint64_t,167> coarse{};
    std::array<std::array<std::uint64_t,1999>,StatisticalBlocks> blocks{};
    std::map<int,std::uint64_t> rates;
    std::uint64_t observed = 0, pairs = 0;
    void fill(Long64_t delta, int block = -1);
};
struct Diagnostics {
    bool valid = true;
    std::string reason;
    Long64_t invalid_entry = -1, previous_ns = 0, invalid_ns = 0;
    Long64_t tree_entries = 0, first_ns = 0, last_ns = 0, core_first_ns = -1, core_last_ns = -1;
    int tree_cycle = 0;
    std::uint64_t entries = 0, filtered = 0, unknown_sr = 0;
    std::uint64_t core_references = 0, excluded_edge_references = 0;
    std::map<int,std::uint64_t> reference_rates;
};
struct SliceResult {
    Slice source;
    Diagnostics diagnostics;
    std::map<Address,Spectrum> spectra;
    std::string slice_log;
};
struct TimedHit { Long64_t ns; Address address; bool core; int block = -1; };

class TimeOffsetProcessor {
public:
    static int tick(int sr);
    static bool convert(Long64_t ts, int q, Long64_t& ns);
    static bool accepted(const Hit& hit);
    static int quantize(double mu, int tick_ns);
    static std::vector<int> quantization_candidates(double mu,int tick_ns);
    static int effective(int value_ns, int tick_ns);
    SliceResult read(const Slice& slice) const;
    SliceResult process(const Slice& slice, const std::vector<Hit>& hits) const;
    static void save(const SliceResult& result, const std::string& output);
    static bool verify(const std::string& path);
    static SliceResult load(const std::string& path);
    static void self_test(const std::string& directory);
private:
    SliceResult read_slice(const Slice& slice,bool preflight_only) const;
    static bool inspect(const Hit& hit, Long64_t entry, SliceResult& result, bool& have_time);
    static void pair(const Hit& hit, Long64_t entry, SliceResult& result,
                     std::deque<TimedHit>& refs, std::deque<TimedHit>& targets);
};
struct PeakWindow {
    double low = -600, high = 600, left_low = -1800, left_high = -1200, right_low = 1200, right_high = 1800;
};
struct Estimate {
    bool passed = false;
    std::string reason = "not_estimated";
    double net = 0, background = 0, background_variance = 0, variance = 0, poisson_variance = 0;
    double mu = 0, mu_error = 0, snr = 0, background_p = 0, background_chi2 = 0;
    double perturbation = 0, block_chi2 = 0, block_p = 0;
    int signal_sites = 0, side_sites = 0, usable_blocks = 0;
    std::array<double,3> gates{}, gate_errors{}, uncorrected_gates{};
};
struct TemplateRow {
    Address address;
    int offset = 0, low = 0, high = 0;
    std::string raw;
};
struct CrateTemplate {
    std::string path, header, text;
    std::vector<TemplateRow> rows;
};
class Calibration {
public:
    static Estimate estimate(const Spectrum&, const PeakWindow&, int lattice, int tick, bool perturb = true);
    static CrateTemplate read_template(const std::string&, int cid);
    static void freeze(const std::string& training, const std::string& windows,
                       const std::string& template0, const std::string& template1,
                       const Slice& holdout, const std::string& output);
    static void validate(const std::string& frozen, const std::string& output_directory);
    static bool verify(const std::string& directory);
    static void suggest(const std::string& training, const std::string& output);
    static void preview(const std::string&,const std::string&,const std::string&,const std::string&,const std::string&);
    static bool mission(const std::string& manifest,const std::string& output);
    static void combine(const std::string& manifest,const std::string& output);
    static void provenance(const std::string& manifest,const std::string& output);
    static void summarize(const std::string& manifest,const std::string& output);
    static void self_test(const std::string& directory);
};
}
#endif
