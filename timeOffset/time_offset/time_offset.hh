#ifndef TIME_OFFSET_HH
#define TIME_OFFSET_HH
#include "UserDefine.hh"
#include <RtypesCore.h>
#include <TH1D.h>
#include <array>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <tuple>
#include <vector>

struct Address {
    int cid, sid, ch;
    bool operator<(const Address &b) const { return std::tie(cid,sid,ch)<std::tie(b.cid,b.sid,b.ch); }
    bool operator==(const Address &b) const { return cid==b.cid && sid==b.sid && ch==b.ch; }
};
struct Hit { Long64_t ts=0; Short_t cid=0,sid=0,ch=0,sr=0; };
struct Spectrum {
    std::unique_ptr<TH1D> fine, coarse;
    Long64_t hits=0;
    std::set<int> ticks;
};

// 单输入、固定起点事件包及双分箱谱；测试入口复用同一处理路径。
class TimeOffset {
public:
    void Process(int run);
    void Process(int run, const std::string &input, const std::string &output,
                 Long64_t limit=0, bool fit=UserDefine::FIT_ENABLED);
    static void SelfCheck();
    static void InspectSpectrum(const std::string &file,const std::string &name);
private:
    void ProcessEntry(Address address, Long64_t ns, int tick);
    void EndEvent();
    void Fill(Address address, Long64_t dt);
    void Write(int run, const std::string &input, const std::string &output, bool fit);
    std::map<Address,Spectrum> spectra;
    std::map<Address,Long64_t> ge;
    std::vector<std::pair<Address,Long64_t>> csi;
    bool active=false, have_reference=false;
    Long64_t start=0, reference_time=0, previous=0;
    Long64_t input_entries=0, processed=0, accepted=0, rejected=0;
    Long64_t events=0, reference_events=0, reference_hits=0, regressions=0;
};
#endif
