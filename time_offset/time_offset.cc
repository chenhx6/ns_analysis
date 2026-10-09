#include "time_offset.hh"
#include <TFile.h>
#include <TTree.h>
#include <TLeaf.h>
#include <TKey.h>
#include <TH1D.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TF1.h>
#include <TFitResult.h>
#include <TFitResultPtr.h>
#include <TMath.h>
#include <TMD5.h>
#include <TH2D.h>
#include <iomanip>
#include <cctype>
#include <random>
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <cerrno>
#include <cstdio>

namespace fs = std::filesystem;
namespace time_offset {
namespace {
void require(bool condition, const std::string& text) {
    if (!condition) throw std::runtime_error(text);
}
void new_path(const std::string& path) {
    require(!fs::exists(path) && !fs::is_symlink(path), "refusing existing output: " + path);
    require(fs::exists(fs::path(path).parent_path().empty() ? fs::path(".") : fs::path(path).parent_path()), "output parent missing");
}
void bind(TTree& tree, Hit& hit) {
    tree.SetBranchStatus("*", 0);
    for (const char* name : {"ts", "cid", "sid", "ch", "sr"}) {
        TLeaf* leaf = tree.GetLeaf(name);
        const std::string type = std::string(name)=="ts" ? "Long64_t" : "Short_t";
        require(leaf && leaf->GetTypeName()==type && leaf->GetLenStatic()==1 && !leaf->GetLeafCount(), "invalid scalar branch: " + std::string(name));
        tree.SetBranchStatus(name,1);
    }
    require(tree.SetBranchAddress("ts",&hit.ts)>=0 && tree.SetBranchAddress("cid",&hit.cid)>=0 &&
            tree.SetBranchAddress("sid",&hit.sid)>=0 && tree.SetBranchAddress("ch",&hit.ch)>=0 &&
            tree.SetBranchAddress("sr",&hit.sr)>=0, "cannot bind branches");
}
void validate_slice(const Slice& s, Long64_t entries) {
    require(!s.id.empty() && !s.group.empty() && s.ge_run>0 && s.csi_run>0, "explicit slice/group/Ge/CsI identity required");
    require(s.begin>=0 && s.begin<s.end && s.end<=entries && s.core_begin>=s.begin &&
            s.core_begin<s.core_end && s.core_end<=s.end, "invalid read/core entry intervals");
    require(s.chunk>0 && s.max_gap_ns>=WindowNs, "invalid chunk/max-gap-ns");
}
void invalid(SliceResult& r, Long64_t entry, Long64_t ns, const std::string& reason) {
    r.diagnostics.valid=false;
    r.diagnostics.reason=reason;
    r.diagnostics.invalid_entry=entry;
    r.diagnostics.invalid_ns=ns;
    r.diagnostics.previous_ns=r.diagnostics.last_ns;
}
std::string manifest(const SliceResult& r) {
    const auto& s=r.source;
    const auto& d=r.diagnostics;
    std::ostringstream o;
    o << "format=1\nsource=" << fs::absolute(s.file).lexically_normal().string()
      << "\nslice=" << s.id << "\ngroup=" << s.group << "\nge_run=" << s.ge_run << "\ncsi_run=" << s.csi_run
      << "\nread_begin=" << s.begin << "\nread_end=" << s.end << "\ncore_begin=" << s.core_begin << "\ncore_end=" << s.core_end
      << "\nordered_blocks=" << s.ordered_blocks << "\nstatistical_begin_ns=" << s.statistical_begin_ns << "\nstatistical_end_ns=" << s.statistical_end_ns
      << "\ncandidate_policy=" << s.candidate_policy
      << "\nchunk=" << s.chunk << "\nsubslice_entries=" << s.subslice_entries << "\nmax_gap_ns=" << s.max_gap_ns << "\nsynthetic=" << s.synthetic
      << "\nvalid=" << d.valid << "\nreason=" << d.reason << "\ninvalid_entry=" << d.invalid_entry
      << "\nprevious_ns=" << d.previous_ns << "\ninvalid_ns=" << d.invalid_ns
      << "\nfirst_ns=" << d.first_ns << "\nlast_ns=" << d.last_ns
      << "\ncore_first_ns=" << d.core_first_ns << "\ncore_last_ns=" << d.core_last_ns
      << "\ntree_entries=" << d.tree_entries << "\ntree_cycle=" << d.tree_cycle
      << "\nentries=" << d.entries << "\nfiltered=" << d.filtered << "\nunknown_sr=" << d.unknown_sr
      << "\ncore_references=" << d.core_references << "\nexcluded_edge_references=" << d.excluded_edge_references
      << "\nreference=0:2:5\ndelta=reference-channel\nwindow_ns=1999\nstatus=diagnostic\n";
    return o.str();
}
void same_spectra(const SliceResult& a, const SliceResult& b) {
    require(a.spectra.size()==b.spectra.size(), "chunk address mismatch");
    for (const auto& item : a.spectra) {
        const auto& rhs=b.spectra.at(item.first);
        require(item.second.fine==rhs.fine && item.second.coarse==rhs.coarse && item.second.pairs==rhs.pairs && item.second.blocks==rhs.blocks,
                "chunk spectra mismatch");
    }
}
}
std::string Address::name() const { return "c"+std::to_string(cid)+"_s"+std::to_string(sid)+"_ch"+std::to_string(ch); }
int TimeOffsetProcessor::tick(int sr) {
    if(sr==125 || sr==250) return 8;
    if(sr==100 || sr==500) return 10;
    return 0;
}
bool TimeOffsetProcessor::convert(Long64_t ts, int q, Long64_t& ns) {
    if(q<=0 || ts<0 || ts>std::numeric_limits<Long64_t>::max()/q) return false;
    ns=ts*q;
    return true;
}
bool TimeOffsetProcessor::accepted(const Hit& h) { return (h.cid==0 || h.cid==1) && h.sid>=2 && h.ch>=0 && h.ch<16; }
int TimeOffsetProcessor::effective(int value, int q) {
    require(q==8 || q==10, "unsupported tick");
    return (value/q)*q; // C++ signed integer division truncates toward zero.
}
int TimeOffsetProcessor::quantize(double mu, int q) {
    require((q==8 || q==10) && std::isfinite(mu), "invalid quantization input");
    const double value=std::round(mu/q)*q;
    require(value>=-32768 && value<=32767, "offset exceeds signed 16-bit");
    return static_cast<int>(value);
}
std::vector<int> TimeOffsetProcessor::quantization_candidates(double mu,int q) {
    const int nearest=quantize(mu,q);
    const double low=std::floor(mu/q)*q,high=low+q;
    if(std::abs((mu-low)-(high-mu))<=1e-10 && low>=-32768 && high<=32767)return {int(low),int(high)};
    return {nearest};
}
void Spectrum::fill(Long64_t delta, int block) {
    require(delta>=-WindowNs && delta<=WindowNs && delta%2==0, "unreachable delta");
    ++fine.at(static_cast<std::size_t>((delta+1999)/2));
    ++coarse.at(static_cast<std::size_t>((delta+2004)/24));
    ++pairs;
    if(block>=0) ++blocks.at(block).at(static_cast<std::size_t>((delta+1999)/2));
}
bool TimeOffsetProcessor::inspect(const Hit& h, Long64_t entry, SliceResult& r, bool& have_time) {
    auto& d=r.diagnostics;
    ++d.entries;
    if(!accepted(h)) { ++d.filtered; return true; }
    const Address address{h.cid,h.sid,h.ch};
    auto& spectrum=r.spectra[address];
    ++spectrum.observed;
    ++spectrum.rates[h.sr];
    const int q=tick(h.sr);
    if(!q) { ++d.unknown_sr; return true; }
    Long64_t ns=0;
    if(!convert(h.ts,q,ns)) { invalid(r,entry,0,"negative_or_overflow_timestamp"); return false; }
    if(have_time && (ns<d.last_ns || ns-d.last_ns>r.source.max_gap_ns)) {
        invalid(r,entry,ns,ns<d.last_ns?"time_regression":"time_gap_exceeded");
        return false;
    }
    if(!have_time) { d.first_ns=ns; have_time=true; }
    d.last_ns=ns;
    if(entry>=r.source.core_begin && entry<r.source.core_end) {
        if(d.core_first_ns<0) d.core_first_ns=ns;
        d.core_last_ns=ns;
    }
    if(address==Reference) ++d.reference_rates[h.sr];
    return true;
}
void TimeOffsetProcessor::pair(const Hit& h, Long64_t entry, SliceResult& r,
                               std::deque<TimedHit>& refs, std::deque<TimedHit>& targets) {
    if(!accepted(h) || !tick(h.sr)) return;
    Long64_t ns=0;
    require(convert(h.ts,tick(h.sr),ns), "validated timestamp changed");
    while(!refs.empty() && ns-refs.front().ns>WindowNs) refs.pop_front();
    while(!targets.empty() && ns-targets.front().ns>WindowNs) targets.pop_front();
    const Address address{h.cid,h.sid,h.ch};
    if(address==Reference) {
        const bool requested=entry>=r.source.core_begin && entry<r.source.core_end;
        const bool guarded=ns-r.diagnostics.first_ns>=WindowNs && r.diagnostics.last_ns-ns>=WindowNs;
        if(requested && !guarded) ++r.diagnostics.excluded_edge_references;
        const bool core=requested && guarded;
        int block=-1;
        const auto block_begin=r.source.statistical_begin_ns>=0?r.source.statistical_begin_ns:r.diagnostics.core_first_ns;
        const auto block_end=r.source.statistical_end_ns>=0?r.source.statistical_end_ns:r.diagnostics.core_last_ns;
        const auto width=(block_end-block_begin)/StatisticalBlocks;
        if(core && width>4*WindowNs) {
            const auto relative=ns-block_begin;
            const auto index=relative/width;
            if(relative>=0 && index<StatisticalBlocks && relative%width>=WindowNs && width-relative%width>WindowNs) block=index;
        }
        if(core) {
            ++r.diagnostics.core_references;
            for(const auto& target:targets) r.spectra.at(target.address).fill(ns-target.ns,block);
        }
        refs.push_back({ns,address,core,block});
    } else {
        for(const auto& ref:refs) if(ref.core) r.spectra.at(address).fill(ref.ns-ns,ref.block);
        targets.push_back({ns,address,false});
    }
}
SliceResult TimeOffsetProcessor::process(const Slice& s, const std::vector<Hit>& hits) const {
    validate_slice(s,static_cast<Long64_t>(hits.size()));
    SliceResult r;
    r.source=s; r.diagnostics.tree_entries=hits.size();
    bool have_time=false;
    for(Long64_t i=s.begin;i<s.end;++i) if(!inspect(hits[i],i,r,have_time)) return r;
    if(!have_time) { invalid(r,s.begin,0,"no_supported_time"); return r; }
    if(r.source.statistical_begin_ns<0){r.source.statistical_begin_ns=r.diagnostics.core_first_ns;r.source.statistical_end_ns=r.diagnostics.core_last_ns;}
    std::deque<TimedHit> refs,targets;
    for(Long64_t chunk=s.begin;chunk<s.end;) {
        const auto end=chunk+std::min(s.chunk,s.end-chunk);
        for(Long64_t i=chunk;i<end;++i) pair(hits[i],i,r,refs,targets);
        chunk=end;
    }
    if(!r.diagnostics.core_references) r.diagnostics.reason="missing_guarded_core_reference";
    return r;
}
SliceResult TimeOffsetProcessor::read(const Slice& s) const {
    if(s.subslice_entries<=0)return read_slice(s,false);
    require(s.subslice_entries>=1000,"subslice must have at least 1000 entries");
    struct CheckedSlice { Slice slice;Diagnostics diagnostics;bool synthetic=false; };
    std::vector<CheckedSlice> checked;
    Long64_t first=-1,last=-1;
    for(Long64_t start=s.begin;start<s.end;) {
        Slice part=s;part.begin=start;part.end=start+std::min(s.subslice_entries,s.end-start);part.subslice_entries=0;
        part.core_begin=std::max(part.begin,s.core_begin);part.core_end=std::min(part.end,s.core_end);
        if(part.core_begin>=part.core_end){start=part.end;continue;}
        part.id=s.id+"-"+std::to_string(start);
        const auto inspected=read_slice(part,true);auto diagnostic=inspected.diagnostics;
        if(diagnostic.valid && last>=0 && diagnostic.core_first_ns<last) {
            diagnostic.valid=false;diagnostic.reason="valid_core_time_overlap_or_regression";diagnostic.invalid_entry=part.core_begin;
        }
        if(diagnostic.valid) {if(first<0)first=diagnostic.core_first_ns;last=diagnostic.core_last_ns;}
        checked.push_back({part,diagnostic,inspected.source.synthetic});start=part.end;
    }
    SliceResult merged;merged.source=s;merged.source.statistical_begin_ns=first;merged.source.statistical_end_ns=last;
    bool have_valid=false;std::ostringstream log;
    for(const auto& inspected:checked) {
        auto part=inspected.slice;
        // One common chronological axis for all valid slices. Never fold slice-relative bin k together.
        part.statistical_begin_ns=first;part.statistical_end_ns=last;
        const auto& diagnostic=inspected.diagnostics;
        merged.diagnostics.entries+=diagnostic.entries;merged.diagnostics.tree_entries=diagnostic.tree_entries;
        merged.diagnostics.tree_cycle=diagnostic.tree_cycle;merged.source.synthetic=inspected.synthetic;
        std::uint64_t pairs=0;
        if(diagnostic.valid) {
            const auto current=read_slice(part,false);
            require(current.diagnostics.valid && current.diagnostics.first_ns==diagnostic.first_ns && current.diagnostics.last_ns==diagnostic.last_ns,
                    "input changed after whole-grid preflight");
            if(!have_valid){merged.diagnostics.first_ns=diagnostic.first_ns;merged.diagnostics.core_first_ns=diagnostic.core_first_ns;have_valid=true;}
            merged.diagnostics.last_ns=diagnostic.last_ns;merged.diagnostics.core_last_ns=diagnostic.core_last_ns;
            merged.diagnostics.filtered+=diagnostic.filtered;merged.diagnostics.unknown_sr+=diagnostic.unknown_sr;
            merged.diagnostics.core_references+=current.diagnostics.core_references;merged.diagnostics.excluded_edge_references+=current.diagnostics.excluded_edge_references;
            for(const auto& entry:current.spectra) {
                auto& target=merged.spectra[entry.first];const auto& src=entry.second;
                target.observed+=src.observed;target.pairs+=src.pairs;pairs+=src.pairs;
                for(const auto& rate:src.rates)target.rates[rate.first]+=rate.second;
                for(int i=0;i<1999;++i){target.fine[i]+=src.fine[i];for(int k=0;k<StatisticalBlocks;++k)target.blocks[k][i]+=src.blocks[k][i];}
                for(int i=0;i<167;++i)target.coarse[i]+=src.coarse[i];
            }
        }
        log<<part.begin<<' '<<part.end<<' '<<diagnostic.valid<<' '<<pairs<<' '<<diagnostic.invalid_entry<<' '<<std::quoted(diagnostic.reason)<<'\n';
    }
    merged.slice_log=log.str();merged.diagnostics.valid=have_valid;if(!have_valid)merged.diagnostics.reason="no_valid_grid_slices";
    return merged;
}
SliceResult TimeOffsetProcessor::read_slice(const Slice& s,bool preflight_only) const {
    std::unique_ptr<TFile> file(TFile::Open(s.file.c_str(),"READ"));
    require(file && !file->IsZombie(), "cannot read ROOT: "+s.file);
    auto* tree=dynamic_cast<TTree*>(file->Get("tree")); // ROOT resolves latest cycle.
    require(tree, "missing tree");
    validate_slice(s,tree->GetEntries());
    SliceResult r;
    r.source=s; r.diagnostics.tree_entries=tree->GetEntries();
    if(auto* provenance=dynamic_cast<TNamed*>(file->Get("provenance")))
        if(std::string(provenance->GetTitle()).find("synthetic")!=std::string::npos) r.source.synthetic=true;
    auto* key=file->GetKey("tree");
    require(key,"missing tree key"); r.diagnostics.tree_cycle=key->GetCycle();
    Hit hit;
    bind(*tree,hit);
    bool have_time=false;
    // A bounded-memory preflight precedes any watermark/cache or histogram mutation.
    // Invalid slices therefore never contribute partial spectra, including future outliers.
    for(Long64_t i=s.begin;i<s.end;++i) {
        require(tree->GetEntry(i)>0,"entry read failed");
        if(!inspect(hit,i,r,have_time)) return r;
    }
    if(!have_time) { invalid(r,s.begin,0,"no_supported_time"); return r; }
    if(r.source.statistical_begin_ns<0){r.source.statistical_begin_ns=r.diagnostics.core_first_ns;r.source.statistical_end_ns=r.diagnostics.core_last_ns;}
    if(preflight_only)return r;
    std::deque<TimedHit> refs,targets;
    for(Long64_t chunk=s.begin;chunk<s.end;) {
        const auto end=chunk+std::min(s.chunk,s.end-chunk);
        for(Long64_t i=chunk;i<end;++i) {
            require(tree->GetEntry(i)>0,"entry reread failed");
            pair(hit,i,r,refs,targets);
        }
        chunk=end;
    }
    if(!r.diagnostics.core_references) r.diagnostics.reason="missing_guarded_core_reference";
    return r;
}
void TimeOffsetProcessor::save(const SliceResult& r, const std::string& output) {
    new_path(output);
    TFile file(output.c_str(),"CREATE");
    require(!file.IsZombie(),"cannot create output ROOT");
    TNamed info("manifest",manifest(r).c_str()); info.Write();
    TNamed log("slice_log",r.slice_log.c_str());log.Write();
    TNamed meaning("uncertainty","all pairs diagnostic; blocks_2ns use 16 equal-time core subblocks with 1999ns edge exclusion; empirical block covariance and Poisson floor evaluated only by calibration"); meaning.Write();
    TTree metadata("channels","observed addresses and sampling rates");
    Int_t cid=0,sid=0,ch=0,sr=0;
    ULong64_t observed=0,pairs=0;
    metadata.Branch("cid",&cid,"cid/I"); metadata.Branch("sid",&sid,"sid/I"); metadata.Branch("ch",&ch,"ch/I");
    metadata.Branch("sr",&sr,"sr/I"); metadata.Branch("observed",&observed,"observed/l"); metadata.Branch("pairs",&pairs,"pairs/l");
    for(const auto& item:r.spectra) {
        const auto& a=item.first; const auto& s=item.second;
        cid=a.cid; sid=a.sid; ch=a.ch; pairs=s.pairs;
        for(const auto& rate:s.rates) { sr=rate.first; observed=rate.second; metadata.Fill(); }
        const auto name=a.name();
        TH1D fine((name+"_2ns").c_str(),"Delta t = reference - channel;Delta t (ns);Candidate pairs / 2 ns",1999,-1999,1999);
        TH1D coarse((name+"_24ns").c_str(),"Delta t = reference - channel;Delta t (ns);Candidate pairs / 24 ns",167,-2004,2004);
        for(std::size_t i=0;i<s.fine.size();++i) fine.SetBinContent(i+1,s.fine[i]);
        for(std::size_t i=0;i<s.coarse.size();++i) coarse.SetBinContent(i+1,s.coarse[i]);
        TH2D blocks((name+"_blocks_2ns").c_str(),"Separated statistical subcores;Delta t (ns);Subcore",1999,-1999,1999,StatisticalBlocks,0,StatisticalBlocks);
        for(int k=0;k<StatisticalBlocks;++k) for(int j=0;j<1999;++j) blocks.SetBinContent(j+1,k+1,s.blocks[k][j]);
        blocks.Write();
        fine.SetEntries(s.pairs); coarse.SetEntries(s.pairs);
        fine.Write(); coarse.Write();
    }
    metadata.Write();
    file.Close();
}
bool TimeOffsetProcessor::verify(const std::string& path) {
    TFile file(path.c_str(),"READ");
    require(!file.IsZombie(),"invalid artifact ROOT");
    auto* info=dynamic_cast<TNamed*>(file.Get("manifest"));
    auto* channels=dynamic_cast<TTree*>(file.Get("channels"));
    require(info && channels,"missing manifest/channel metadata");
    const std::string description=info->GetTitle();
    require(description.find("reference=0:2:5\n")!=std::string::npos && description.find("status=diagnostic\n")!=std::string::npos,"wrong artifact contract");
    const bool invalid_slice=description.find("valid=0\n")!=std::string::npos;
    Int_t cid=0,sid=0,ch=0,sr=0; ULong64_t observed=0,pairs=0;
    channels->SetBranchAddress("cid",&cid); channels->SetBranchAddress("sid",&sid); channels->SetBranchAddress("ch",&ch);
    channels->SetBranchAddress("sr",&sr); channels->SetBranchAddress("observed",&observed); channels->SetBranchAddress("pairs",&pairs);
    std::map<Address,std::set<int>> rates;
    std::map<Address,ULong64_t> counts;
    for(Long64_t i=0;i<channels->GetEntries();++i) {
        require(channels->GetEntry(i)>0,"bad metadata entry");
        Address a{cid,sid,ch};
        require(observed>0 && rates[a].insert(sr).second,"duplicate/empty sampling-rate row");
        if(counts.count(a)) require(counts[a]==pairs,"rate rows disagree on pair count");
        counts[a]=pairs;
    }
    for(const auto& item:rates) {
        const auto name=item.first.name();
        auto* fine=dynamic_cast<TH1D*>(file.Get((name+"_2ns").c_str()));
        auto* coarse=dynamic_cast<TH1D*>(file.Get((name+"_24ns").c_str()));
        require(fine && coarse && fine->GetNbinsX()==1999 && coarse->GetNbinsX()==167,"missing/wrong histograms");
        require(fine->GetXaxis()->GetXmin()==-1999 && fine->GetXaxis()->GetXmax()==1999 &&
                coarse->GetXaxis()->GetXmin()==-2004 && coarse->GetXaxis()->GetXmax()==2004,"wrong bin edges");
        require(fine->GetBinContent(0)==0 && fine->GetBinContent(2000)==0 && coarse->GetBinContent(0)==0 && coarse->GetBinContent(168)==0,"overflow bins nonzero");
        auto* blocks=dynamic_cast<TH2D*>(file.Get((name+"_blocks_2ns").c_str()));
        require(blocks && blocks->GetNbinsX()==1999 && blocks->GetNbinsY()==StatisticalBlocks,"missing statistical blocks");
        std::array<double,167> rebinned{};
        double sum=0;
        for(int b=1;b<=1999;++b) {
            const double y=fine->GetBinContent(b), x=fine->GetBinCenter(b);
            require(std::isfinite(y) && y>=0 && std::floor(y)==y,"noninteger/negative pair count");
            double subcounts=0;
            for(int k=1;k<=StatisticalBlocks;++k) {
                const double n=blocks->GetBinContent(b,k);
                require(std::isfinite(n) && n>=0 && std::floor(n)==n,"bad subcore count"); subcounts+=n;
            }
            require(subcounts<=y,"subcore counts exceed full pairs");
            rebinned.at(coarse->FindBin(x)-1)+=y; sum+=y;
        }
        for(int b=1;b<=167;++b) require(rebinned[b-1]==coarse->GetBinContent(b),"2/24 ns pair populations disagree");
        require(sum==static_cast<double>(counts[item.first]),"metadata pair count disagrees");
        require(!invalid_slice || sum==0,"invalid slice contributed counts");
        require(!(item.first==Reference) || sum==0,"reference self-pairs present");
    }
    if(auto* log=dynamic_cast<TNamed*>(file.Get("slice_log"))) {
        if(std::string(log->GetTitle()).size()) {
            std::istringstream rows(log->GetTitle());Long64_t begin=0,end=0,error=0,last_end=-1;bool valid=false;std::uint64_t pairs=0,total=0;std::string reason;
            while(rows>>begin>>end>>valid>>pairs>>error>>std::quoted(reason)) {
                require(begin<end && begin>=last_end && (valid || pairs==0),"invalid grid slice evidence");last_end=end;total+=pairs;
            }
            std::uint64_t expected=0;for(const auto& item:counts)expected+=item.second;
            require(total==expected,"grid valid-slice count sum mismatch");
        }
    }
    return true;
}
void TimeOffsetProcessor::self_test(const std::string& directory) {
    require(!fs::exists(directory),"self-test directory must be new");
    fs::create_directories(directory);
    std::vector<std::string> passed;
    auto check=[&](bool condition,const std::string& name) { require(condition,"self-test failed: "+name); passed.push_back(name); };
    check(tick(100)==10 && tick(500)==10 && tick(125)==8 && tick(250)==8 && tick(1)==0,"sampling_rate_mapping");
    Long64_t ns=0;
    check(convert(12,8,ns) && ns==96 && !convert(-1,8,ns) && !convert(std::numeric_limits<Long64_t>::max(),10,ns),"timestamp_checked_conversion");
    check(effective(-22,8)==-16 && effective(22,8)==16 && quantize(-22,8)==-24 && quantize(22,8)==24,"signed_quantization");
    bool throws=false; try { quantize(40000,8); } catch(const std::exception&) { throws=true; }
    check(throws,"signed16_rejection");
    std::vector<Hit> hits{{0,0,2,0,250},{375,0,2,0,250},{390,0,2,5,250},{400,1,2,0,500},{800,0,2,0,250}};
    Slice s; s.file=directory+"/synthetic.root"; s.id="synthetic-1"; s.group="synthetic"; s.ge_run=1; s.csi_run=1;
    s.begin=0; s.end=hits.size(); s.core_begin=1; s.core_end=4; s.synthetic=true;
    TimeOffsetProcessor processor;
    const auto one=processor.process(s,hits);
    auto split=s; split.chunk=1;
    const auto many=processor.process(split,hits); same_spectra(one,many);
    check(one.spectra.at({0,2,0}).pairs==1 && one.spectra.at({1,2,0}).pairs==1,"all_pairs_and_chunk_equivalence");
    check(one.spectra.at({0,2,0}).fine.at((120+1999)/2)==1 && one.spectra.at({1,2,0}).fine.at((-880+1999)/2)==1,"delta_sign_mixed_tick");
    auto second=s; second.id="synthetic-2"; second.ge_run=2;
    auto no_ref=hits; no_ref[2].ch=1;
    const auto isolated=processor.process(second,no_ref);
    check(isolated.diagnostics.core_references==0 && isolated.spectra.at({0,2,0}).pairs==0,"cross_run_slice_cache_reset");
    auto bad=hits; bad[3].ts=std::numeric_limits<Long64_t>::max()/100;
    const auto future=processor.process(s,bad);
    check(!future.diagnostics.valid && future.diagnostics.invalid_entry==3 && future.diagnostics.last_ns==3120 && future.spectra.at({0,2,0}).pairs==0,"future_outlier_no_watermark_or_counts");
    bad=hits; bad[3].ts=1;
    check(!processor.process(s,bad).diagnostics.valid,"regression_invalidates_slice");
    bad=hits; bad[3].ts=std::numeric_limits<Long64_t>::max();
    check(!processor.process(s,bad).diagnostics.valid,"overflow_invalidates_slice");
    bad=hits; bad[3].sr=123;
    const auto unknown=processor.process(s,bad);
    check(unknown.diagnostics.unknown_sr==1 && unknown.spectra.at({1,2,0}).pairs==0,"unknown_rate_no_guessed_tick");
    auto edge=hits; edge[0]={0,0,2,5,250}; edge[4]={800,0,2,5,250};
    auto full=s; full.core_begin=0; full.core_end=5;
    const auto guarded=processor.process(full,edge);
    check(guarded.diagnostics.excluded_edge_references==2 && guarded.diagnostics.core_references==1,"insufficient_edge_guard_excluded");
    // A guard reference is never counted, even though its target partners are read.
    auto only_guard=s; only_guard.core_begin=3; only_guard.core_end=4;
    check(processor.process(only_guard,hits).spectra.at({0,2,0}).pairs==0,"guard_reference_never_counted");
    // Exhaustive all-pairs oracle uses the same core and guard policy, but no streaming cache.
    std::vector<Hit> oracle_hits;
    for(int i=0;i<350;++i) {
        const Long64_t t=i*40;
        if(i%7==0) oracle_hits.push_back({t/8,0,2,5,250});
        if(i%3==0) oracle_hits.push_back({t/8,0,3,1,125});
        if(i%4==0) oracle_hits.push_back({t/10,1,3,2,100});
    }
    auto os=s; os.end=oracle_hits.size(); os.core_begin=10; os.core_end=os.end-10;
    const auto streamed=processor.process(os,oracle_hits);
    std::map<Address,Spectrum> brute;
    for(Long64_t i=os.core_begin;i<os.core_end;++i) {
        const auto& ref=oracle_hits[i];
        if(!(Address{ref.cid,ref.sid,ref.ch}==Reference)) continue;
        const auto t=ref.ts*tick(ref.sr);
        if(t-streamed.diagnostics.first_ns<WindowNs || streamed.diagnostics.last_ns-t<WindowNs) continue;
        for(const auto& target:oracle_hits) {
            const Address a{target.cid,target.sid,target.ch};
            if(a==Reference) continue;
            const auto delta=t-target.ts*tick(target.sr);
            if(std::abs(delta)<=WindowNs) brute[a].fill(delta);
        }
    }
    for(const auto& item:brute) {
        const auto& actual=streamed.spectra.at(item.first);
        check(actual.fine==item.second.fine && actual.coarse==item.second.coarse,"all_pairs_bruteforce_"+item.first.name());
    }
    for(const auto chunk:{1,2,7,29,1000}) {
        os.chunk=chunk; same_spectra(streamed,processor.process(os,oracle_hits));
    }
    check(true,"arbitrary_chunk_partition_invariance");
    auto restored=processor.process(s,hits);
    same_spectra(one,restored);
    check(restored.diagnostics.valid,"new_slice_recovers_after_rejected_slice");
    auto mixed=hits; mixed[4].sr=125;
    check(processor.process(s,mixed).spectra.at({0,2,0}).rates.size()==2,"mixed_sr_same_tick_retained");
    Spectrum boundary; boundary.fill(-1998); boundary.fill(1998);
    check(boundary.pairs==2 && boundary.fine.front()==1 && boundary.fine.back()==1,"reachable_window_boundaries");
    {
        TFile file(s.file.c_str(),"CREATE");
        TNamed label("provenance","synthetic engineering fixture, not experimental evidence"); label.Write();
        TTree tree("tree","synthetic hits"); Hit h;
        tree.Branch("ts",&h.ts,"ts/L"); tree.Branch("cid",&h.cid,"cid/S"); tree.Branch("sid",&h.sid,"sid/S");
        tree.Branch("ch",&h.ch,"ch/S"); tree.Branch("sr",&h.sr,"sr/S");
        for(std::size_t i=0;i<hits.size();++i) { h=hits[i]; tree.Fill(); if(i==1) tree.Write(); }
        tree.Write();
    }
    const auto readback=processor.read(split); same_spectra(one,readback);
    check(readback.diagnostics.tree_cycle==2 && readback.diagnostics.tree_entries==5,"latest_cycle_and_scalar_schema");
    const auto artifact=directory+"/tampered.root";
    save(readback,directory+"/diagnostic.root");
    save(readback,artifact); check(verify(artifact),"root_rebin_recomputation");
    save(future,directory+"/invalid.root"); check(verify(directory+"/invalid.root"),"invalid_slice_artifact_zero_counts");
    throws=false; try { save(readback,s.file); } catch(const std::exception&) { throws=true; }
    check(throws,"existing_input_output_protection");
    {
        TFile corrupt(artifact.c_str(),"UPDATE");
        auto* histogram=dynamic_cast<TH1D*>(corrupt.Get("c0_s2_ch0_24ns"));
        histogram->SetBinContent(1,histogram->GetBinContent(1)+1); histogram->Write("",TObject::kOverwrite);
    }
    throws=false; try { verify(artifact); } catch(const std::exception&) { throws=true; }
    check(throws,"artifact_tampering_detected");
    std::ofstream report(directory+"/self_test.json");
    report << "{\n  \"scope\": \"G001 engineering synthetic only\",\n  \"passed\": true,\n  \"tests\": [";
    for(std::size_t i=0;i<passed.size();++i) report << (i?",":"") << "\n    \"" << passed[i] << "\"";
    report << "\n  ],\n  \"scientific_calibration_complete\": false\n}\n";
    std::cout << "PASS " << passed.size() << " synthetic checks; scientific calibration not claimed\n";
}
}
namespace {
Long64_t integer(const std::string& text) {
    std::size_t end=0; const auto value=std::stoll(text,&end);
    if(end!=text.size()) throw std::runtime_error("invalid integer: "+text);
    return value;
}
}
int main(int argc,char** argv) {
    try {
        using namespace time_offset;
        if(argc==2 && std::string(argv[1])=="--help") {
            std::cout << "TimeOffsetProcessor: read, pair, freeze, independently validate and export\n"
                      << "  --self-test NEW_DIRECTORY\n"
                      << "  --verify-artifacts ROOT_FILE_OR_VALIDATION_DIRECTORY\n"
                      << "  --suggest-windows TRAINING_ROOT NEW_WINDOWS_CSV\n"
                      << "  --preview TRAINING_ROOT WINDOWS_CSV TEMPLATE0 TEMPLATE1 NEW_CSV\n"
                      << "  --combine COMPARISON_MANIFEST NEW_GROUP_DIRECTORY\n"
                      << "  --provenance GROUP_MANIFEST NEW_SOURCES_CSV\n"
                      << "  --summarize GROUP_MANIFEST NEW_REASONS_CSV\n"
                      << "  --mission GROUP_MANIFEST completion.json\n"
                      << "  --freeze --training ROOT --windows CSV --template0 DAT --template1 DAT plus all --scan identity/range options (for planned holdout); --output NEW_FREEZE_DIRECTORY\n"
                      << "  --validate FREEZE_DIRECTORY NEW_VALIDATION_DIRECTORY\n"
                      << "  --scan --input FILE --output NEW_ROOT --ge-run N --csi-run N --group LABEL --slice ID\n"
                      << "    --begin N --end N --core-begin N --core-end N [--chunk 100000] [--max-gap-ns 1000000000] [--slice-entries 0] [--candidate-policy weighted|main]\n"
                      << "Ranges are half-open entries. Read both guards; references lacking 1999 ns guard are excluded.\n"
                      << "Positive --slice-entries uses a fixed grid; each subslice has separate caches and invalidation. Scan alone never calibrates.\n";
            return 0;
        }
        if(argc==3 && std::string(argv[1])=="--self-test") { TimeOffsetProcessor::self_test(argv[2]); Calibration::self_test(std::string(argv[2])+"/calibration"); return 0; }
        if(argc==3 && std::string(argv[1])=="--verify-artifacts") {
            if(fs::is_directory(argv[2])) Calibration::verify(argv[2]); else TimeOffsetProcessor::verify(argv[2]);
            std::cout<<"PASS artifact recomputation\n"; return 0;
        }
        if(argc==7 && std::string(argv[1])=="--preview") { Calibration::preview(argv[2],argv[3],argv[4],argv[5],argv[6]); return 0; }
        if(argc==4 && std::string(argv[1])=="--summarize") { Calibration::summarize(argv[2],argv[3]); return 0; }
        if(argc==4 && std::string(argv[1])=="--provenance") { Calibration::provenance(argv[2],argv[3]); return 0; }
        if(argc==4 && std::string(argv[1])=="--combine") { Calibration::combine(argv[2],argv[3]); return 0; }
        if(argc==4 && std::string(argv[1])=="--mission") { return Calibration::mission(argv[2],argv[3])?0:3; }
        if(argc==4 && std::string(argv[1])=="--suggest-windows") { Calibration::suggest(argv[2],argv[3]); return 0; }
        if(argc==4 && std::string(argv[1])=="--validate") { Calibration::validate(argv[2],argv[3]); return 0; }
        if(argc<2 || (std::string(argv[1])!="--scan" && std::string(argv[1])!="--freeze")) throw std::runtime_error("use --help");
        const bool freeze=std::string(argv[1])=="--freeze";
        std::map<std::string,std::string> args;
        const std::set<std::string> allowed{"--input","--output","--ge-run","--csi-run","--group","--slice","--begin","--end","--core-begin","--core-end","--chunk","--max-gap-ns","--slice-entries","--candidate-policy","--training","--windows","--template0","--template1"};
        for(int i=2;i<argc;i+=2) {
            if(i+1>=argc || !allowed.count(argv[i]) || !args.emplace(argv[i],argv[i+1]).second) throw std::runtime_error("unknown/duplicate/missing option");
        }
        for(const char* key:{"--input","--output","--ge-run","--csi-run","--group","--slice","--begin","--end","--core-begin","--core-end"})
            if(!args.count(key)) throw std::runtime_error(std::string("required ")+key);
        Slice s; s.file=args.at("--input"); s.id=args.at("--slice"); s.group=args.at("--group");
        const auto ge=integer(args.at("--ge-run")), csi=integer(args.at("--csi-run"));
        if(ge<=0 || ge>std::numeric_limits<int>::max() || csi<=0 || csi>std::numeric_limits<int>::max()) throw std::runtime_error("invalid run ID");
        s.ge_run=ge; s.csi_run=csi;
        for(char character:s.group+s.id) if(!(std::isalnum(static_cast<unsigned char>(character)) || character=='-' || character=='_' || character=='.')) throw std::runtime_error("group/slice identifiers must be ASCII alphanumeric punctuation");
        s.begin=integer(args.at("--begin")); s.end=integer(args.at("--end"));
        s.core_begin=integer(args.at("--core-begin")); s.core_end=integer(args.at("--core-end"));
        if(args.count("--chunk")) s.chunk=integer(args.at("--chunk"));
        if(args.count("--max-gap-ns")) s.max_gap_ns=integer(args.at("--max-gap-ns"));
        if(args.count("--slice-entries")) s.subslice_entries=integer(args.at("--slice-entries"));
        if(args.count("--candidate-policy"))s.candidate_policy=args.at("--candidate-policy");
        if(s.candidate_policy!="weighted" && s.candidate_policy!="main")throw std::runtime_error("candidate policy must be selected before training: weighted or main");
        if(fs::exists(args.at("--output")) || fs::is_symlink(args.at("--output"))) throw std::runtime_error("output already exists");
        if(freeze) {
            for(const char* key:{"--training","--windows","--template0","--template1"}) if(!args.count(key)) throw std::runtime_error(std::string("required ")+key);
            Calibration::freeze(args.at("--training"),args.at("--windows"),args.at("--template0"),args.at("--template1"),s,args.at("--output"));
            return 0;
        }
        auto result=TimeOffsetProcessor().read(s);
        TimeOffsetProcessor::save(result,args.at("--output"));
        TimeOffsetProcessor::verify(args.at("--output"));
        std::uint64_t pairs=0; for(const auto& item:result.spectra) pairs+=item.second.pairs;
        std::cout << "valid=" << result.diagnostics.valid << " entries=" << result.diagnostics.entries << " pairs=" << pairs
                  << " references=" << result.diagnostics.core_references << " reason=" << result.diagnostics.reason << "\n";
        return result.diagnostics.valid?0:2;
    } catch(const std::exception& error) { std::cerr << "ERROR: " << error.what() << '\n'; return 1; }
}

namespace time_offset {
namespace {
bool verify_group(const std::string& directory);
std::string verified_group_name(const std::string&,int&);
std::string source_csv(const std::string&);
std::map<std::string,std::string> fields(const std::string& text) {
    std::map<std::string,std::string> out;
    std::istringstream in(text); std::string line;
    while(std::getline(in,line)) {
        const auto split=line.find('=');
        require(split!=std::string::npos && out.emplace(line.substr(0,split),line.substr(split+1)).second,"malformed/duplicate metadata key");
    }
    return out;
}
std::string named(TFile& f,const char* key) {
    auto* value=dynamic_cast<TNamed*>(f.Get(key)); require(value,"missing ROOT metadata: "+std::string(key)); return value->GetTitle();
}
std::string file_text(const std::string& path) {
    std::ifstream in(path); require(in.good(),"cannot read text: "+path);
    std::ostringstream out; out<<in.rdbuf(); return out.str();
}
void write_text(const std::string& path,const std::string& value) {
    new_path(path); std::ofstream out(path); require(out.good(),"cannot create text: "+path);
    out<<value; out.close(); require(out.good(),"text write failed: "+path);
}
std::string json_string(const std::string& value) {
    static const char hex[]="0123456789abcdef";
    std::string encoded="\"";
    for(unsigned char c:value){
        switch(c){
            case '"':encoded+="\\\"";break;
            case '\\':encoded+="\\\\";break;
            case '\b':encoded+="\\b";break;
            case '\f':encoded+="\\f";break;
            case '\n':encoded+="\\n";break;
            case '\r':encoded+="\\r";break;
            case '\t':encoded+="\\t";break;
            default:if(c<32){encoded+="\\u00";encoded+=hex[c>>4];encoded+=hex[c&15];}else encoded+=char(c);
        }
    }
    return encoded+'"';
}
void check_completion_destination(int directory_fd,const std::string& name) {
    struct stat metadata{};
    if(fstatat(directory_fd,name.c_str(),&metadata,AT_SYMLINK_NOFOLLOW)==0) {
        require(S_ISREG(metadata.st_mode) && metadata.st_nlink==1,
                "completion output must be a regular file with exactly one link");
    } else require(errno==ENOENT,"cannot inspect completion output");
}
void atomic_completion(const std::string& path,const std::string& content) {
    const fs::path destination(path);
    const auto parent=destination.parent_path().empty()?fs::path("."):destination.parent_path();
    int directory_fd=open(parent.c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    require(directory_fd>=0,"cannot open completion parent directory");
    int descriptor=-1;FILE* stream=nullptr;std::string temporary;bool temporary_owned=false;
    try {
        const auto name=destination.filename().string();
        check_completion_destination(directory_fd,name);
        for(unsigned attempt=0;attempt<128;++attempt) {
            temporary=".completion.tmp."+std::to_string(getpid())+"."+std::to_string(attempt);
            descriptor=openat(directory_fd,temporary.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
            if(descriptor>=0){temporary_owned=true;break;}
            require(errno==EEXIST,"cannot create exclusive completion temporary file");
            temporary.clear();
        }
        require(descriptor>=0,"no unused completion temporary filename");
        stream=fdopen(descriptor,"w");require(stream!=nullptr,"cannot open completion stream");descriptor=-1;
        require(fwrite(content.data(),1,content.size(),stream)==content.size(),"completion write failed");
        require(fflush(stream)==0,"completion flush failed");
        require(fsync(fileno(stream))==0,"completion fsync failed");
        const int closed=fclose(stream);stream=nullptr;require(closed==0,"completion close failed");
        check_completion_destination(directory_fd,name);
        require(renameat(directory_fd,temporary.c_str(),directory_fd,name.c_str())==0,"completion atomic rename failed");
        temporary.clear();temporary_owned=false;
        const int directory_closed=close(directory_fd);directory_fd=-1;
        require(directory_closed==0,"completion directory close failed");
    } catch(...) {
        if(stream)fclose(stream);
        else if(descriptor>=0)close(descriptor);
        if(temporary_owned)unlinkat(directory_fd,temporary.c_str(),0);
        if(directory_fd>=0)close(directory_fd);
        throw;
    }
}
struct ValidationUse {
    std::string path,hash;
    Long64_t begin=0,end=0;
};
std::vector<ValidationUse> read_validation_uses(const fs::path& path) {
    require(fs::symlink_status(path).type()==fs::file_type::regular && fs::hard_link_count(path)==1,
            "validation ledger must be an ordinary singly-linked file");
    std::ifstream in(path);require(in.good(),"cannot read validation ledger: "+path.string());
    std::vector<ValidationUse> uses;std::string line;unsigned line_number=0;
    while(std::getline(in,line)) {
        ++line_number;
        const auto error="malformed or truncated validation ledger line "+std::to_string(line_number);
        require(!in.eof(),error+" (missing newline)");
        std::istringstream row(line);row>>std::ws;require(row.peek()=='"',error+" (quoted path required)");
        ValidationUse use;
        require(bool(row>>std::quoted(use.path)>>use.begin>>use.end>>use.hash),error);
        row>>std::ws;require(row.eof(),error+" (trailing fields)");
        require(!use.path.empty() && fs::path(use.path).is_absolute() &&
                std::all_of(use.path.begin(),use.path.end(),[](unsigned char c){return c>=32;}),error+" (path)");
        require(use.begin>=0 && use.end>use.begin,error+" (range)");
        require(use.hash.size()==32 && std::all_of(use.hash.begin(),use.hash.end(),[](unsigned char c){return std::isxdigit(c)!=0;}),error+" (digest)");
        uses.push_back(std::move(use));
    }
    require(in.eof() && !in.bad(),"validation ledger read failed");
    return uses;
}
std::string digest(const std::string& path) {
    std::unique_ptr<TMD5> value(TMD5::FileChecksum(path.c_str())); require(bool(value),"cannot checksum: "+path); return value->AsString();
}
Slice slice_from_fields(const std::map<std::string,std::string>& m) {
    Slice s; s.file=m.at("source"); s.id=m.at("slice"); s.group=m.at("group");
    s.ge_run=std::stoi(m.at("ge_run")); s.csi_run=std::stoi(m.at("csi_run"));
    s.begin=std::stoll(m.at("read_begin")); s.end=std::stoll(m.at("read_end"));
    s.core_begin=std::stoll(m.at("core_begin")); s.core_end=std::stoll(m.at("core_end"));
    s.chunk=std::stoll(m.at("chunk")); s.subslice_entries=std::stoll(m.at("subslice_entries")); s.max_gap_ns=std::stoll(m.at("max_gap_ns")); s.synthetic=std::stoi(m.at("synthetic"));
    s.ordered_blocks=m.count("ordered_blocks")?std::stoi(m.at("ordered_blocks")):false;
    if(m.count("statistical_begin_ns")){s.statistical_begin_ns=std::stoll(m.at("statistical_begin_ns"));s.statistical_end_ns=std::stoll(m.at("statistical_end_ns"));}
    if(m.count("candidate_policy"))s.candidate_policy=m.at("candidate_policy");
    return s;
}
std::array<double,1999> statistical_counts(const Spectrum& s) {
    std::array<double,1999> counts{};
    for(const auto& block:s.blocks) for(int i=0;i<1999;++i) counts[i]+=block[i];
    return counts;
}
double projection_variance(const Spectrum& s,const std::array<double,1999>& weights,double& poisson) {
    double sum=0, sum2=0; poisson=0;
    for(const auto& block:s.blocks) {
        double value=0;
        for(int i=0;i<1999;++i) { value+=weights[i]*block[i]; poisson+=weights[i]*weights[i]*block[i]; }
        sum+=value; sum2+=value*value;
    }
    const double empirical=double(StatisticalBlocks)/(StatisticalBlocks-1)*(sum2-sum*sum/StatisticalBlocks);
    return std::max(poisson,std::max(0.,empirical));
}
bool within(double x,double a,double b) { return x>=a && x<=b; }
bool signal_gate(double net,double variance) {
    return std::isfinite(net) && std::isfinite(variance) && variance>0 && net>=100 && net/std::sqrt(variance)>=5;
}
bool center_gate(const Estimate& training,const Estimate& validation,int q) {
    return std::isfinite(training.mu) && std::isfinite(validation.mu) && std::isfinite(training.mu_error) && std::isfinite(validation.mu_error) &&
        std::abs(validation.mu-training.mu)<=std::max(2.*q,3.*std::hypot(training.mu_error,validation.mu_error));
}
void check_window(const PeakWindow& p) {
    require(p.left_low>=-1998 && p.right_high<=1998 && p.left_low<p.left_high && p.left_high<p.low &&
            p.low<p.high && p.high<p.right_low && p.right_low<p.right_high,"invalid/disjoint sideband and peak boundaries");
}
std::map<Address,PeakWindow> parse_windows(const std::string& text) {
    std::istringstream in(text); std::string line;
    require(bool(std::getline(in,line)) && line=="cid,sid,ch,low,high,left_low,left_high,right_low,right_high","bad windows CSV header");
    std::map<Address,PeakWindow> windows;
    while(std::getline(in,line)) {
        if(line.empty()) continue;
        std::replace(line.begin(),line.end(),',',' '); std::istringstream row(line); Address a; PeakWindow p;
        require(bool(row>>a.cid>>a.sid>>a.ch>>p.low>>p.high>>p.left_low>>p.left_high>>p.right_low>>p.right_high),"bad window row");
        std::string rest; require(!(row>>rest),"extra window column");
        check_window(p); require(windows.emplace(a,p).second,"duplicate window address");
    }
    return windows;
}
std::string numbers(const Estimate& e) {
    if(e.reason=="not_estimated")return std::string(21,',');
    std::ostringstream out; out<<std::setprecision(17)<<e.net<<','<<e.background<<','<<e.background_variance<<','<<e.variance<<','<<e.poisson_variance
        <<','<<e.mu<<','<<e.mu_error<<','<<e.snr<<','<<e.background_p<<','<<e.background_chi2<<','<<e.perturbation<<','<<e.block_p<<','<<e.usable_blocks;
    for(int j=0;j<3;++j) out<<','<<e.gates[j]<<','<<e.gate_errors[j]<<','<<e.uncorrected_gates[j];
    return out.str();
}
int unique_rate(const Spectrum* s) { return s && s->rates.size()==1 ? s->rates.begin()->first : 0; }
fs::path validation_ledger(const std::string& directory) {
    fs::path current=fs::absolute(directory).parent_path();
    const auto local=current/"validation_uses.csv";
    while(current!=current.root_path()) {
        if(current.filename()=="time_offset")return current/"validation_uses.csv";
        current=current.parent_path();
    }
    return local; // Isolated synthetic fixtures outside the project keep their own ledger.
}
struct PhysicalPlan {
    bool resolved=false,main_left=true;
    std::string reason="single_or_unresolved";
    int lattice=0,split=0,fit_status=-1,covariance=-1;
    double fit_p=0;
    std::array<double,6> components{}; // amplitude, mu, sigma for the ordered left/right fitted component.
};
PeakWindow component_window(const PeakWindow& whole,const PhysicalPlan& plan,bool left) {
    PeakWindow p=whole;if(left)p.high=plan.split;else p.low=plan.split+plan.lattice;
    check_window(p);return p;
}
PhysicalPlan identify_physical_peaks(const Spectrum& spectrum,const PeakWindow& p,int lattice,int q,const std::string& name,TFile* output) {
    PhysicalPlan plan;plan.lattice=lattice;
    if(!lattice || !q){plan.reason="unknown_or_mixed_sampling_rate";return plan;}
    const auto base=Calibration::estimate(spectrum,p,lattice,q);
    if(!base.passed){plan.reason="overall_"+base.reason;return plan;}
    const auto counts=statistical_counts(spectrum);
    TH1D h((name+"_physical_training_24ns").c_str(),"Training-only physical peak regions;Delta t (ns);Pairs / 24 ns",167,-2004,2004);
    h.SetDirectory(nullptr);
    for(int i=0;i<1999;++i)h.AddBinContent(h.FindBin(-1998+2*i),counts[i]);
    for(int b=1;b<=167;++b)h.SetBinError(b,std::sqrt(std::max(1.,h.GetBinContent(b))));
    int first=0,second=0;
    for(int b=2;b<167;++b)if(within(h.GetBinCenter(b),p.low,p.high) && (!first || h.GetBinContent(b)>h.GetBinContent(first)))first=b;
    for(int b=2;b<167;++b)if(within(h.GetBinCenter(b),p.low,p.high) && std::abs(h.GetBinCenter(b)-h.GetBinCenter(first))>=48 &&
        h.GetBinContent(b)>=h.GetBinContent(b-1) && h.GetBinContent(b)>=h.GetBinContent(b+1) && (!second || h.GetBinContent(b)>h.GetBinContent(second)))second=b;
    if(!first || !second || h.GetBinContent(second)<=0){plan.reason="no_second_training_peak";return plan;}
    if(first>second)std::swap(first,second);
    const double maximum=h.GetMaximum();
    TF1 model((name+"_physical_double").c_str(),"gaus(0)+gaus(3)+[6]",p.low,p.high);
    model.SetParameters(h.GetBinContent(first),h.GetBinCenter(first),48.,h.GetBinContent(second),h.GetBinCenter(second),48.,base.background*24/lattice);
    for(int k=0;k<2;++k){model.SetParLimits(3*k,0,maximum*20);model.SetParLimits(3*k+1,p.low,p.high);model.SetParLimits(3*k+2,4,p.high-p.low);}
    model.SetParLimits(6,0,maximum);
    const TFitResultPtr fit=h.Fit(&model,"QRS0N");plan.fit_status=int(fit);plan.covariance=fit.Get()?fit->CovMatrixStatus():-1;
    plan.fit_p=model.GetNDF()>0?TMath::Prob(model.GetChisquare(),model.GetNDF()):0;
    if(output){output->cd();h.Write();model.Write();if(fit.Get())fit->Write((name+"_physical_fit_result").c_str());}
    bool boundary=false,finite=true;
    for(int i=0;i<model.GetNpar();++i){double low=0,high=0;model.GetParLimits(i,low,high);const auto value=model.GetParameter(i);
        boundary|=high>low && std::min(value-low,high-value)<=1e-5*(high-low);finite&=std::isfinite(value)&&std::isfinite(model.GetParError(i));}
    int lo=model.GetParameter(1)<model.GetParameter(4)?0:3,hi=3-lo;
    for(int i=0;i<3;++i){plan.components[i]=model.GetParameter(lo+i);plan.components[i+3]=model.GetParameter(hi+i);}
    if(plan.fit_status!=0 || plan.covariance!=3 || boundary || !finite || plan.fit_p<.01){plan.reason="double_fit_not_credible";return plan;}
    if(plan.components[4]-plan.components[1]<std::max(48.,2*std::max(plan.components[2],plan.components[5]))){plan.reason="components_not_separated";return plan;}
    plan.split=static_cast<int>(std::floor((plan.components[1]+plan.components[4])/(2*lattice)))*lattice;
    if(plan.split<=p.low || plan.split+lattice>=p.high){plan.reason="split_outside_signal_region";return plan;}
    const auto left=Calibration::estimate(spectrum,component_window(p,plan,true),lattice,q);
    const auto right=Calibration::estimate(spectrum,component_window(p,plan,false),lattice,q);
    if(!left.passed || !right.passed){plan.reason="component_count_quality_failed";return plan;}
    double left_height=0,right_height=0;
    for(int b=1;b<=167;++b)if(within(h.GetBinCenter(b),p.low,p.high)) {
        if(h.GetBinCenter(b)<=plan.split)left_height=std::max(left_height,h.GetBinContent(b));else right_height=std::max(right_height,h.GetBinContent(b));
    }
    if(left_height==right_height){plan.reason="main_peak_height_tie";return plan;}
    plan.main_left=left_height>right_height;plan.resolved=true;plan.reason="double_resolved";
    require(std::abs((left.net*left.mu+right.net*right.mu)/(left.net+right.net)-base.mu)<1e-8,"disjoint count-area weighted centroid mismatch");
    return plan;
}
std::string physical_plan_csv(const std::map<Address,PhysicalPlan>& plans) {
    std::ostringstream out;out<<std::setprecision(17)<<"cid,sid,ch,resolved,reason,lattice,split,main_left,fit_status,covariance,fit_p,amplitude1,mu1,sigma1,amplitude2,mu2,sigma2\n";
    for(const auto& item:plans){const auto& a=item.first;const auto& p=item.second;out<<a.cid<<','<<a.sid<<','<<a.ch<<','<<p.resolved<<','<<p.reason<<','<<p.lattice<<','<<p.split<<','<<p.main_left<<','<<p.fit_status<<','<<p.covariance<<','<<p.fit_p;
        for(double value:p.components)out<<','<<value;
        out<<'\n';}
    return out.str();
}
std::map<Address,PhysicalPlan> parse_physical_plans(const std::string& text) {
    std::istringstream input(text);std::string line;require(bool(std::getline(input,line)) && line=="cid,sid,ch,resolved,reason,lattice,split,main_left,fit_status,covariance,fit_p,amplitude1,mu1,sigma1,amplitude2,mu2,sigma2","physical plan header mismatch");
    std::map<Address,PhysicalPlan> plans;
    while(std::getline(input,line)){
        std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);Address a;PhysicalPlan p;
        require(bool(row>>a.cid>>a.sid>>a.ch>>p.resolved>>p.reason>>p.lattice>>p.split>>p.main_left>>p.fit_status>>p.covariance>>p.fit_p),"malformed physical plan");
        for(double& value:p.components)require(bool(row>>value)&&std::isfinite(value),"nonfinite physical plan parameter");
        row>>std::ws;require(row.eof()&&plans.emplace(a,p).second,"duplicate/trailing physical plan field");
        require(std::isfinite(p.fit_p),"nonfinite physical fit probability");
        if(p.resolved)require(p.reason=="double_resolved"&&p.fit_status==0&&p.covariance==3&&p.fit_p>=.01&&p.lattice>0&&p.split%p.lattice==0&&p.components[0]>0&&p.components[3]>0&&p.components[4]-p.components[1]>=std::max(48.,2*std::max(p.components[2],p.components[5])),"invalid resolved physical peaks");
    }
    return plans;
}
struct Frozen {
    std::string directory, contract, windows_text, hash;
    Slice holdout;
    SliceResult training;
    std::array<CrateTemplate,2> templates;
    std::map<Address,PeakWindow> windows;
    bool candidate_version=false;
    std::string policy="weighted";
    std::map<Address,PhysicalPlan> physical;
};
Frozen load_frozen(const std::string& directory) {
    Frozen f; f.directory=fs::absolute(directory).lexically_normal().string();
    f.hash=digest(f.directory+"/frozen.root");
    require(file_text(f.directory+"/frozen.md5")==f.hash+"\n","frozen parameter digest mismatch");
    TFile root((f.directory+"/frozen.root").c_str(),"READ"); require(!root.IsZombie(),"bad frozen ROOT");
    f.contract=named(root,"contract"); const auto contract=fields(f.contract);
    require(contract.at("training_md5")==digest(f.directory+"/training.root"),"frozen training artifact changed");
    f.training=TimeOffsetProcessor::load(f.directory+"/training.root");
    f.holdout=slice_from_fields(fields(named(root,"holdout")));
    f.windows_text=named(root,"windows"); f.windows=parse_windows(f.windows_text);
    for(int cid=0;cid<2;++cid) {
        f.templates[cid]=Calibration::read_template(contract.at("template"+std::to_string(cid)),cid);
        require(f.templates[cid].text==named(root,("template"+std::to_string(cid)).c_str()),"original template changed since freeze");
    }
    f.candidate_version=contract.at("algorithm")=="count_2ns_candidates_ordered_v2";
    require((f.candidate_version || contract.at("algorithm")=="count_2ns_flat_lattice_blocks_v1") && contract.at("net_min")=="100" && contract.at("snr_min")=="5" &&
            contract.at("background_p_min")=="0.01" && contract.at("block_p_min")=="0.01" && contract.at("perturbation_q")=="1","unknown frozen method/thresholds");
    if(f.candidate_version){
        f.policy=contract.at("candidate_policy");
        require((f.policy=="weighted"||f.policy=="main")&&f.policy==f.training.source.candidate_policy&&f.training.source.ordered_blocks,"candidate policy/order must precede training");
        f.physical=parse_physical_plans(named(root,"physical_plan"));
        require(f.physical.size()==f.windows.size(),"missing physical peak plans");
        for(const auto& item:f.physical)if(item.second.resolved){
            const auto& a=item.first;const auto& plan=item.second;const auto& window=f.windows.at(a);const auto name=a.name();
            auto* model=dynamic_cast<TF1*>(root.Get((name+"_physical_double").c_str()));
            auto* fit=dynamic_cast<TFitResult*>(root.Get((name+"_physical_fit_result").c_str()));
            auto* histogram=dynamic_cast<TH1D*>(root.Get((name+"_physical_training_24ns").c_str()));
            require(model&&fit&&histogram&&fit->Status()==0&&fit->CovMatrixStatus()==3,"missing/invalid frozen physical fit");
            int left=model->GetParameter(1)<model->GetParameter(4)?0:3,right=3-left;
            for(int j=0;j<3;++j)require(model->GetParameter(left+j)==plan.components[j]&&model->GetParameter(right+j)==plan.components[j+3],"physical plan differs from frozen fit parameters");
            require(plan.split==int(std::floor((plan.components[1]+plan.components[4])/(2*plan.lattice)))*plan.lattice,"physical split differs from frozen training means");
            const auto& spectrum=f.training.spectra.at(a);const auto counts=statistical_counts(spectrum);std::array<double,167> coarse{};
            for(int j=0;j<1999;++j)coarse[(j*2-1998+2004)/24]+=counts[j];
            double chi2=0;int fitted_bins=0;double left_height=0,right_height=0;
            for(int b=1;b<=167;++b){
                require(histogram->GetBinContent(b)==coarse[b-1],"physical fit histogram differs from training counts");
                const double x=histogram->GetBinCenter(b),y=coarse[b-1];
                if(within(x,window.low,window.high)){
                    const double residual=y-model->Eval(x);chi2+=residual*residual/std::max(1.,y);++fitted_bins;
                    if(x<=plan.split)left_height=std::max(left_height,y);else right_height=std::max(right_height,y);
                }
            }
            require(fitted_bins-7==model->GetNDF()&&std::abs(chi2-model->GetChisquare())<=1e-7*std::max(1.,chi2),"physical fit residual recomputation mismatch");
            require(TMath::Prob(model->GetChisquare(),model->GetNDF())==plan.fit_p&&plan.main_left==(left_height>right_height)&&left_height!=right_height,"physical fit/main choice mismatch");
            const int q=TimeOffsetProcessor::tick(unique_rate(&spectrum));
            require(Calibration::estimate(spectrum,component_window(window,plan,true),plan.lattice,q).passed&&Calibration::estimate(spectrum,component_window(window,plan,false),plan.lattice,q).passed,"frozen physical count regions fail quality");
        }
    }
    return f;
}
void gates(Estimate& e,const Spectrum& s,const PeakWindow& p,int lattice,int offset) {
    const auto counts=statistical_counts(s);
    for(int j=0;j<3;++j) {
        const int half=100*(j+1);std::array<double,1999> weights{};int n=0,raw_n=0;double signal=0,uncorrected=0;
        for(int i=0;i<1999;++i) {
            const int x=-1998+2*i;if(x%lattice)continue;
            if(std::abs(x-offset)<half){weights[i]=1;++n;signal+=counts[i];}
            if(std::abs(x)<half){++raw_n;uncorrected+=counts[i];}
        }
        for(int i=0;i<1999;++i) {const int x=-1998+2*i;if(x%lattice)continue;
            if(within(x,p.left_low,p.left_high)||within(x,p.right_low,p.right_high))weights[i]-=double(n)/e.side_sites;
        }
        double poisson=0;e.gates[j]=signal-n*e.background;e.gate_errors[j]=std::sqrt(projection_variance(s,weights,poisson));
        e.uncorrected_gates[j]=uncorrected-raw_n*e.background;
    }
}
struct RowResult {
    Address a;
    int old_offset=0, value=0, sr=0, q=0;
    bool observed=false;
    std::vector<int> candidates;
    double low_net200=0,high_net200=0,validation_low_net200=0,validation_high_net200=0;
    std::string status="unknown",reason="not_observed",method="count_2ns";
    Estimate train,validation;
};
std::vector<RowResult> results(const Frozen& frozen,const SliceResult* validation) {
    std::vector<RowResult> rows;
    const auto ref=frozen.training.spectra.find(Reference);
    const int ref_sr=ref==frozen.training.spectra.end()?0:unique_rate(&ref->second);
    const int ref_q=TimeOffsetProcessor::tick(ref_sr);
    for(const auto& crate:frozen.templates) for(const auto& row:crate.rows) {
        RowResult r; r.a=row.address; r.old_offset=row.offset; r.value=row.offset;
        const auto found=frozen.training.spectra.find(r.a);
        const Spectrum* train=found==frozen.training.spectra.end()?nullptr:&found->second;
        r.observed=train && train->observed>0;
        r.sr=unique_rate(train); r.q=TimeOffsetProcessor::tick(r.sr);
        if(r.a==Reference) { r.status="reference"; r.reason="fixed_zero"; rows.push_back(r); continue; }
        if(!r.observed) { rows.push_back(r); continue; }
        if(!r.q || !ref_q) r.reason="unknown_or_mixed_sampling_rate";
        else if(!frozen.windows.count(r.a)) r.reason="no_frozen_peak_window";
        else {
            PeakWindow selected_window=frozen.windows.at(r.a);
            if(frozen.candidate_version){
                const auto& plan=frozen.physical.at(r.a);
                r.method=plan.resolved?"count_2ns_"+frozen.policy:"count_2ns_overall";
                if(frozen.policy=="main"){
                    if(!plan.resolved){r.reason="main_candidate_unresolved";rows.push_back(r);continue;}
                    selected_window=component_window(selected_window,plan,plan.main_left);
                }
            }
            r.train=Calibration::estimate(*train,selected_window,std::gcd(ref_q,r.q),r.q);
            if(r.train.passed) gates(r.train,*train,selected_window,std::gcd(ref_q,r.q),TimeOffsetProcessor::quantize(r.train.mu,r.q));
            r.reason=r.train.reason;
            if(r.train.passed) {
                r.candidates=TimeOffsetProcessor::quantization_candidates(r.train.mu,r.q);
                auto lower=r.train,upper=r.train;
                gates(lower,*train,selected_window,std::gcd(ref_q,r.q),r.candidates.front());
                gates(upper,*train,selected_window,std::gcd(ref_q,r.q),r.candidates.back());
                r.low_net200=lower.gates[1];r.high_net200=upper.gates[1];
                if(r.candidates.size()==2) {
                    r.reason="quantization_tie_unresolved";
                    if(validation) {
                        auto it=validation->spectra.find(r.a);
                        if(it!=validation->spectra.end() && unique_rate(&it->second)==r.sr) {
                            r.validation=Calibration::estimate(it->second,selected_window,std::gcd(ref_q,r.q),r.q);
                            if(r.validation.passed) {
                                auto lo=r.validation,hi=r.validation;
                                gates(lo,it->second,selected_window,std::gcd(ref_q,r.q),r.candidates.front());gates(hi,it->second,selected_window,std::gcd(ref_q,r.q),r.candidates.back());
                                r.validation_low_net200=lo.gates[1];r.validation_high_net200=hi.gates[1];
                            }
                        }
                    }
                    rows.push_back(r);continue;
                }
                r.status="candidate"; r.reason="awaiting_independent_validation";
                if(validation) {
                    const auto vi=validation->spectra.find(r.a), vr=validation->spectra.find(Reference);
                    if(!validation->diagnostics.valid) r.reason="invalid_validation_slice";
                    else if(vi==validation->spectra.end() || vr==validation->spectra.end()) r.reason="missing_validation_channel_or_reference";
                    else if(unique_rate(&vi->second)!=r.sr || unique_rate(&vr->second)!=ref_sr) r.reason="validation_sampling_rate_changed";
                    else {
                        r.validation=Calibration::estimate(vi->second,selected_window,std::gcd(ref_q,r.q),r.q);
                        if(r.validation.side_sites) gates(r.validation,vi->second,selected_window,std::gcd(ref_q,r.q),TimeOffsetProcessor::quantize(r.train.mu,r.q));
                        if(!r.validation.passed) r.reason="validation_"+r.validation.reason;
                        else if(!center_gate(r.train,r.validation,r.q)) r.reason="validation_center_drift";
                        else { r.status="calibrated"; r.reason="independent_validation_passed"; r.value=TimeOffsetProcessor::quantize(r.train.mu,r.q); }
                    }
                    if(r.status!="calibrated") r.status="unknown";
                }
            }
        }
        rows.push_back(r);
    }
    return rows;
}
std::string physical_candidates_csv(const Frozen& frozen,const SliceResult* validation) {
    require(frozen.candidate_version,"physical candidate table needs v2 freeze");
    std::ostringstream out;out<<std::setprecision(17);
    out<<"cid,sid,ch,shape,resolution_reason,candidate,selected,region_source,region_low,region_high,left_net,left_mu,right_net,right_mu,mu_train,error_train,net_train,variance_train,snr_train,background_train,background_variance_train,background_p_train,perturbation_train,block_p_train,offset_ns,effective_ns,residual_train,mu_validation,error_validation,net_validation,variance_validation,snr_validation,background_p_validation,perturbation_validation,block_p_validation,residual_validation,status,reason";
    for(int half:{100,200,300})out<<",train_net_"<<half<<",train_error_"<<half<<",validation_net_"<<half<<",validation_error_"<<half;
    out<<'\n';
    const auto ri=frozen.training.spectra.find(Reference);
    const int ref_sr=ri==frozen.training.spectra.end()?0:unique_rate(&ri->second),ref_q=TimeOffsetProcessor::tick(ref_sr);
    for(const auto& entry:frozen.windows){
        const auto& a=entry.first;const auto& p=entry.second;const auto& plan=frozen.physical.at(a);
        const auto it=frozen.training.spectra.find(a);if(it==frozen.training.spectra.end())continue;
        const int sr=unique_rate(&it->second),q=TimeOffsetProcessor::tick(sr);if(!q || !ref_q)continue;
        const int lattice=std::gcd(q,ref_q);Estimate left,right;
        if(plan.resolved){left=Calibration::estimate(it->second,component_window(p,plan,true),lattice,q);right=Calibration::estimate(it->second,component_window(p,plan,false),lattice,q);}
        const std::vector<std::string> names=plan.resolved?std::vector<std::string>{"main","weighted"}:std::vector<std::string>{"overall"};
        for(const auto& name:names){
            const bool selected=name==frozen.policy || (name=="overall"&&frozen.policy=="weighted");
            const auto region=name=="main"?component_window(p,plan,plan.main_left):p;
            const auto trained=Calibration::estimate(it->second,region,lattice,q);
            const auto offsets=trained.passed?TimeOffsetProcessor::quantization_candidates(trained.mu,q):std::vector<int>{};
            for(std::size_t variant=0;variant<std::max(std::size_t(1),offsets.size());++variant){
                Estimate t=trained,v;const bool have_offset=!offsets.empty();const int offset=have_offset?offsets[variant]:0;
                std::string status="unknown",reason=t.reason;
                if(have_offset){gates(t,it->second,region,lattice,offset);status=offsets.size()==1?"candidate":"unknown";reason=offsets.size()==1?"awaiting_independent_validation":"quantization_tie_unresolved";}
                if(validation && have_offset){
                    const auto vi=validation->spectra.find(a),vr=validation->spectra.find(Reference);
                    if(!validation->diagnostics.valid)reason="invalid_validation_slice";
                    else if(vi==validation->spectra.end()||vr==validation->spectra.end())reason="missing_validation_channel_or_reference";
                    else if(unique_rate(&vi->second)!=sr||unique_rate(&vr->second)!=ref_sr)reason="validation_sampling_rate_changed";
                    else{
                        v=Calibration::estimate(vi->second,region,lattice,q);if(v.side_sites)gates(v,vi->second,region,lattice,offset);
                        if(!v.passed)reason="validation_"+v.reason;
                        else if(!center_gate(t,v,q))reason="validation_center_drift";
                        else if(offsets.size()==1){status="validated";reason="independent_validation_passed";}
                    }
                    if(status!="validated")status="unknown";
                }
                out<<a.cid<<','<<a.sid<<','<<a.ch<<','<<(plan.resolved?"double":"single_or_unresolved")<<','<<plan.reason<<','<<name<<','<<selected
                   <<','<<(plan.resolved?"training_fit24_disjoint_count_regions":"training_whole_count_region")<<','<<region.low<<','<<region.high<<',';
                if(plan.resolved)out<<left.net<<','<<left.mu<<','<<right.net<<','<<right.mu;else out<<",,,";
                out<<','<<t.mu<<','<<t.mu_error<<','<<t.net<<','<<t.variance<<','<<t.snr<<','<<t.background<<','<<t.background_variance<<','<<t.background_p<<','<<t.perturbation<<','<<t.block_p<<',';
                if(have_offset)out<<offset;
                out<<',';if(have_offset)out<<TimeOffsetProcessor::effective(offset,q);
                out<<',';if(have_offset)out<<t.mu-offset;
                out<<','<<v.mu<<','<<v.mu_error<<','<<v.net<<','<<v.variance<<','<<v.snr<<','<<v.background_p<<','<<v.perturbation<<','<<v.block_p<<',';
                if(have_offset&&v.reason!="not_estimated")out<<v.mu-offset;
                out<<','<<status<<','<<reason;
                for(int j=0;j<3;++j)out<<','<<t.gates[j]<<','<<t.gate_errors[j]<<','<<v.gates[j]<<','<<v.gate_errors[j];
                out<<'\n';
            }
        }
    }
    return out.str();
}
std::string row_csv(const std::vector<RowResult>& rows) {
    std::ostringstream out;
    out<<"cid,sid,ch,sr,tick_ns,status,reason,old_offset,crate_value_ns,effective_ns,residual_ns,method,candidate_low_ns,candidate_high_ns,candidate_low_net200,candidate_high_net200,validation_low_net200,validation_high_net200,train_net,train_background,train_background_variance,train_variance,train_poisson_variance,train_mu,train_mu_error,train_snr,train_background_p,train_background_chi2,train_perturbation,train_block_p,train_usable_blocks,train_net_100,train_error_100,train_raw_net_100,train_net_200,train_error_200,train_raw_net_200,train_net_300,train_error_300,train_raw_net_300,validation_net,validation_background,validation_background_variance,validation_variance,validation_poisson_variance,validation_mu,validation_mu_error,validation_snr,validation_background_p,validation_background_chi2,validation_perturbation,validation_block_p,validation_usable_blocks,validation_net_100,validation_error_100,validation_raw_net_100,validation_net_200,validation_error_200,validation_raw_net_200,validation_net_300,validation_error_300,validation_raw_net_300\n";
    for(const auto& r:rows) {
        out<<r.a.cid<<','<<r.a.sid<<','<<r.a.ch<<','<<r.sr<<','<<r.q<<','<<r.status<<','<<r.reason<<','<<r.old_offset<<','<<r.value<<',';
        if(r.q) out<<TimeOffsetProcessor::effective(r.value,r.q);
        out<<',';
        if(r.status=="calibrated") out<<std::setprecision(17)<<r.train.mu-TimeOffsetProcessor::effective(r.value,r.q);
        out<<','<<r.method<<',';
        if(!r.candidates.empty())out<<r.candidates.front();
        out<<',';
        if(!r.candidates.empty())out<<r.candidates.back();
        out<<',';
        if(!r.candidates.empty())out<<std::setprecision(17)<<r.low_net200;
        out<<',';
        if(!r.candidates.empty())out<<std::setprecision(17)<<r.high_net200;
        out<<',';
        if(r.candidates.size()==2 && r.validation.passed)out<<std::setprecision(17)<<r.validation_low_net200;
        out<<',';
        if(r.candidates.size()==2 && r.validation.passed)out<<std::setprecision(17)<<r.validation_high_net200;
        out<<',';
        out<<numbers(r.train)<<','<<numbers(r.validation)<<'\n';
    }
    return out.str();
}
std::string crate_text(const CrateTemplate& original,const std::vector<RowResult>& rows) {
    std::ostringstream out; out<<original.header<<'\n';
    for(const auto& row:original.rows) {
        auto found=std::find_if(rows.begin(),rows.end(),[&](const RowResult& r){return r.a==row.address;});
        require(found!=rows.end(),"template row missing status");
        if(found->status=="calibrated") {
            require(found->value>=-32768 && found->value<=32767 && found->q && found->value%found->q==0,"illegal calibrated offset");
            out<<row.address.sid<<'\t'<<row.address.ch<<'\t'<<found->value<<'\t'<<row.low<<'\t'<<row.high<<'\n';
        } else out<<row.raw<<'\n';
    }
    return out.str();
}
std::string coverage(const Frozen& f,const std::vector<RowResult>& rows,bool validated) {
    int observed=0,calibrated=0,unobserved=0,unknown=0,reference=0,non_template=0;
    for(const auto& r:rows) {
        observed+=r.observed;
        if(r.a==Reference) ++reference;
        else if(r.status=="calibrated") ++calibrated;
        else if(!r.observed) ++unobserved;
        else ++unknown;
    }
    for(const auto& entry:f.training.spectra)
        if(std::none_of(rows.begin(),rows.end(),[&](const RowResult& r){return r.a==entry.first;})) ++non_template;
    std::ostringstream out;
    out<<"{\n  \"group\": \""<<f.training.source.group<<"\",\n  \"template_count\": "<<rows.size()<<",\n  \"observed_template_count\": "<<observed
       <<",\n  \"reference_count\": "<<reference<<",\n  \"calibrated_count\": "<<calibrated<<",\n  \"unobserved_count\": "<<unobserved
       <<",\n  \"unknown_observed_count\": "<<unknown<<",\n  \"non_template_count\": "<<non_template
       <<",\n  \"synthetic\": "<<(f.training.source.synthetic?"true":"false")
       <<",\n  \"status\": \""<<(validated && calibrated>0?"partial_usable":"diagnostic")<<"\",\n  \"scientific_calibration_complete\": "
       <<(validated && calibrated>0 && !f.training.source.synthetic?"true":"false")<<"\n}\n";
    return out.str();
}
void fits(const SliceResult& source,const std::map<Address,PeakWindow>& windows,const std::string& path) {
    new_path(path); TFile file(path.c_str(),"CREATE"); require(!file.IsZombie(),"cannot create fit ROOT");
    TNamed note("fit_contract","Optional diagnostic single/double Gaussian fits; count_2ns selection never requires fit success; double-component areas and means use the same frozen finite peak interval."); note.Write();
    for(const auto& entry:source.spectra) {
        if(entry.first==Reference || !windows.count(entry.first)) continue;
        const auto p=windows.at(entry.first); const auto name=entry.first.name();
        TH1D h((name+"_fit_24ns").c_str(),"Diagnostic 24 ns fit;Delta t (ns);Pairs / 24 ns",167,-2004,2004);
        for(int i=0;i<167;++i) { h.SetBinContent(i+1,entry.second.coarse[i]); h.SetBinError(i+1,std::sqrt(std::max(1.,double(entry.second.coarse[i])))); }
        const double maximum=h.GetMaximum(), midpoint=h.GetBinCenter(h.GetMaximumBin());
        if(maximum<=0 || !within(midpoint,p.low,p.high)) { h.Write(); continue; }
        for(int components:{1,2}) {
            TF1 f((name+(components==1?"_single":"_double")).c_str(),components==1?"gaus(0)+[3]":"gaus(0)+gaus(3)+[6]",p.low,p.high);
            f.SetParameters(maximum,midpoint,48.,maximum/2.,std::min(p.high-24.,midpoint+120.),72.,0.);
            for(int k=0;k<components;++k) { f.SetParLimits(3*k,0.,maximum*20.); f.SetParLimits(3*k+1,p.low,p.high); f.SetParLimits(3*k+2,4.,p.high-p.low); }
            f.SetParLimits(components*3,0.,maximum);
            if(components==1) f.SetParameter(3,0.);
            const TFitResultPtr result=h.Fit(&f,"QRS0N");
            bool bounded=false; double area_sum=0,moment_sum=0;
            std::ostringstream details; details<<std::setprecision(17)<<"source=fit_24ns\nstatus="<<int(result)<<"\ncovariance_status="<<(result.Get()?result->CovMatrixStatus():-1)<<'\n';
            for(int i=0;i<f.GetNpar();++i) { double low=0,high=0; f.GetParLimits(i,low,high); const double value=f.GetParameter(i); if(high>low && std::min(value-low,high-value)<=1e-5*(high-low)) bounded=true; }
            for(int k=0;k<components;++k) {
                const double amplitude=f.GetParameter(k*3),mu=f.GetParameter(k*3+1),sigma=std::abs(f.GetParameter(k*3+2));
                const double u=(p.low-mu)/sigma,v=(p.high-mu)/sigma;
                const double area=amplitude*sigma*std::sqrt(TMath::Pi()/2)*(std::erf(v/std::sqrt(2.))-std::erf(u/std::sqrt(2.)))/24.;
                const double moment=mu*area+amplitude*sigma*sigma*(std::exp(-u*u/2)-std::exp(-v*v/2))/24.;
                details<<"area"<<k<<'='<<area<<"\nfinite_mu"<<k<<'='<<(area>0?moment/area:0)<<'\n'; area_sum+=area; moment_sum+=moment;
            }
            const double pvalue=f.GetNDF()>0?TMath::Prob(f.GetChisquare(),f.GetNDF()):0;
            details<<"at_boundary="<<bounded<<"\nfit_p="<<pvalue<<"\nfinite_area_weighted_mu="<<(area_sum>0?moment_sum/area_sum:0)
                   <<"\nfit_candidate_valid="<<(int(result)==0 && result.Get() && result->CovMatrixStatus()==3 && !bounded && pvalue>=.01 && area_sum>0)<<'\n';
            TNamed record((std::string(f.GetName())+"_parameters").c_str(),details.str().c_str()); record.Write(); f.Write();
            if(result.Get()) result->Write((std::string(f.GetName())+"_result").c_str());
        }
        h.Write();
    }
    file.Close();
}
}

SliceResult TimeOffsetProcessor::load(const std::string& path) {
    verify(path); TFile file(path.c_str(),"READ"); const auto m=fields(named(file,"manifest"));
    SliceResult r; r.source=slice_from_fields(m);r.slice_log=named(file,"slice_log"); auto& d=r.diagnostics;
    d.valid=std::stoi(m.at("valid")); d.reason=m.at("reason"); d.first_ns=std::stoll(m.at("first_ns")); d.last_ns=std::stoll(m.at("last_ns"));
    d.core_first_ns=std::stoll(m.at("core_first_ns")); d.core_last_ns=std::stoll(m.at("core_last_ns"));
    d.tree_entries=std::stoll(m.at("tree_entries")); d.tree_cycle=std::stoi(m.at("tree_cycle"));
    d.entries=std::stoull(m.at("entries")); d.core_references=std::stoull(m.at("core_references"));
    auto* channels=dynamic_cast<TTree*>(file.Get("channels")); Int_t cid=0,sid=0,ch=0,sr=0; ULong64_t observed=0,pairs=0;
    channels->SetBranchAddress("cid",&cid); channels->SetBranchAddress("sid",&sid); channels->SetBranchAddress("ch",&ch);
    channels->SetBranchAddress("sr",&sr); channels->SetBranchAddress("observed",&observed); channels->SetBranchAddress("pairs",&pairs);
    for(Long64_t i=0;i<channels->GetEntries();++i) {
        require(channels->GetEntry(i)>0,"bad channel metadata"); auto& s=r.spectra[{cid,sid,ch}]; s.rates[sr]=observed; s.observed+=observed; s.pairs=pairs;
    }
    for(auto& entry:r.spectra) {
        const auto name=entry.first.name(); auto& s=entry.second;
        auto* fine=dynamic_cast<TH1D*>(file.Get((name+"_2ns").c_str())); auto* coarse=dynamic_cast<TH1D*>(file.Get((name+"_24ns").c_str()));
        auto* blocks=dynamic_cast<TH2D*>(file.Get((name+"_blocks_2ns").c_str()));
        for(int i=0;i<1999;++i) { s.fine[i]=fine->GetBinContent(i+1); for(int k=0;k<StatisticalBlocks;++k) s.blocks[k][i]=blocks->GetBinContent(i+1,k+1); }
        for(int i=0;i<167;++i) s.coarse[i]=coarse->GetBinContent(i+1);
    }
    return r;
}

Estimate Calibration::estimate(const Spectrum& s,const PeakWindow& p,int lattice,int q,bool perturb) {
    check_window(p); require((lattice==2 || lattice==8 || lattice==10) && (q==8 || q==10),"invalid estimation lattice/tick");
    Estimate e; e.reason="insufficient_sideband_statistics";
    const auto counts=statistical_counts(s);
    std::array<double,1999> net_weights{},moment_weights{};
    double signal=0,side=0,moment=0,sum_x=0,left=0,right=0; int nl=0,nr=0;
    for(int i=0;i<1999;++i) {
        const int x=-1998+2*i; if(x%lattice) { if(counts[i]>0) { e.reason="off_lattice_counts"; return e; } continue; }
        if(within(x,p.low,p.high)) { ++e.signal_sites; signal+=counts[i]; moment+=x*counts[i]; sum_x+=x; }
        if(within(x,p.left_low,p.left_high)) { ++nl; left+=counts[i]; }
        if(within(x,p.right_low,p.right_high)) { ++nr; right+=counts[i]; }
    }
    e.side_sites=nl+nr; side=left+right;
    if(!nl || !nr || !e.signal_sites || left<20 || right<20) return e;
    e.background=side/e.side_sites;
    // Four pre-specified sideband cells test both left/right level and within-side slope.
    // Aggregate expected counts >=5 are required for the Pearson chi-square approximation.
    std::array<double,4> cell_counts{},cell_sites{};
    for(int i=0;i<1999;++i) {
        const int x=-1998+2*i;if(x%lattice)continue;int cell=-1;
        if(within(x,p.left_low,p.left_high))cell=x<(p.left_low+p.left_high)/2?0:1;
        if(within(x,p.right_low,p.right_high))cell=x<(p.right_low+p.right_high)/2?2:3;
        if(cell>=0){cell_counts[cell]+=counts[i];++cell_sites[cell];}
    }
    for(int k=0;k<4;++k) {
        const double expected=e.background*cell_sites[k];
        if(expected<5){e.reason="insufficient_sideband_cell_counts";return e;}
        e.background_chi2+=(cell_counts[k]-expected)*(cell_counts[k]-expected)/expected;
    }
    e.background_p=TMath::Prob(e.background_chi2,3);
    e.net=signal-e.signal_sites*e.background;
    if(e.net<=0) { e.reason="nonpositive_net"; return e; }
    e.mu=(moment-sum_x*e.background)/e.net;
    std::array<double,1999> bg_weights{};
    for(int i=0;i<1999;++i) {
        const int x=-1998+2*i; if(x%lattice) continue;
        if(within(x,p.low,p.high)) { net_weights[i]=1; moment_weights[i]=(x-e.mu)/e.net; }
        if(within(x,p.left_low,p.left_high) || within(x,p.right_low,p.right_high)) {
            net_weights[i]=-double(e.signal_sites)/e.side_sites;
            moment_weights[i]=-(sum_x-e.mu*e.signal_sites)/(e.net*e.side_sites);
            bg_weights[i]=1./e.side_sites;
        }
    }
    e.variance=projection_variance(s,net_weights,e.poisson_variance);
    double unused=0; e.background_variance=projection_variance(s,bg_weights,unused);
    e.mu_error=std::sqrt(projection_variance(s,moment_weights,unused));
    e.snr=e.variance>0?e.net/std::sqrt(e.variance):0;
    for(const auto& block:s.blocks) {
        double n=0,mu_linear=0,var=0;
        for(int i=0;i<1999;++i) { n+=net_weights[i]*block[i]; mu_linear+=moment_weights[i]*block[i]*e.net; var+=std::pow(moment_weights[i]*e.net,2)*block[i]; }
        if(n>=5 && var>0) { ++e.usable_blocks; e.block_chi2+=mu_linear*mu_linear/var; }
    }
    e.block_p=e.usable_blocks>1?TMath::Prob(e.block_chi2,e.usable_blocks-1):0;
    if(e.background_p<.01) e.reason="sideband_inconsistent";
    else if(!signal_gate(e.net,e.variance)) e.reason="insufficient_signal";
    else if(e.usable_blocks<8 || e.block_p<.01) e.reason="subcore_instability_or_insufficient_blocks";
    else if(!std::isfinite(e.mu) || !std::isfinite(e.mu_error) || !std::isfinite(e.variance)) e.reason="nonfinite_uncertainty";
    else { e.passed=true; e.reason="passed"; }
    if(perturb && e.passed) {
        // All twelve pre-registered single-boundary +/- one lattice perturbations are mandatory.
        for(int boundary=0;boundary<6;++boundary) for(int sign:{-1,1}) {
            PeakWindow shifted=p;
            double* values[]={&shifted.low,&shifted.high,&shifted.left_low,&shifted.left_high,&shifted.right_low,&shifted.right_high};
            *values[boundary]+=sign*lattice;
            Estimate candidate;
            try { candidate=estimate(s,shifted,lattice,q,false); } catch(const std::exception&) { candidate.passed=false; }
            e.perturbation=std::max(e.perturbation,std::abs(candidate.mu-e.mu));
            if(!candidate.passed || e.perturbation>q) { e.passed=false; e.reason="boundary_perturbation_failed"; }
        }
    }
    return e;
}

CrateTemplate Calibration::read_template(const std::string& path,int cid) {
    CrateTemplate c; c.path=fs::canonical(path).string(); c.text=file_text(path);
    std::istringstream in(c.text); require(bool(std::getline(in,c.header)),"empty template");
    std::istringstream header(c.header); std::string a,b,d,e,f,extra;
    require(bool(header>>a>>b>>d>>e>>f) && !(header>>extra) && a=="sid" && b=="ch" && d=="ts_offset" && e=="ch_low" && f=="ch_high","invalid five-column template header");
    std::set<Address> addresses; std::string line; bool reference=false;
    while(std::getline(in,line)) {
        if(line.empty()) continue;
        TemplateRow r; r.address.cid=cid; r.raw=line; std::istringstream row(line);
        require(bool(row>>r.address.sid>>r.address.ch>>r.offset>>r.low>>r.high) && !(row>>extra),"invalid five-column template row");
        require(r.address.sid>=2 && r.address.ch>=0 && r.address.ch<16 && r.offset>=-32768 && r.offset<=32767 &&
                r.low>=0 && r.high>=r.low && r.high<=65535 && addresses.insert(r.address).second,"invalid/duplicate/range template row");
        if(r.address==Reference) { require(r.offset==0,"nonzero reference template offset"); reference=true; }
        c.rows.push_back(r);
    }
    require(!c.rows.empty() && (cid!=0 || reference),"empty template/missing reference");
    return c;
}
void Calibration::suggest(const std::string& training,const std::string& output) {
    const auto r=TimeOffsetProcessor::load(training);
    std::ostringstream out; out<<"cid,sid,ch,low,high,left_low,left_high,right_low,right_high\n";
    for(const auto& entry:r.spectra) {
        if(entry.first==Reference || entry.second.pairs<100) continue;
        const auto& bins=entry.second.coarse;
        const auto maximum=std::max_element(bins.begin(),bins.end());
        const double mu=-1992+24*std::distance(bins.begin(),maximum);
        const double half=entry.first.cid==0?240:480;
        const double low=std::max(-1100.,mu-half), high=std::min(1100.,mu+half);
        if(low>=high) continue;
        out<<entry.first.cid<<','<<entry.first.sid<<','<<entry.first.ch<<','<<low<<','<<high<<",-1800,-1200,1200,1800\n";
    }
    write_text(output,out.str());
}
void Calibration::freeze(const std::string& training,const std::string& windows,const std::string& template0,const std::string& template1,const Slice& holdout,const std::string& output) {
    require(!fs::exists(output),"freeze output already exists");
    auto source=TimeOffsetProcessor::load(training); require(source.diagnostics.valid,"invalid training slice");
    require(source.source.ordered_blocks && source.source.candidate_policy==holdout.candidate_policy,"v2 requires ordered training and the pre-training candidate policy");
    const auto parsed=parse_windows(file_text(windows));
    const auto t0=read_template(template0,0),t1=read_template(template1,1);
    require(holdout.group==source.source.group && holdout.ge_run>0 && holdout.csi_run>0,"holdout identity/group missing");
    require(holdout.begin>=0 && holdout.end>holdout.begin && holdout.core_begin>=holdout.begin && holdout.core_end<=holdout.end && holdout.core_begin<holdout.core_end,"holdout intervals invalid");
    if(fs::equivalent(holdout.file,source.source.file)) require(holdout.end<=source.source.begin || holdout.begin>=source.source.end,"training/holdout read ranges overlap");
    require(source.source.max_gap_ns==holdout.max_gap_ns,"holdout anomaly rule differs from training");
    fs::create_directory(output);
    fs::copy_file(training,output+"/training.root");
    SliceResult planned; planned.source=holdout;
    std::ostringstream contract;
    contract<<"algorithm=count_2ns_candidates_ordered_v2\ncandidate_policy="<<source.source.candidate_policy<<"\nnet_min=100\nsnr_min=5\nbackground_p_min=0.01\nblock_p_min=0.01\nperturbation_q=1\n"
            <<"training_md5="<<digest(output+"/training.root")<<"\ntemplate0="<<t0.path<<"\ntemplate1="<<t1.path
            <<"\ntraining_source="<<source.source.file<<"\ntraining_slice="<<source.source.id<<"\n";
    {
        TFile file((output+"/frozen.root").c_str(),"CREATE"); require(!file.IsZombie(),"cannot create frozen ROOT");
        TNamed methods("contract",contract.str().c_str()); methods.Write();
        TNamed planned_slice("holdout",manifest(planned).c_str()); planned_slice.Write();
        TNamed w("windows",file_text(windows).c_str()); w.Write();
        TNamed zero("template0",t0.text.c_str()); zero.Write(); TNamed one("template1",t1.text.c_str()); one.Write();
        std::map<Address,PhysicalPlan> physical;
        const auto ref=source.spectra.find(Reference);const int rq=ref==source.spectra.end()?0:TimeOffsetProcessor::tick(unique_rate(&ref->second));
        for(const auto& item:parsed){
            const auto found=source.spectra.find(item.first);const int q=found==source.spectra.end()?0:TimeOffsetProcessor::tick(unique_rate(&found->second));
            if(found!=source.spectra.end()&&q&&rq)physical[item.first]=identify_physical_peaks(found->second,item.second,std::gcd(q,rq),q,item.first.name(),&file);
            else{PhysicalPlan plan;plan.reason="unknown_or_mixed_sampling_rate";physical[item.first]=plan;}
        }
        TNamed physical_record("physical_plan",physical_plan_csv(physical).c_str());physical_record.Write();
    }
    write_text(output+"/frozen.md5",digest(output+"/frozen.root")+"\n");
    auto frozen=load_frozen(output);
    const auto rows=results(frozen,nullptr);
    write_text(output+"/candidates.csv",row_csv(rows));
    write_text(output+"/physical_candidates.csv",physical_candidates_csv(frozen,nullptr));
    {
        TFile root((output+"/frozen.root").c_str(),"UPDATE");
        TNamed candidates("frozen_candidates",row_csv(rows).c_str());candidates.Write();
        TNamed physical("physical_candidates",physical_candidates_csv(frozen,nullptr).c_str());physical.Write();
        TNamed statistics("statistics","v2: common absolute-time chronological 16 buckets across all valid grid slices; slice and bucket gaps >=3998ns prevent target sharing; covariance=sum-block empirical variance with Poisson lower bound; flat reachable lattice background; 4-side-cell Pearson df=3 expected>=5; stationarity assumption tested with block centers; all 12 single-boundary +/-lattice perturbations; strict halfwidth gates 100/200/300 ns");statistics.Write();
    }
    {std::ofstream hash(output+"/frozen.md5");hash<<digest(output+"/frozen.root")<<'\n';}
    fits(source,frozen.windows,output+"/training_fits.root");
    std::cout<<"frozen "<<output<<" candidates="<<std::count_if(rows.begin(),rows.end(),[](const RowResult& r){return r.status=="candidate";})<<"; holdout not opened\n";
}

void Calibration::validate(const std::string& frozen_path,const std::string& output) {
    auto f=load_frozen(frozen_path);
    require(file_text(f.directory+"/candidates.csv")==row_csv(results(f,nullptr)),"frozen candidate values changed");
    require(f.candidate_version,"historical v1 is read-only; new holdout validation requires v2");
    require(file_text(f.directory+"/physical_candidates.csv")==physical_candidates_csv(f,nullptr),"frozen physical candidates changed");
    require(!fs::exists(output),"validation output already exists");
    const auto ledger=validation_ledger(f.directory);
    const auto lock=ledger.string()+".lock";
    require(fs::create_directory(lock),"validation ledger busy; do not bypass lock");
    try {
        if(fs::exists(ledger) || fs::is_symlink(ledger)) {
            for(const auto& use:read_validation_uses(ledger))
                if(fs::equivalent(use.path,f.holdout.file)) require(f.holdout.end<=use.begin || f.holdout.begin>=use.end,"holdout already consumed; use untouched range");
        }
        std::ofstream append(ledger,std::ios::app); require(append.good(),"cannot register validation consumption");
        append<<std::quoted(fs::canonical(f.holdout.file).string())<<' '<<f.holdout.begin<<' '<<f.holdout.end<<' '<<f.hash<<'\n';
        append.close(); require(append.good(),"failed registering validation use");
        fs::remove(lock);
    } catch(...) { fs::remove(lock); throw; }
    fs::create_directory(output);
    // No TFile for the held-out input exists before all frozen-candidate checks and consumption registration.
    const auto validation=TimeOffsetProcessor().read(f.holdout);
    TimeOffsetProcessor::save(validation,output+"/validation.root");
    write_text(output+"/frozen_path.txt",fs::relative(f.directory,fs::absolute(output)).string()+"\n"); write_text(output+"/frozen.md5",f.hash+"\n");
    const auto rows=results(f,&validation);
    write_text(output+"/offsets.csv",row_csv(rows));
    write_text(output+"/physical_candidates.csv",physical_candidates_csv(f,&validation));
    {
        TFile root((output+"/validation.root").c_str(),"UPDATE");
        TNamed evaluation("evaluation",row_csv(rows).c_str());evaluation.Write();
        TNamed physical("physical_candidates",physical_candidates_csv(f,&validation).c_str());physical.Write();
        TNamed frozen_digest("frozen_digest",f.hash.c_str());frozen_digest.Write();
    }
    for(int cid=0;cid<2;++cid) write_text(output+"/crate"+std::to_string(cid)+".dat",crate_text(f.templates[cid],rows));
    write_text(output+"/coverage.json",coverage(f,rows,true));
    fits(validation,f.windows,output+"/validation_fits.root");
    require(verify(output),"validation artifacts inconsistent");
    std::cout<<file_text(output+"/coverage.json");
}
bool Calibration::verify(const std::string& directory) {
    if(fs::exists(directory+"/group_manifest.txt"))return verify_group(directory);
    auto frozen_path=file_text(directory+"/frozen_path.txt"); require(!frozen_path.empty() && frozen_path.back()=='\n',"bad frozen path record"); frozen_path.pop_back();
    if(fs::path(frozen_path).is_relative())frozen_path=(fs::path(directory)/frozen_path).lexically_normal().string();
    const auto f=load_frozen(frozen_path);
    require(file_text(directory+"/frozen.md5")==f.hash+"\n","validation used altered frozen parameters");
    require(file_text(f.directory+"/candidates.csv")==row_csv(results(f,nullptr)),"candidate recomputation disagrees");
    const auto validation=TimeOffsetProcessor::load(directory+"/validation.root");
    require(validation.source.synthetic==f.training.source.synthetic,"training/validation synthetic provenance mismatch");
    if(f.candidate_version)require(validation.source.ordered_blocks && validation.source.candidate_policy==f.policy,"validation block mode or preselected policy changed");
    const auto& a=validation.source; const auto& b=f.holdout;
    require(a.file==fs::absolute(b.file).lexically_normal().string() && a.id==b.id && a.ge_run==b.ge_run && a.csi_run==b.csi_run &&
            a.begin==b.begin && a.end==b.end && a.core_begin==b.core_begin && a.core_end==b.core_end && a.max_gap_ns==b.max_gap_ns && a.subslice_entries==b.subslice_entries,"validation identity differs from pre-registered slice");
    bool registered=false;
    for(const auto& use:read_validation_uses(validation_ledger(f.directory)))
        if(fs::equivalent(use.path,a.file) && use.begin==a.begin && use.end==a.end && use.hash==f.hash)registered=true;
    require(registered,"heldout use is missing from the task-wide consumption ledger");
    const auto rows=results(f,&validation);
    require(file_text(directory+"/offsets.csv")==row_csv(rows),"offset CSV numerical/status recomputation mismatch");
    if(f.candidate_version){
        require(file_text(f.directory+"/physical_candidates.csv")==physical_candidates_csv(f,nullptr),"training physical candidate recomputation mismatch");
        require(file_text(directory+"/physical_candidates.csv")==physical_candidates_csv(f,&validation),"holdout physical candidate recomputation mismatch");
        TFile trained((f.directory+"/frozen.root").c_str(),"READ"),validated((directory+"/validation.root").c_str(),"READ");
        require(named(trained,"physical_candidates")==physical_candidates_csv(f,nullptr)&&named(validated,"physical_candidates")==physical_candidates_csv(f,&validation),"ROOT physical candidate recomputation mismatch");
    }
    {TFile root((directory+"/validation.root").c_str(),"READ");require(named(root,"evaluation")==row_csv(rows) && named(root,"frozen_digest")==f.hash,"ROOT validation evaluation mismatch");}
    {TFile root((f.directory+"/frozen.root").c_str(),"READ");require(named(root,"frozen_candidates")==row_csv(results(f,nullptr)),"ROOT frozen candidates mismatch");}
    for(int cid=0;cid<2;++cid) {
        const auto path=directory+"/crate"+std::to_string(cid)+".dat";
        require(!fs::equivalent(path,f.templates[cid].path),"output aliases input template");
        require(file_text(path)==crate_text(f.templates[cid],rows),"crate template/value preservation mismatch");
        read_template(path,cid);
    }
    require(file_text(directory+"/coverage.json")==coverage(f,rows,true),"coverage recomputation mismatch");
    return true;
}
}

namespace time_offset {
void Calibration::self_test(const std::string& directory) {
    require(!fs::exists(directory),"calibration fixture directory already exists"); fs::create_directory(directory);
    std::vector<std::string> passed;
    auto check=[&](bool value,const std::string& name){require(value,"calibration self-test: "+name);passed.push_back(name);};
    auto rejects=[&](auto operation,const std::string& name){bool failed=false;try {operation();} catch(const std::exception&){failed=true;}check(failed,name);};
    check(signal_gate(100,400) && !signal_gate(99.999,400) && !signal_gate(100,400.001) && !signal_gate(std::numeric_limits<double>::quiet_NaN(),400),"inclusive_net_snr_threshold_and_nan_rejection");
    Estimate baseline,shifted;baseline.mu_error=1;shifted.mu_error=1;shifted.mu=16;
    check(center_gate(baseline,shifted,8),"inclusive_validation_drift_threshold");shifted.mu=16.0001;
    check(!center_gate(baseline,shifted,8),"validation_drift_over_threshold_rejected");
    const auto template0=directory+"/template0.dat",template1=directory+"/template1.dat";
    write_text(template0,"sid ch ts_offset ch_low ch_high\n2 0 16 10 60000\n2 1 -22 12 55000\n2 2 30 13 50000\n2 5 0 0 65535\n");
    write_text(template1,"sid ch ts_offset ch_low ch_high\n2 0 -19 23 45000\n");
    auto make_events=[&](unsigned seed,const std::string& path,bool dual=false) {
        std::mt19937 generator(seed); std::uniform_int_distribution<int> background(-249,249); std::normal_distribution<double> signal(dual?-120.:160.,24.),second_peak(240.,24.);
        std::vector<Hit> hits;
        for(int i=0;i<16000;++i) {
            const Long64_t t=10000+20000LL*i;
            hits.push_back({t/8,0,2,5,250});
            for(int j=0;j<12;++j) {
                const Long64_t delta=j<8?std::llround((dual&&j>=5?second_peak(generator):signal(generator))/8)*8:background(generator)*8;
                hits.push_back({(t-delta)/8,0,2,0,250});
            }
            if(i%20==0) hits.push_back({t/8,0,2,1,Short_t(i%40?125:250)});
        }
        std::stable_sort(hits.begin(),hits.end(),[](const Hit& a,const Hit& b){return a.ts<b.ts;});
        TFile root(path.c_str(),"CREATE"); require(!root.IsZombie(),"cannot create synthetic events");
        TNamed provenance("provenance","synthetic independent engineering fixture; not measured experiment");provenance.Write();
        TTree tree("tree","synthetic calibration events");Hit hit;
        tree.Branch("ts",&hit.ts,"ts/L");tree.Branch("cid",&hit.cid,"cid/S");tree.Branch("sid",&hit.sid,"sid/S");tree.Branch("ch",&hit.ch,"ch/S");tree.Branch("sr",&hit.sr,"sr/S");
        for(const auto& h:hits){hit=h;tree.Fill();}tree.Write();
        return static_cast<Long64_t>(hits.size());
    };
    const auto train_file=directory+"/train_events.root",validation_file=directory+"/validation_events.root";
    const auto train_entries=make_events(431,train_file),validation_entries=make_events(932,validation_file);
    Slice train;train.file=train_file;train.id="synthetic-training";train.group="synthetic";train.ge_run=1;train.csi_run=1;
    train.end=train_entries;train.core_begin=20;train.core_end=train_entries-20;train.synthetic=true;
    auto observed=TimeOffsetProcessor().read(train);TimeOffsetProcessor::save(observed,directory+"/train.root");
    auto grid=train;grid.subslice_entries=50000;grid.chunk=37;
    const auto grid_result=TimeOffsetProcessor().read(grid);
    grid.chunk=100000;const auto grid_again=TimeOffsetProcessor().read(grid);same_spectra(grid_result,grid_again);
    check(grid_result.diagnostics.valid && !grid_result.slice_log.empty(),"fixed_grid_chunk_invariance_and_slice_ledger");
    TimeOffsetProcessor::save(grid_result,directory+"/grid.root");check(TimeOffsetProcessor::verify(directory+"/grid.root"),"grid_contribution_recomputation");
    PeakWindow p;p.low=0;p.high=320;
    const auto e=estimate(observed.spectra.at({0,2,0}),p,8,8);
    Spectrum chronological,folded;chronological.rates[250]=1;chronological.observed=1;
    for(int k=0;k<StatisticalBlocks;++k)for(int i=0;i<1999;++i){
        const int x=-1998+2*i;if(x%8)continue;
        const double mean=80+8*k;
        chronological.blocks[k][i]=16*(4+std::llround(200*std::exp(-.5*std::pow((x-mean)/24.,2))));
        chronological.fine[i]+=chronological.blocks[k][i];
    }
    for(int i=0;i<1999;++i){chronological.coarse[(2*i-1998+2004)/24]+=chronological.fine[i];chronological.pairs+=chronological.fine[i];}
    folded=chronological;for(auto& block:folded.blocks)for(int i=0;i<1999;++i)block[i]=chronological.fine[i]/StatisticalBlocks;
    PeakWindow drift_window;drift_window.low=-80;drift_window.high=400;
    const auto ordered_drift=estimate(chronological,drift_window,8,8),folded_drift=estimate(folded,drift_window,8,8);
    check(folded_drift.passed&&!ordered_drift.passed&&ordered_drift.reason=="subcore_instability_or_insufficient_blocks","slow_drift_folded_buckets_hide_ordered_buckets_detect");
    check(grid_result.source.statistical_begin_ns==grid_again.source.statistical_begin_ns&&grid_result.source.statistical_end_ns==grid_again.source.statistical_end_ns,"grid_shared_absolute_time_axis_is_frozen");
    SliceResult drift_fixture;drift_fixture.source=train;drift_fixture.source.id="synthetic-ordered-drift";drift_fixture.spectra[{0,2,0}]=chronological;
    TimeOffsetProcessor::save(drift_fixture,directory+"/ordered_drift.root");drift_fixture.spectra[{0,2,0}]=folded;drift_fixture.source.id="synthetic-folded-drift";
    TimeOffsetProcessor::save(drift_fixture,directory+"/folded_drift.root");
    check(e.passed && std::abs(e.mu-160)<2 && e.variance>=e.poisson_variance && e.background_variance>0,"lattice_net_centroid_shared_hit_covariance");
    auto sparse=observed.spectra.at({0,2,0});for(auto& block:sparse.blocks)for(auto& n:block)n=0;
    check(!estimate(sparse,p,8,8).passed,"zero_signal_never_calibrated");
    auto off_lattice=observed.spectra.at({0,2,0});++off_lattice.blocks[0][1000];
    check(!estimate(off_lattice,p,8,8).passed,"unreachable_bin_rejected");
    check(e.perturbation<=8 && e.usable_blocks==16,"all_boundary_perturbations_and_subcores");
    check(TimeOffsetProcessor::quantization_candidates(20,8)==std::vector<int>({16,24}) && TimeOffsetProcessor::quantization_candidates(-20,8)==std::vector<int>({-24,-16}),"equidistant_quantization_preserves_both_candidates");
    write_text(directory+"/windows.csv","cid,sid,ch,low,high,left_low,left_high,right_low,right_high\n0,2,0,0,320,-1800,-1200,1200,1800\n0,2,1,0,320,-1800,-1200,1200,1800\n");
    auto holdout=train;holdout.file=validation_file;holdout.id="synthetic-validation";holdout.end=validation_entries;holdout.core_end=validation_entries-20;
    freeze(directory+"/train.root",directory+"/windows.csv",template0,template1,holdout,directory+"/frozen");
    check(!fs::exists(directory+"/validation_uses.csv"),"freeze_precedes_holdout_consumption");
    validate(directory+"/frozen",directory+"/validated");
    check(verify(directory+"/validated"),"scientific_numerical_artifact_recomputation");
    const auto output=read_template(directory+"/validated/crate0.dat",0);
    check(output.rows[0].offset==160 && output.rows[0].low==10 && output.rows[0].high==60000 && output.rows[1].offset==-22 && output.rows[2].offset==30,"complete_template_unknown_mixed_sr_energy_preservation");
    check(file_text(directory+"/validated/coverage.json").find("\"calibrated_count\": 1")!=std::string::npos &&
          file_text(directory+"/validated/coverage.json").find("\"scientific_calibration_complete\": false")!=std::string::npos,"synthetic_not_scientific_completion");
    rejects([&]{validate(directory+"/frozen",directory+"/reused");},"holdout_reuse_rejected");
    fs::create_directories(directory+"/time_offset/other_batch");
    fs::copy(directory+"/frozen",directory+"/time_offset/other_batch/frozen",fs::copy_options::recursive);
    fs::copy_file(directory+"/validation_uses.csv",directory+"/time_offset/validation_uses.csv");
    rejects([&]{validate(directory+"/time_offset/other_batch/frozen",directory+"/time_offset/other_batch/reused");},"cross_batch_holdout_reuse_rejected");
    const auto csv_path=directory+"/validated/offsets.csv";const auto csv=file_text(csv_path);
    {
        auto tampered=csv; const auto pos=tampered.find("unknown");require(pos!=std::string::npos,"missing unknown fixture");tampered.replace(pos,7,"calibrated");
        std::ofstream out(csv_path);out<<tampered;
    }
    rejects([&]{verify(directory+"/validated");},"csv_status_tampering_rejected");
    fs::copy_file(csv_path,directory+"/tampered_offsets.csv");{std::ofstream out(csv_path);out<<csv;}
    const auto md5_path=directory+"/frozen/frozen.md5";const auto original_hash=file_text(md5_path);
    {std::ofstream out(md5_path);out<<"modified\n";}
    rejects([&]{verify(directory+"/validated");},"changed_frozen_parameters_rejected");
    {std::ofstream out(md5_path);out<<original_hash;}
    rejects([&]{freeze(directory+"/train.root",directory+"/windows.csv",template0,template1,train,directory+"/overlap");},"training_validation_read_overlap_rejected");
    write_text(directory+"/duplicate.dat","sid ch ts_offset ch_low ch_high\n2 5 0 0 65535\n2 5 0 0 65535\n");
    rejects([&]{read_template(directory+"/duplicate.dat",0);},"duplicate_template_rejected");
    write_text(directory+"/nonzero_ref.dat","sid ch ts_offset ch_low ch_high\n2 5 8 0 65535\n");
    rejects([&]{read_template(directory+"/nonzero_ref.dat",0);},"nonzero_reference_rejected");
    write_text(directory+"/bad_range.dat","sid ch ts_offset ch_low ch_high\n2 5 0 0 65535\n2 0 32768 0 65535\n");
    rejects([&]{read_template(directory+"/bad_range.dat",0);},"template_signed16_rejected");
    rejects([&]{validate(directory+"/frozen",template0);},"template_output_overwrite_rejected");
    check(verify(directory+"/validated"),"restored_fixture_valid");
    write_text(directory+"/mission_inputs.txt",directory+"/validated\n");
    check(!mission(directory+"/mission_inputs.txt",directory+"/completion.json"),"diagnostic_or_synthetic_cannot_satisfy_mission");
    const auto protected_bytes=file_text(template0);
    const auto completion_path=directory+"/completion.json";
    fs::remove(completion_path);fs::create_symlink(fs::absolute(template0),completion_path);
    rejects([&]{mission(directory+"/mission_inputs.txt",completion_path);},"failed_mission_symlink_output_rejected");
    check(file_text(template0)==protected_bytes && fs::is_symlink(completion_path),"symlink_target_bytes_unchanged");
    fs::remove(completion_path);fs::create_hard_link(template0,completion_path);
    rejects([&]{mission(directory+"/mission_inputs.txt",completion_path);},"failed_mission_hardlink_output_rejected");
    check(file_text(template0)==protected_bytes && fs::hard_link_count(template0)==2,"hardlink_target_bytes_unchanged");
    fs::remove(completion_path);fs::create_directory(completion_path);
    rejects([&]{mission(directory+"/mission_inputs.txt",completion_path);},"nonregular_completion_output_rejected");
    fs::remove(completion_path);
    atomic_completion(completion_path,"first\n");atomic_completion(completion_path,"replacement\n");
    check(file_text(completion_path)=="replacement\n" && fs::hard_link_count(completion_path)==1,"ordinary_completion_atomic_replace");
    check(!mission(directory+"/mission_inputs.txt",completion_path) && file_text(completion_path).find("\"passed\": false")!=std::string::npos,"failed_mission_regular_report_atomic_write");
    const auto json_test=directory+"/json-failure";
    fs::create_directory(json_test);fs::create_directory(json_test+"/group");
    const auto bad_comparison=json_test+"/quote"+char(34)+"backslash"+char(92)+"tab"+char(9)+"return"+char(13);
    fs::create_directory(bad_comparison);
    write_text(bad_comparison+"/frozen_path.txt",std::string("missing")+char(10)+"frozen\n");
    write_text(json_test+"/group/group_manifest.txt",bad_comparison+"\n");
    write_text(json_test+"/mission_inputs.txt",json_test+"/group\n");
    check(!mission(json_test+"/mission_inputs.txt",json_test+"/completion.json"),"special_path_failure_writes_escaped_json");
    const auto escaped_report=file_text(json_test+"/completion.json");
    check(escaped_report.find("\\\"")!=std::string::npos && escaped_report.find("\\\\")!=std::string::npos &&
          escaped_report.find("\\t")!=std::string::npos && escaped_report.find("\\r")!=std::string::npos && escaped_report.find("\\n")!=std::string::npos,
          "json_error_quotes_backslash_and_controls_escaped");
    check(json_string(std::string(1,char(1)))=="\"\\u0001\"" && json_string(std::string(1,char(0)))=="\"\\u0000\"", "json_remaining_control_bytes_escaped");
    const auto ledger_path=validation_ledger(directory+"/frozen");const auto ledger_original=file_text(ledger_path.string());
    std::vector<std::pair<std::string,std::string>> corrupt_ledgers{
        {"bad-before","broken\n"+ledger_original},
        {"bad-after",ledger_original+"broken\n"},
        {"truncated",ledger_original.substr(0,ledger_original.size()-1)},
        {"extra-field",ledger_original.substr(0,ledger_original.size()-1)+" extra\n"},
        {"bad-digest","\"/tmp/source.root\" 0 1 not-md5\n"},
        {"bad-range","\"/tmp/source.root\" 5 5 0123456789abcdef0123456789abcdef\n"},
        {"unquoted-path","/tmp/source.root 0 1 0123456789abcdef0123456789abcdef\n"}
    };
    for(const auto& corruption:corrupt_ledgers) {
        {std::ofstream file(ledger_path);file<<corruption.second;}
        rejects([&]{read_validation_uses(ledger_path);},"strict_ledger_parser_"+corruption.first);
        rejects([&]{validate(directory+"/frozen",directory+"/rejected-"+corruption.first);},"malformed_ledger_before_holdout_"+corruption.first);
        rejects([&]{verify(directory+"/validated");},"verifier_reads_all_ledger_"+corruption.first);
        check(!fs::exists(directory+"/rejected-"+corruption.first) && file_text(ledger_path.string())==corruption.second,"ledger_failure_has_no_consumption_"+corruption.first);
    }
    {std::ofstream file(ledger_path);file<<ledger_original;}
    rejects([&]{read_validation_uses(directory+"/missing-ledger.csv");},"unreadable_missing_ledger_rejected");
    check(read_validation_uses(ledger_path).size()==1 && verify(directory+"/validated"),"valid_ledger_and_artifact_restored");
    const auto dual_train_path=directory+"/dual_train_events.root",dual_validation_path=directory+"/dual_validation_events.root";
    const auto dual_train_entries=make_events(711,dual_train_path,true),dual_validation_entries=make_events(912,dual_validation_path,true);
    auto dual_train=train;dual_train.file=dual_train_path;dual_train.id="synthetic-physical-training";dual_train.end=dual_train_entries;dual_train.core_end=dual_train_entries-20;
    const auto dual_data=TimeOffsetProcessor().read(dual_train);TimeOffsetProcessor::save(dual_data,directory+"/dual_train.root");
    write_text(directory+"/dual_windows.csv","cid,sid,ch,low,high,left_low,left_high,right_low,right_high\n0,2,0,-360,480,-1800,-1200,1200,1800\n");
    auto dual_holdout=dual_train;dual_holdout.file=dual_validation_path;dual_holdout.id="synthetic-physical-validation";dual_holdout.end=dual_validation_entries;dual_holdout.core_end=dual_validation_entries-20;
    freeze(directory+"/dual_train.root",directory+"/dual_windows.csv",template0,template1,dual_holdout,directory+"/dual_frozen");
    const auto dual_frozen=load_frozen(directory+"/dual_frozen");const auto& dual_plan=dual_frozen.physical.at({0,2,0});
    check(dual_plan.resolved&&dual_plan.main_left,"training_double_peak_resolves_disjoint_physical_regions");
    const auto& dual_spectrum=dual_frozen.training.spectra.at({0,2,0});const auto& dual_window=dual_frozen.windows.at({0,2,0});
    auto main_estimate=estimate(dual_spectrum,component_window(dual_window,dual_plan,true),8,8),weighted_estimate=estimate(dual_spectrum,dual_window,8,8);
    gates(main_estimate,dual_spectrum,dual_window,8,TimeOffsetProcessor::quantize(main_estimate.mu,8));
    gates(weighted_estimate,dual_spectrum,dual_window,8,TimeOffsetProcessor::quantize(weighted_estimate.mu,8));
    check(main_estimate.passed&&weighted_estimate.passed&&std::abs(main_estimate.mu-weighted_estimate.mu)>100&&main_estimate.gates[0]>weighted_estimate.gates[0],"main_vs_area_weighted_distinct_centers_same_halfwidth_gates");
    validate(directory+"/dual_frozen",directory+"/dual_validated");
    const auto physical_table=file_text(directory+"/dual_validated/physical_candidates.csv");
    check(physical_table.find(",double,double_resolved,main,0,")!=std::string::npos&&physical_table.find(",double,double_resolved,weighted,1,")!=std::string::npos&&verify(directory+"/dual_validated"),"both_physical_candidates_frozen_and_independently_validated");
    auto main_training=dual_train;main_training.candidate_policy="main";main_training.id="synthetic-main-policy-training";
    TimeOffsetProcessor::save(TimeOffsetProcessor().read(main_training),directory+"/main_policy_train.root");
    auto main_holdout=dual_holdout;main_holdout.candidate_policy="main";
    freeze(directory+"/main_policy_train.root",directory+"/dual_windows.csv",template0,template1,main_holdout,directory+"/main_policy_frozen");
    const auto main_rows=results(load_frozen(directory+"/main_policy_frozen"),nullptr);
    check(std::abs(main_rows.front().train.mu-main_estimate.mu)<1e-9&&main_rows.front().method=="count_2ns_main","main_policy_recorded_before_training_changes_selected_candidate");
    rejects([&]{freeze(directory+"/dual_train.root",directory+"/dual_windows.csv",template0,template1,main_holdout,directory+"/late_policy_change");},"changing_policy_after_training_rejected");
    {std::ofstream altered(directory+"/dual_validated/physical_candidates.csv");altered<<physical_table<<"forged\n";}
    rejects([&]{verify(directory+"/dual_validated");},"physical_candidate_table_tampering_rejected");
    {std::ofstream restored(directory+"/dual_validated/physical_candidates.csv");restored<<physical_table;}
    std::ostringstream json;json<<"{\n  \"scope\": \"synthetic numerical and template tests\",\n  \"passed\": true,\n  \"tests\": [";
    for(std::size_t i=0;i<passed.size();++i)json<<(i?",":"")<<"\n    \""<<passed[i]<<"\"";
    json<<"\n  ],\n  \"scientific_calibration_complete\": false\n}\n";write_text(directory+"/calibration_test.json",json.str());
    std::cout<<"PASS "<<passed.size()<<" numerical/template synthetic checks\n";
}
}

namespace time_offset {
void Calibration::preview(const std::string& training,const std::string& windows,const std::string& template0,const std::string& template1,const std::string& output) {
    Frozen f;f.training=TimeOffsetProcessor::load(training);f.windows=parse_windows(file_text(windows));f.templates[0]=read_template(template0,0);f.templates[1]=read_template(template1,1);
    require(f.training.diagnostics.valid,"invalid training slice");
    const auto rows=results(f,nullptr);write_text(output,row_csv(rows));
    std::cout<<coverage(f,rows,false);
    std::cout<<"training_candidates="<<std::count_if(rows.begin(),rows.end(),[](const RowResult& r){return r.status=="candidate";})<<'\n';
}
bool Calibration::mission(const std::string& manifest_path,const std::string& output) {
    require(fs::path(output).filename()=="completion.json","mission report must be named completion.json");
    require(!fs::exists(output) || !fs::equivalent(output,manifest_path),"completion output aliases mission input");
    std::istringstream manifest(file_text(manifest_path));std::string directory;std::set<std::string> groups;
    int calibrated=0,artifacts=0;bool valid=true;std::string reason;
    try {
        while(std::getline(manifest,directory)) {
            if(directory.empty())continue;
            int count=0;groups.insert(verified_group_name(directory,count));calibrated+=count;++artifacts;
        }
        require(groups.count("A") && groups.count("B") && groups.count("C"),"missing A/B/C group artifacts");
        require(calibrated>0,"all unknown or reference only: diagnostic, not scientific completion");
        require(file_text((fs::path(manifest_path).parent_path()/"sources.csv").string())==source_csv(file_text(manifest_path)),"source CSV disagrees with ROOT and frozen identities");
    } catch(const std::exception& error) {valid=false;reason=error.what();}
    std::ostringstream out;out<<"{\n  \"status\": \""<<(valid?"passed":"failed")<<"\",\n  \"passed\": "<<(valid?"true":"false")
        <<",\n  \"scientific_calibration_complete\": "<<(valid?"true":"false")<<",\n  \"verified_artifact_sets\": "<<artifacts
        <<",\n  \"calibrated_rows_across_artifacts\": "<<calibrated<<",\n  \"reason\": "<<json_string(reason)<<"\n}\n";
    // Verification output is a replaceable machine report, never an input or scientific result table.
    atomic_completion(output,out.str());
    std::cout<<out.str();return valid;
}
}

namespace time_offset {
namespace {
struct GroupResult { Frozen frozen;std::vector<RowResult> rows;std::string inputs; };
GroupResult group_results(const std::string& inputs) {
    GroupResult out;out.inputs=inputs;std::istringstream in(inputs);std::string directory;bool first=true;
    std::set<std::pair<int,int>> identities;
    while(std::getline(in,directory)) {
        if(directory.empty())continue;
        require(!fs::exists(directory+"/group_manifest.txt"),"nested group manifests are not allowed");
        Calibration::verify(directory);
        auto path=file_text(directory+"/frozen_path.txt");path.pop_back();if(fs::path(path).is_relative())path=(fs::path(directory)/path).lexically_normal().string();auto frozen=load_frozen(path);
        auto validation=TimeOffsetProcessor::load(directory+"/validation.root");
        require(identities.insert({validation.source.ge_run,validation.source.csi_run}).second,"group duplicate validation run identity");
        const auto current=results(frozen,&validation);
        if(first){out.frozen=std::move(frozen);out.rows=current;first=false;}
        else {
            require(frozen.contract==out.frozen.contract && frozen.windows_text==out.frozen.windows_text && current.size()==out.rows.size(),"group candidates/training/parameters differ");
            if(frozen.candidate_version)require(physical_plan_csv(frozen.physical)==physical_plan_csv(out.frozen.physical),"group physical peak regions changed across holdouts");
            for(std::size_t i=0;i<current.size();++i) {
                auto& row=out.rows[i];require(row.a==current[i].a,"group template ordering differs");
                if(row.a==Reference)continue;
                if(current[i].status!="calibrated") {
                    row.status="unknown";row.value=row.old_offset;row.reason="comparison_"+std::to_string(validation.source.ge_run)+"_"+current[i].reason;
                } else if(row.status=="calibrated") require(row.value==current[i].value,"group fixed offset changed");
            }
        }
    }
    require(!first && identities.size()>=2,"group requires at least two independent validation runs");
    return out;
}
std::string verified_group_name(const std::string& directory,int& count) {
    require(fs::exists(directory+"/group_manifest.txt"),"mission requires combined cross-run group artifacts");
    verify_group(directory);const auto group=group_results(file_text(directory+"/group_manifest.txt"));
    require(!group.frozen.training.source.synthetic,"synthetic group cannot satisfy mission");
    require(group.frozen.candidate_version,"historical v1 cannot satisfy the physical-candidate mission");
    for(const auto& row:group.rows)count+=row.status=="calibrated";
    return group.frozen.training.source.group;
}
bool verify_group(const std::string& directory) {
    const auto group=group_results(file_text(directory+"/group_manifest.txt"));
    require(file_text(directory+"/offsets.csv")==row_csv(group.rows),"group offset intersection differs");
    for(int cid=0;cid<2;++cid) {
        const auto path=directory+"/crate"+std::to_string(cid)+".dat";
        require(!fs::equivalent(path,group.frozen.templates[cid].path),"group output aliases original template");
        require(file_text(path)==crate_text(group.frozen.templates[cid],group.rows),"group crate differs from verified intersection");
    }
    require(file_text(directory+"/coverage.json")==coverage(group.frozen,group.rows,true),"group coverage differs");
    TFile root((directory+"/group.root").c_str(),"READ");require(!root.IsZombie(),"group ROOT absent");
    require(named(root,"comparison_manifest")==group.inputs && named(root,"group_offsets")==row_csv(group.rows),"group ROOT differs");
    return true;
}
}
void Calibration::combine(const std::string& manifest_path,const std::string& output) {
    const auto group=group_results(file_text(manifest_path));require(!fs::exists(output),"group output already exists");fs::create_directory(output);
    write_text(output+"/group_manifest.txt",group.inputs);write_text(output+"/offsets.csv",row_csv(group.rows));
    for(int cid=0;cid<2;++cid)write_text(output+"/crate"+std::to_string(cid)+".dat",crate_text(group.frozen.templates[cid],group.rows));
    write_text(output+"/coverage.json",coverage(group.frozen,group.rows,true));
    {TFile root((output+"/group.root").c_str(),"CREATE");TNamed inputs("comparison_manifest",group.inputs.c_str());inputs.Write();TNamed offsets("group_offsets",row_csv(group.rows).c_str());offsets.Write();}
    require(verify_group(output),"group verification failed");std::cout<<coverage(group.frozen,group.rows,true);
}
}

namespace time_offset {
namespace {
std::string source_csv(const std::string& group_inputs) {
    std::ostringstream out;
    out<<"group,phase,ge_run,csi_run,source_file,slice,read_begin,read_end,core_begin,core_end,subslice_entries,statistical_begin_ns,statistical_end_ns,ordered_blocks,candidate_policy,entries_checked,tree_entries,tree_cycle,valid_slice_count,invalid_slice_count,guarded_references,pairs,synthetic,artifact\n";
    std::set<std::string> used;
    auto append=[&](const SliceResult& r,const std::string& phase,const std::string& artifact) {
        require(fs::exists(artifact),"source table artifact path missing");
        const auto& s=r.source;const auto& d=r.diagnostics;
        const auto id=s.file+":"+s.id;
        if(!used.insert(id).second)return;
        int valid=d.valid?1:0,invalid=d.valid?0:1;
        if(!r.slice_log.empty()) {
            valid=invalid=0;std::istringstream in(r.slice_log);Long64_t b=0,e=0,error=0;bool ok=false;std::uint64_t pairs=0;std::string reason;
            while(in>>b>>e>>ok>>pairs>>error>>std::quoted(reason)){if(ok)++valid;else ++invalid;}
        }
        std::uint64_t pairs=0;for(const auto& channel:r.spectra)pairs+=channel.second.pairs;
        out<<s.group<<','<<phase<<','<<s.ge_run<<','<<s.csi_run<<','<<s.file<<','<<s.id<<','<<s.begin<<','<<s.end<<','<<s.core_begin<<','<<s.core_end<<','<<s.subslice_entries
           <<','<<s.statistical_begin_ns<<','<<s.statistical_end_ns<<','<<s.ordered_blocks<<','<<s.candidate_policy<<','<<d.entries<<','<<d.tree_entries<<','<<d.tree_cycle<<','<<valid<<','<<invalid<<','<<d.core_references<<','<<pairs<<','<<s.synthetic<<','<<artifact<<'\n';
    };
    std::istringstream groups(group_inputs);std::string group;
    while(std::getline(groups,group)) {
        if(group.empty())continue;
        std::istringstream comparisons(file_text(group+"/group_manifest.txt"));std::string comparison;
        while(std::getline(comparisons,comparison)) {
            if(comparison.empty())continue;
            auto path=file_text(comparison+"/frozen_path.txt");path.pop_back();if(fs::path(path).is_relative())path=(fs::path(comparison)/path).lexically_normal().string();
            const auto f=load_frozen(path);
            append(f.training,"training",(fs::path(comparison)/".."/fs::path(f.directory).filename()/"training.root").lexically_normal().string());
            append(TimeOffsetProcessor::load(comparison+"/validation.root"),"validation",comparison+"/validation.root");
        }
    }
    return out.str();
}
}
void Calibration::provenance(const std::string& manifest,const std::string& output) {write_text(output,source_csv(file_text(manifest)));}
}

namespace time_offset {
void Calibration::summarize(const std::string& manifest,const std::string& output) {
    std::map<std::tuple<std::string,int,std::string,std::string,std::string>,int> counts;
    std::istringstream groups(file_text(manifest));std::string path;
    while(std::getline(groups,path)) {
        if(path.empty())continue;
        verify_group(path);const auto group=group_results(file_text(path+"/group_manifest.txt"));
        for(const auto& row:group.rows) {
            ++counts[{group.frozen.training.source.group,row.a.cid,"final",row.status,row.reason}];
            ++counts[{group.frozen.training.source.group,row.a.cid,"coverage",row.status,"all"}];
        }
        for(const auto& row:results(group.frozen,nullptr))++counts[{group.frozen.training.source.group,row.a.cid,"training",row.status,row.reason}];
        if(group.frozen.candidate_version)for(const auto& item:group.frozen.physical)++counts[{group.frozen.training.source.group,item.first.cid,"physical_shape",item.second.resolved?"double_resolved":"single_or_unresolved",item.second.reason}];
    }
    std::ostringstream out;out<<"group,cid,stage,status,reason,count\n";
    for(const auto& item:counts)out<<std::get<0>(item.first)<<','<<std::get<1>(item.first)<<','<<std::get<2>(item.first)<<','<<std::get<3>(item.first)<<','<<std::get<4>(item.first)<<','<<item.second<<'\n';
    write_text(output,out.str());
}
}
