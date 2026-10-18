#include "time_offset.hh"
#include <TFile.h>
#include <TTree.h>
#include <TLeaf.h>
#include <TF1.h>
#include <TFitResult.h>
#include <TFitResultPtr.h>
#include <TNamed.h>
#include <TParameter.h>
#include <TROOT.h>
#include <TMatrixDSym.h>
#include <algorithm>
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace fs=std::filesystem;
namespace {
using namespace UserDefine;
constexpr double NaN=std::numeric_limits<double>::quiet_NaN();
Address Ref() { return {REF_CID,REF_SID,REF_CH}; }
void Require(bool ok,const std::string &message) { if(!ok) throw std::runtime_error(message); }
bool Cut(int x,int low,int high) { return (low==-1 || x>=low) && (high==-1 || x<=high); }
void CheckCut(int low,int high) {
    Require(low>=-1 && high>=-1 && (low==-1 || high==-1 || low<=high),"Invalid address cut");
}
// 输入地址只检查非负的标量地址；稀疏map不会暗中施加固定数组上限。
bool ValidAddress(Address a) { return a.cid>=0 && a.sid>=0 && a.ch>=0; }
bool Accepted(Address a) {
    return Cut(a.cid,CID_CUT_MIN,CID_CUT_MAX) && Cut(a.sid,SID_CUT_MIN,SID_CUT_MAX) && Cut(a.ch,CH_CUT_MIN,CH_CUT_MAX);
}
int Tick(int sr) {
    for(const auto &p:SR_TICK_NS) if(p.first==sr) { Require(p.second>0,"Invalid timestamp tick"); return p.second; }
    throw std::runtime_error("Unknown sr="+std::to_string(sr));
}
std::string Name(Address a) {
    return "cid"+std::to_string(a.cid)+"_sid"+std::to_string(a.sid)+"_ch"+std::to_string(a.ch);
}
std::string Number(double x) { std::ostringstream s; s<<std::setprecision(12)<<x; return s.str(); }
std::string Width(double low,double high,int bins) { return Number((high-low)/bins)+"ns"; }
void Validate() {
    CheckCut(CID_CUT_MIN,CID_CUT_MAX); CheckCut(SID_CUT_MIN,SID_CUT_MAX); CheckCut(CH_CUT_MIN,CH_CUT_MAX);
    Require(ValidAddress(Ref()) && Accepted(Ref()),"Reference is unconfigured, invalid or excluded by cuts");
    Require(GE_CID>=0 && CSI_CID>=0 && GE_CID!=CSI_CID,"Invalid Ge/CsI crate identities");
    Require(REF_CID==GE_CID || REF_CID==CSI_CID,"Reference crate has no retention rule");
    Require(EVENT_WINDOW_NS>0 && EVENT_WINDOW_NS<std::numeric_limits<Long64_t>::max()/2,"Invalid event window");
    Require(HIST_BIN_NUMBER>0 && HIST_X_MAX>HIST_X_MIN && std::isfinite(HIST_X_MAX-HIST_X_MIN),"Invalid fine histogram");
    Require(FIT_HIST_BIN_NUMBER>0 && FIT_HIST_X_MAX>FIT_HIST_X_MIN && std::isfinite(FIT_HIST_X_MAX-FIT_HIST_X_MIN),"Invalid fit histogram");
    Require(SMOOTH_NS>0 && MIN_SIGMA_NS>0 && SIDEBAND_BLOCK_NS>0 && MIN_PAIRS>0,"Invalid peak parameters");
    Require(Width(HIST_X_MIN,HIST_X_MAX,HIST_BIN_NUMBER)!=Width(FIT_HIST_X_MIN,FIT_HIST_X_MAX,FIT_HIST_BIN_NUMBER),"Histogram names require different bin widths");
}
struct Shape {
    bool signal=false,two=false;
    double peak=0,second=0,left=0,right=0,background=0;
    std::vector<double> smooth;
};
// 平滑临时计数密度；原始两谱不修改，不把8/10ns格点误认为多峰。
Shape FindShape(const TH1D &h) {
    Shape s;
    int n=h.GetNbinsX();
    double bin=h.GetBinWidth(1), sigma=SMOOTH_NS/2.354820045;
    int radius=std::max(1,int(std::ceil(3*sigma/bin)));
    s.smooth.resize(n+1);
    for(int i=1;i<=n;++i) {
        double sum=0,norm=0;
        for(int j=std::max(1,i-radius);j<=std::min(n,i+radius);++j) {
            double weight=std::exp(-0.5*std::pow((j-i)*bin/sigma,2));
            sum+=weight*h.GetBinContent(j); norm+=weight;
        }
        s.smooth[i]=sum/norm/bin;
    }
    std::vector<double> sorted(s.smooth.begin()+1,s.smooth.end());
    std::sort(sorted.begin(),sorted.end());
    s.background=sorted[sorted.size()/3];
    int p=std::max_element(s.smooth.begin()+1,s.smooth.end())-s.smooth.begin();
    // 主峰附近的对称外围样本中位数，避免远处本底台阶支配局部峰尾。
    std::vector<double> local;
    for(int i=1;i<=n;++i) {
        double distance=std::abs(h.GetBinCenter(i)-h.GetBinCenter(p));
        if(distance>=LOCAL_BACKGROUND_INNER_NS && distance<=LOCAL_BACKGROUND_OUTER_NS) local.push_back(s.smooth[i]);
    }
    if(!local.empty()) { std::sort(local.begin(),local.end()); s.background=local[local.size()/2]; }
    double height=s.smooth[p]-s.background;
    double noise=std::sqrt((s.background+1/SMOOTH_NS)/SMOOTH_NS);
    if(h.Integral()<MIN_PAIRS || height<PEAK_SIGNIFICANCE*noise) return s;
    s.signal=true; s.peak=h.GetBinCenter(p);
    int q=p;
    for(int i=2;i<n;++i) {
        if(std::abs(h.GetBinCenter(i)-s.peak)<SECOND_SEPARATION_NS ||
           s.smooth[i]<s.smooth[i-1] || s.smooth[i]<=s.smooth[i+1]) continue;
        double valley=*std::min_element(s.smooth.begin()+std::min(i,p),s.smooth.begin()+std::max(i,p)+1);
        if(s.smooth[i]-s.background>std::max(SECOND_HEIGHT_FRACTION*height,PEAK_SIGNIFICANCE*noise) &&
           valley-s.background<VALLEY_FRACTION*(std::min(s.smooth[i],s.smooth[p])-s.background) &&
           (q==p || s.smooth[i]>s.smooth[q])) q=i;
    }
    s.two=q!=p; s.second=h.GetBinCenter(q);
    int l=std::min(p,q),r=std::max(p,q);
    double tail=s.background+std::max(TAIL_FRACTION*height,2*noise);
    while(l>1 && s.smooth[l]>tail) --l;
    while(r<n && s.smooth[r]>tail) ++r;
    s.left=h.GetBinCenter(l); s.right=h.GetBinCenter(r);
    return s;
}
struct Range { double low,high; };
// 用连续侧带块的二阶差分限制扩展，单个bin不决定边界。
double SideLimit(const TH1D &h,double tail,int direction) {
    double edge=tail;
    std::vector<double> means,variances;
    for(int block=0;block<SIDEBAND_BLOCKS.back();++block) {
        double next=tail+direction*(block+1)*SIDEBAND_BLOCK_NS;
        double low=std::min(edge,next),high=std::max(edge,next);
        if(low<h.GetXaxis()->GetXmin() || high>h.GetXaxis()->GetXmax() ||
           low< -double(EVENT_WINDOW_NS) || high>double(EVENT_WINDOW_NS)) break;
        int first=h.FindFixBin(low+1e-6),last=h.FindFixBin(high-1e-6);
        double count=h.Integral(first,last),width=(last-first+1)*h.GetBinWidth(1);
        means.push_back(count/width); variances.push_back(std::max(1.0,count)/(width*width));
        auto n=means.size();
        if(n>=3 && std::abs(means[n-1]-2*means[n-2]+means[n-3])>
           SIDEBAND_CURVATURE_Z*std::sqrt(variances[n-1]+4*variances[n-2]+variances[n-3])) break;
        edge=next;
    }
    return edge;
}
std::vector<Range> Ranges(const TH1D &h,const Shape &s) {
    std::vector<Range> ranges;
    double limitL=SideLimit(h,s.left,-1),limitR=SideLimit(h,s.right,1),bin=h.GetBinWidth(1);
    for(int blocks:SIDEBAND_BLOCKS) {
        double l=std::max(limitL,s.left-blocks*SIDEBAND_BLOCK_NS);
        double r=std::min(limitR,s.right+blocks*SIDEBAND_BLOCK_NS);
        // 只取完整原始bin，并排除固定事件窗不可能到达的padding。
        l=std::max({l,h.GetXaxis()->GetXmin(),-double(EVENT_WINDOW_NS)});
        r=std::min({r,h.GetXaxis()->GetXmax(),double(EVENT_WINDOW_NS)});
        int first=h.FindFixBin(l+1e-6),last=h.FindFixBin(r-1e-6);
        if(h.GetBinLowEdge(first)<l-1e-6) ++first;
        if(h.GetBinLowEdge(last+1)>r+1e-6) --last;
        Range range{h.GetBinLowEdge(first),h.GetBinLowEdge(last+1)};
        if(range.low>=s.left || range.high<=s.right || (range.high-range.low)/bin<=9) continue;
        if(ranges.empty() || range.low!=ranges.back().low || range.high!=ranges.back().high) ranges.push_back(range);
    }
    return ranges;
}
struct Fit {
    std::unique_ptr<TF1> function;
    int status=-1,covariance=0,ndf=0,components=0;
    bool numeric=false,boundary=false,identifiable=true,tails=false;
    double mean=NaN,error=NaN,deviance=NaN,peak_deviance=NaN,side_deviance=NaN,bic=NaN;
    double single_bic=NaN,double_bic=NaN;
    Range range{0,0};
    std::array<double,2> areas{{NaN,NaN}};
    std::vector<double> covariance_values;
};
// 面积权重及联合协方差传播；本底参数对加权中心的显式导数为零。
std::pair<double,double> Center(const std::vector<double> &p,const std::vector<double> &cov,int components) {
    if(components==1) return {p[1],cov[1*p.size()+1]>=0?std::sqrt(cov[1*p.size()+1]):NaN};
    double w1=p[0]*p[2],w2=p[3]*p[5],sum=w1+w2;
    Require(sum>0,"Nonpositive Gaussian area");
    double mean=(p[1]*w1+p[4]*w2)/sum;
    std::vector<double> j(p.size(),0);
    for(int k:{0,3}) {
        j[k]=p[k+2]*(p[k+1]-mean)/sum;
        j[k+1]=p[k]*p[k+2]/sum;
        j[k+2]=p[k]*(p[k+1]-mean)/sum;
    }
    double variance=0;
    for(size_t a=0;a<j.size();++a) for(size_t b=0;b<j.size();++b) variance+=j[a]*cov[a*j.size()+b]*j[b];
    return {mean,variance>=0?std::sqrt(variance):NaN};
}
// 端点非负的直线与pol1同一模型族，保证区间内Poisson期望有效。
Fit FitModel(TH1D &h,const Shape &s,Range range,int components) {
    Fit out; out.components=components; out.range=range;
    int bg=3*components;
    std::string formula=components==2?"gaus(0)+gaus(3)":"gaus(0)";
    formula+="+["+std::to_string(bg)+"]*("+Number(range.high)+"-x)/"+Number(range.high-range.low)+
             "+["+std::to_string(bg+1)+"]*(x-("+Number(range.low)+"))/"+Number(range.high-range.low);
    out.function.reset(new TF1("trial",formula.c_str(),range.low,range.high));
    TF1 &f=*out.function;
    double maximum=h.GetMaximum(),bin=h.GetBinWidth(1),background=s.background*bin;
    for(int k=0;k<bg;k+=3) {
        f.SetParameter(k,std::max(1.0,maximum-background)*(k?0.6:1));
        f.SetParLimits(k,1e-8,10*maximum+10);
        f.SetParameter(k+1,k?s.second:s.peak);
        f.SetParLimits(k+1,range.low+bin/2,range.high-bin/2);
        f.SetParameter(k+2,INITIAL_SIGMA_NS);
        f.SetParLimits(k+2,MIN_SIGMA_NS,(range.high-range.low)/2);
    }
    for(int k=bg;k<bg+2;++k) { f.SetParameter(k,std::max(0.1,background)); f.SetParLimits(k,0,10*maximum+10); }
    // L:Poisson; I:bin积分平均; S:协方差; N:不附加被淘汰的候选。
    TFitResultPtr result=h.Fit(&f,"SQLIRN");
    out.status=int(result);
    if(!result.Get()) return out;
    out.covariance=result->CovMatrixStatus();
    out.numeric=out.status==0 && out.covariance>=2;
    std::vector<double> p(f.GetNpar()),cov(p.size()*p.size());
    for(size_t a=0;a<p.size();++a) {
        p[a]=f.GetParameter(a);
        for(size_t b=0;b<p.size();++b) cov[a*p.size()+b]=result->CovMatrix(a,b);
    }
    out.covariance_values=cov;
    auto center=Center(p,cov,components); out.mean=center.first;
    if(out.covariance>=2) out.error=center.second;
    out.numeric=out.numeric && std::isfinite(out.mean) && std::isfinite(out.error);
    for(int k=0;k<bg;k+=3) {
        double lower,upper;
        for(int a=k;a<k+3;++a) {
            f.GetParLimits(a,lower,upper);
            if(p[a]<=lower+0.001*(upper-lower) || p[a]>=upper-0.001*(upper-lower)) out.boundary=true;
        }
        if(p[k]<COMPONENT_SIGNIFICANCE*f.GetParError(k)) out.identifiable=false;
        if(p[k+1]-3*p[k+2]<range.low || p[k+1]+3*p[k+2]>range.high) out.tails=true;
        out.areas[k/3]=p[k]*p[k+2]*std::sqrt(2*std::acos(-1.0))/bin;
    }
    if(components==2 && std::abs(p[1]-p[4])<bin) out.identifiable=false;
    if(components==2 && std::abs(p[1]-p[4])<2*std::sqrt(std::max(0.0,cov[1*p.size()+1]+cov[4*p.size()+4]-2*cov[1*p.size()+4]))) out.identifiable=false;
    int first=h.FindFixBin(range.low+1e-6),last=h.FindFixBin(range.high-1e-6),np=0,ns=0;
    out.deviance=0; out.peak_deviance=0; out.side_deviance=0;
    for(int i=first;i<=last;++i) {
        double expected=f.Integral(h.GetBinLowEdge(i),h.GetBinLowEdge(i+1))/bin,y=h.GetBinContent(i);
        if(!(expected>0) || !std::isfinite(expected)) { out.numeric=false; return out; }
        double d=2*(expected-y+(y>0?y*std::log(y/expected):0));
        out.deviance+=d;
        double x=h.GetBinCenter(i);
        if(x>=s.left && x<=s.right) { out.peak_deviance+=d; ++np; }
        else { out.side_deviance+=d; ++ns; }
    }
    out.ndf=last-first+1-f.GetNpar();
    out.peak_deviance/=std::max(1,np-3*components);
    out.side_deviance/=std::max(1,ns-2);
    out.bic=out.deviance+f.GetNpar()*std::log(double(last-first+1));
    out.numeric=out.numeric && out.ndf>0 && std::isfinite(out.deviance);
    return out;
}
struct Result {
    Fit fit;
    std::string status="no_peak",reason;
    double sensitivity=NaN;
    std::vector<Fit> trials;
};
// 同区间以BIC比较模型；选择可描述侧带的最宽候选，保留全部范围诊断。
Result Analyze(Spectrum &s,bool enabled) {
    Result out;
    if(!enabled) { out.status="not_fitted"; out.reason="fit_disabled"; return out; }
    if(s.coarse->Integral()==0) { out.reason="flow_only"; return out; }
    Shape shape=FindShape(*s.fine);
    if(!shape.signal) { out.reason="insufficient_peak"; return out; }
    auto ranges=Ranges(*s.coarse,shape);
    int selected=-1;
    for(auto range:ranges) {
        Fit fit=FitModel(*s.coarse,shape,range,1);
        double single_bic=fit.bic,double_bic=NaN;
        Shape candidate_shape=shape;
        // 未形成独立局部极大值的肩峰，由单峰后连续平滑残差提出候选。
        if(!candidate_shape.two && fit.numeric && fit.peak_deviance>DEVIANCE_REVIEW) {
            double best=0;
            for(int i=1;i<=s.fine->GetNbinsX();++i) {
                double x=s.fine->GetBinCenter(i);
                if(x<shape.left || x>shape.right || std::abs(x-shape.peak)<SECOND_SEPARATION_NS) continue;
                double expected=fit.function->Eval(x)/s.coarse->GetBinWidth(1);
                double residual=shape.smooth[i]-expected;
                double threshold=std::max(SHOULDER_RESIDUAL_FRACTION*(shape.smooth[s.fine->FindFixBin(shape.peak)]-shape.background),
                    PEAK_SIGNIFICANCE*std::sqrt(std::max(expected,1/SMOOTH_NS)/SMOOTH_NS));
                if(residual>threshold && residual>best) { best=residual; candidate_shape.second=x; candidate_shape.two=true; }
            }
        }
        if(candidate_shape.two) {
            Fit two=FitModel(*s.coarse,candidate_shape,range,2);
            double_bic=two.bic;
            if(two.numeric && two.identifiable && (!fit.numeric || two.bic+BIC_IMPROVEMENT<fit.bic)) fit=std::move(two);
        }
        fit.single_bic=single_bic; fit.double_bic=double_bic;
        out.trials.push_back(std::move(fit));
        auto &candidate=out.trials.back();
        if(!candidate.numeric) continue;
        if(selected<0 || (candidate.identifiable && !candidate.boundary && !candidate.tails && candidate.side_deviance<=DEVIANCE_REVIEW))
            selected=int(out.trials.size())-1;
    }
    if(selected<0) { out.status="fit_failed"; out.reason=ranges.empty()?"no_complete_sidebands":"no_valid_covariance_or_fit"; return out; }
    auto &chosen=out.trials[selected];
    double low=chosen.mean,high=chosen.mean;
    for(const auto &f:out.trials) if(f.numeric) { low=std::min(low,f.mean); high=std::max(high,f.mean); }
    out.sensitivity=high-low;
    if((shape.two || std::isfinite(chosen.double_bic)) && chosen.components==1) out.reason+="second_peak_seed_unresolved;";
    if(chosen.boundary) out.reason+="parameter_boundary;";
    if(!chosen.identifiable) out.reason+="unresolved_component;";
    if(chosen.tails) out.reason+="tail_extrapolation;";
    if(chosen.covariance<3) out.reason+="approximate_covariance;";
    if(chosen.deviance/chosen.ndf>DEVIANCE_REVIEW) out.reason+="deviance_ndf_gt_3;";
    if(chosen.side_deviance>DEVIANCE_REVIEW) out.reason+="sideband_model_mismatch;";
    if(chosen.peak_deviance>DEVIANCE_REVIEW) out.reason+="peak_residual_structure;";
    out.status=out.reason.empty()?"ok":"review";
    // Clone leaves trials intact for range diagnostics and gives ROOT an independent function.
    out.fit.components=chosen.components; out.fit.range=chosen.range; out.fit.status=chosen.status;
    out.fit.covariance=chosen.covariance; out.fit.ndf=chosen.ndf; out.fit.mean=chosen.mean;
    out.fit.error=chosen.error; out.fit.deviance=chosen.deviance; out.fit.bic=chosen.bic;
    out.fit.peak_deviance=chosen.peak_deviance; out.fit.side_deviance=chosen.side_deviance;
    out.fit.covariance_values=chosen.covariance_values;
    out.fit.areas=chosen.areas; out.fit.numeric=chosen.numeric;
    out.fit.function.reset(static_cast<TF1*>(chosen.function->Clone("time_fit")));
    return out;
}
void Cell(std::ostream &out,double x) { if(std::isfinite(x)) out<<x; }
// decoder的整型ns偏移先除目标tick，正负均向零截断。
double Offset(double mean,int tick) { return tick*std::trunc(mean/tick); }
}

// 地址首次出现时建谱；参考单独记末次时间，不要求参考一定属于Ge。
void TimeOffset::ProcessEntry(Address a,Long64_t ns,int tick) {
    if(active && std::llabs(ns-start)>UserDefine::EVENT_WINDOW_NS) EndEvent();
    if(!active) { active=true; start=ns; }
    auto &s=spectra[a];
    if(!s.fine) {
        using namespace UserDefine;
        std::string name=Name(a),title=name+";t_{ref}-t_{channel} [ns];Pairs / ";
        s.fine.reset(new TH1D((name+"_"+Width(HIST_X_MIN,HIST_X_MAX,HIST_BIN_NUMBER)).c_str(),
          (title+Width(HIST_X_MIN,HIST_X_MAX,HIST_BIN_NUMBER)).c_str(),HIST_BIN_NUMBER,HIST_X_MIN,HIST_X_MAX));
        s.coarse.reset(new TH1D((name+"_"+Width(FIT_HIST_X_MIN,FIT_HIST_X_MAX,FIT_HIST_BIN_NUMBER)).c_str(),
          (title+Width(FIT_HIST_X_MIN,FIT_HIST_X_MAX,FIT_HIST_BIN_NUMBER)).c_str(),FIT_HIST_BIN_NUMBER,FIT_HIST_X_MIN,FIT_HIST_X_MAX));
        s.fine->SetDirectory(nullptr); s.coarse->SetDirectory(nullptr);
    }
    ++s.hits; s.ticks.insert(tick);
    if(a==Ref()) { have_reference=true; reference_time=ns; ++reference_hits; }
    if(a.cid==UserDefine::GE_CID) ge[a]=ns;
    else if(a.cid==UserDefine::CSI_CID) csi.emplace_back(a,ns);
    else throw std::runtime_error("Accepted crate has no Ge/CsI retention rule: "+Name(a));
}
// 同一候选对直接填两谱，不额外施加Delta-t cut，保留flow计数。
void TimeOffset::Fill(Address a,Long64_t dt) {
    if(a==Ref()) return;
    spectra.at(a).fine->Fill(double(dt)); spectra.at(a).coarse->Fill(double(dt));
}
// 末包同样调用；不含参考的包不填谱。
void TimeOffset::EndEvent() {
    if(!active) return;
    ++events;
    if(have_reference) {
        ++reference_events;
        for(const auto &hit:ge) Fill(hit.first,reference_time-hit.second);
        for(const auto &hit:csi) Fill(hit.first,reference_time-hit.second);
    }
    ge.clear(); csi.clear(); active=false; have_reference=false;
}
// 正式入口只替换run占位符，所有实验参数来自UserDefine。
void TimeOffset::Process(int run) {
    std::string filename=UserDefine::INPUT_PATTERN;
    size_t pos=0;
    while((pos=filename.find("{run}",pos))!=std::string::npos) {
        std::string value=std::to_string(run); filename.replace(pos,5,value); pos+=value.size();
    }
    Process(run,(fs::path(UserDefine::INPUT_DIRECTORY)/filename).string(),UserDefine::OUTPUT_DIRECTORY);
}
// 只流式启用五个标量分支；limit只供保存的验证程序使用，不更改输入文件。
void TimeOffset::Process(int run,const std::string &input,const std::string &output,Long64_t limit,bool fit) {
    Validate(); Require(run>0 && limit>=0,"Invalid run or entry limit");
    Require(processed==0 && spectra.empty(),"Use a new TimeOffset instance per input");
    fs::create_directories(output);
    for(const char *ext:{".root",".csv",".md"})
        Require(!fs::exists(fs::path(output)/("time_offset_"+std::to_string(run)+ext)),"Output already exists; choose a new output directory");
    TFile source(input.c_str(),"READ"); Require(!source.IsZombie(),"Cannot read input: "+input);
    auto *tree=dynamic_cast<TTree*>(source.Get(UserDefine::TREE_NAME)); Require(tree,"Missing input tree");
    tree->SetBranchStatus("*",0);
    Hit hit;
    std::array<std::pair<const char*,void*>,5> fields{{{UserDefine::TS_FIELD,&hit.ts},{UserDefine::CID_FIELD,&hit.cid},
        {UserDefine::SID_FIELD,&hit.sid},{UserDefine::CH_FIELD,&hit.ch},{UserDefine::SR_FIELD,&hit.sr}}};
    for(size_t i=0;i<fields.size();++i) {
        auto *leaf=tree->GetLeaf(fields[i].first);
        Require(leaf && leaf->GetLenStatic()==1 && !leaf->GetLeafCount() &&
          std::string(leaf->GetTypeName())==(i==0?"Long64_t":"Short_t"),"Missing or invalid scalar branch: "+std::string(fields[i].first));
        tree->SetBranchStatus(fields[i].first,1);
        Require(tree->SetBranchAddress(fields[i].first,fields[i].second)>=0,"Cannot bind input branch");
    }
    input_entries=tree->GetEntries(); Long64_t count=limit?std::min(limit,input_entries):input_entries;
    tree->SetCacheSize(32*1024*1024);
    for(const auto &f:fields) tree->AddBranchToCache(f.first,true);
    std::cout<<"input="<<input<<" entries="<<input_entries<<" process="<<count<<" fit="<<fit<<'\n'
      <<"fine: "<<UserDefine::HIST_X_MIN<<" .. "<<UserDefine::HIST_X_MAX<<" ns, "<<UserDefine::HIST_BIN_NUMBER
      <<" bins, "<<Width(UserDefine::HIST_X_MIN,UserDefine::HIST_X_MAX,UserDefine::HIST_BIN_NUMBER)<<'\n'
      <<"fit: "<<UserDefine::FIT_HIST_X_MIN<<" .. "<<UserDefine::FIT_HIST_X_MAX<<" ns, "<<UserDefine::FIT_HIST_BIN_NUMBER
      <<" bins, "<<Width(UserDefine::FIT_HIST_X_MIN,UserDefine::FIT_HIST_X_MAX,UserDefine::FIT_HIST_BIN_NUMBER)<<std::endl;
    for(Long64_t i=0;i<count;++i) {
        Require(tree->GetEntry(i)>0,"Read failed at entry "+std::to_string(i)); ++processed;
        Address a{hit.cid,hit.sid,hit.ch};
        Require(ValidAddress(a),"Invalid negative input address at entry "+std::to_string(i));
        if(!Accepted(a)) { ++rejected; continue; }
        int tick=Tick(hit.sr);
        Require(hit.ts>=0 && hit.ts<=std::numeric_limits<Long64_t>::max()/tick,"Timestamp ns overflow");
        Long64_t ns=hit.ts*tick;
        if(accepted && ns<previous) ++regressions; // 倒序只记录，不添加计划以外的切包规则。
        previous=ns; ++accepted;
        ProcessEntry(a,ns,tick);
        if((i+1)%10000000==0) std::cout<<"Read "<<i+1<<" / "<<count<<std::endl;
    }
    EndEvent();
    Require(reference_hits>0,"No reference hits found; no calibration outputs produced");
    Write(run,fs::canonical(input).string(),output,fit);
}
// 三个基础文件同名；CSV保留范围诊断，ROOT仅保存非空谱及选中总函数。
void TimeOffset::Write(int run,const std::string &input,const std::string &output,bool enabled) {
    std::string base=(fs::path(output)/("time_offset_"+std::to_string(run))).string();
    TFile target((base+".root").c_str(),"CREATE"); Require(!target.IsZombie(),"Cannot create output ROOT");
    std::ofstream csv(base+".csv"),md(base+".md"); Require(bool(csv)&&bool(md),"Cannot create CSV/MD");
    csv<<std::setprecision(12);
    csv<<"cid,sid,ch,final_mean,time_offset,status,mean_error_ns,tick_ns,hits,pairs,model,fit_status,covariance,low_ns,high_ns,A1,mu1_ns,sigma1_ns,area1,A2,mu2_ns,sigma2_ns,area2,deviance,ndf,deviance_ndf,peak_deviance_ndf,side_deviance_ndf,range_mean_span_ns,expected_residual_ns,fine_underflow,fine_overflow,fit_underflow,fit_overflow,reason,range_diagnostics\n";
    std::map<std::string,int> statuses;
    std::vector<std::string> review;
    int numeric=0,doubles=0;
    double worst_span=0;
    for(auto &item:spectra) {
        Address a=item.first; Spectrum &s=item.second; Result result;
        if(a==Ref()) result.status="reference";
        else result=Analyze(s,enabled);
        Fit &f=result.fit;
        if(a==Ref()) { f.mean=0; f.error=0; }
        double offset=NaN;
        if(a==Ref()) offset=0;
        else if(f.numeric && s.ticks.size()==1) offset=Offset(f.mean,*s.ticks.begin());
        if(!(a==Ref()) && s.ticks.size()!=1) {
            result.reason+="mixed_timestamp_ticks;";
            if(f.numeric) result.status="review";
        }
        if(f.numeric) { ++numeric; if(f.components==2) ++doubles; }
        if(std::isfinite(result.sensitivity)) worst_span=std::max(worst_span,result.sensitivity);
        ++statuses[result.status];
        if(result.status!="ok" && result.status!="reference") review.push_back(Name(a)+": "+result.status+" "+result.reason);
        csv<<a.cid<<','<<a.sid<<','<<a.ch<<','; Cell(csv,f.mean); csv<<','; Cell(csv,offset);
        csv<<','<<result.status<<','; Cell(csv,f.error); csv<<',';
        if(s.ticks.size()==1) csv<<*s.ticks.begin();
        csv<<','<<s.hits<<','<<s.fine->GetEntries()<<','<<(f.function?(f.components==2?"double_gauss_pol1":"gauss_pol1"):"none")<<',';
        if(f.function) csv<<f.status;
        csv<<','; if(f.function) csv<<f.covariance;
        csv<<','; if(f.function) csv<<f.range.low;
        csv<<','; if(f.function) csv<<f.range.high;
        for(int j=0;j<2;++j) {
            for(int k=0;k<3;++k) { csv<<','; if(f.function && j<f.components) csv<<f.function->GetParameter(3*j+k); }
            csv<<','; Cell(csv,f.areas[j]);
        }
        csv<<','; Cell(csv,f.deviance); csv<<','; if(f.function) csv<<f.ndf;
        csv<<','; if(f.function) Cell(csv,f.deviance/f.ndf);
        csv<<','; Cell(csv,f.peak_deviance); csv<<','; Cell(csv,f.side_deviance);
        csv<<','; Cell(csv,result.sensitivity); csv<<',';
        if(std::isfinite(offset)) Cell(csv,f.mean-offset);
        csv<<','<<s.fine->GetBinContent(0)<<','<<s.fine->GetBinContent(s.fine->GetNbinsX()+1)
           <<','<<s.coarse->GetBinContent(0)<<','<<s.coarse->GetBinContent(s.coarse->GetNbinsX()+1)<<','<<result.reason<<',';
        for(const auto &trial:result.trials) {
            csv<<trial.range.low<<':'<<trial.range.high<<':'<<trial.components<<':'<<trial.status<<':'<<trial.covariance<<':';
            Cell(csv,trial.mean); csv<<':'; Cell(csv,trial.deviance); csv<<':'<<trial.ndf<<':';
            Cell(csv,trial.single_bic); csv<<':'; Cell(csv,trial.double_bic); csv<<';';
        }
        csv<<'\n';
        if(f.function) {
            auto *saved=static_cast<TF1*>(f.function->Clone("time_fit"));
            saved->SetLineColor(result.status=="ok"?2:6); saved->SetNpx(1000);
            s.coarse->GetListOfFunctions()->Add(saved);
            int n=saved->GetNpar(); TMatrixDSym covariance(n);
            for(int i=0;i<n;++i) for(int j=0;j<n;++j) covariance(i,j)=f.covariance_values[i*n+j];
            covariance.Write((Name(a)+"_covariance").c_str());
        }
        if(s.fine->GetEntries()>0) s.fine->Write();
        if(s.coarse->GetEntries()>0) s.coarse->Write();
    }
    std::ostringstream config;
    config<<"ref="<<Name(Ref())<<";dt=t_ref-t_channel;window_ns="<<UserDefine::EVENT_WINDOW_NS
       <<";Ge="<<UserDefine::GE_CID<<":last;CsI="<<UserDefine::CSI_CID<<":all;fit="<<enabled
       <<";cid_cut="<<UserDefine::CID_CUT_MIN<<':'<<UserDefine::CID_CUT_MAX
       <<";sid_cut="<<UserDefine::SID_CUT_MIN<<':'<<UserDefine::SID_CUT_MAX
       <<";ch_cut="<<UserDefine::CH_CUT_MIN<<':'<<UserDefine::CH_CUT_MAX
       <<";fine="<<UserDefine::HIST_X_MIN<<':'<<UserDefine::HIST_X_MAX<<':'<<UserDefine::HIST_BIN_NUMBER
       <<";fit_hist="<<UserDefine::FIT_HIST_X_MIN<<':'<<UserDefine::FIT_HIST_X_MAX<<':'<<UserDefine::FIT_HIST_BIN_NUMBER
       <<";smooth_fwhm_ns="<<UserDefine::SMOOTH_NS<<";second_min_ns="<<UserDefine::SECOND_SEPARATION_NS
       <<";bic_improvement="<<UserDefine::BIC_IMPROVEMENT<<";sideband_block_ns="<<UserDefine::SIDEBAND_BLOCK_NS
       <<";min_pairs="<<UserDefine::MIN_PAIRS<<";peak_significance="<<UserDefine::PEAK_SIGNIFICANCE
       <<";second_height_fraction="<<UserDefine::SECOND_HEIGHT_FRACTION<<";valley_fraction="<<UserDefine::VALLEY_FRACTION
       <<";tail_fraction="<<UserDefine::TAIL_FRACTION<<";shoulder_residual_fraction="<<UserDefine::SHOULDER_RESIDUAL_FRACTION
       <<";local_background_ns="<<UserDefine::LOCAL_BACKGROUND_INNER_NS<<':'<<UserDefine::LOCAL_BACKGROUND_OUTER_NS
       <<";curvature_z="<<UserDefine::SIDEBAND_CURVATURE_Z<<";sigma_min_initial_ns="<<UserDefine::MIN_SIGMA_NS<<':'<<UserDefine::INITIAL_SIGMA_NS
       <<";deviance_review="<<UserDefine::DEVIANCE_REVIEW<<";component_significance="<<UserDefine::COMPONENT_SIGNIFICANCE;
    config<<";sideband_blocks=";
    for(int n:UserDefine::SIDEBAND_BLOCKS) config<<n<<':';
    config<<";sr_ticks_ns=";
    for(const auto &p:UserDefine::SR_TICK_NS) config<<p.first<<':'<<p.second<<'|';
    TNamed("source",input.c_str()).Write(); TNamed("configuration",config.str().c_str()).Write();
    TNamed("software","ROOT Poisson likelihood; bin-average integral; positive-endpoint pol1; raw count spectra").Write();
    for(auto p:std::vector<std::pair<const char*,Long64_t>>{{"input_entries",input_entries},{"processed_entries",processed},
       {"accepted_entries",accepted},{"rejected_addresses",rejected},{"events",events},{"reference_events",reference_events},
       {"reference_hits",reference_hits},{"time_regressions",regressions}}) TParameter<Long64_t>(p.first,p.second).Write();
    target.Close();
    md<<"# 单文件时间对齐结果\n\n输入：`"<<input<<"`；run="<<run<<"。\n\n"
      <<"读取条目："<<processed<<" / "<<input_entries<<"（零起始范围 [0,"<<processed<<")）；保留："<<accepted
      <<"；地址cut排除："<<rejected<<"。事件包："<<events<<"；含参考包："<<reference_events
      <<"；参考命中："<<reference_hits<<"；保留序列时间倒序："<<regressions<<"。\n\n"
      <<"配置：`"<<config.str()<<"`。完整工程阈值见同版本 UserDefine.hh。\n\n";
    for(const auto &p:statuses) md<<"- "<<p.first<<"："<<p.second<<"\n";
    md<<"\n数值拟合有效："<<numeric<<"，其中双高斯："<<doubles<<"。候选区间间 final_mean 最大跨度："<<worst_span<<" ns。\n\n"
      <<"final_mean 为高斯完整净面积加权中心，time_offset 为按目标tick向零截断的ns值；加到目标通道时间。"
      <<"误差来自同模型联合协方差，不含模型选择、事件包边界、范围选择或run内漂移的系统影响。"
      <<"review保留可计算候选，不代表校准通过；deviance/ndf>3只作经验回查提示。"
      <<"固定事件包会遗漏跨包近邻；双峰中心归零不使两峰合并。"
      <<"空谱不写ROOT，上下溢出保留；未拟合和失败数值留空。\n\n"
      <<"CSV range_diagnostics 依次为 low:high:分量数:ROOT状态:协方差状态:final_mean:deviance:ndf:single_BIC:double_BIC；范围跨度仅是敏感性诊断，不设额外通过门槛。\n\n";
    if(!review.empty()) {
        md<<"重点回查通道：\n\n";
        for(const auto &line:review) md<<"- "<<line<<'\n';
    }
    Require(bool(csv)&&bool(md),"CSV/MD write failed");
    std::cout<<"processed="<<processed<<" events="<<events<<" ref_events="<<reference_events<<" numeric_fits="<<numeric
      <<" double="<<doubles<<" max_range_span_ns="<<worst_span<<std::endl;
    for(const auto &p:statuses) std::cout<<p.first<<'='<<p.second<<' ';
    std::cout<<'\n'<<base<<".{root,csv,md}"<<std::endl;
}

// 确定性算法检查；合成数据只存在于测试内存，不混入实验结果。
void TimeOffset::SelfCheck() {
    Validate();
    assert(Cut(0,0,1) && Cut(1,0,1) && !Cut(2,0,1));
    assert(Cut(100,-1,-1) && Cut(2,2,-1) && !Cut(1,2,-1));
    assert(Cut(16,-1,16) && !Cut(17,-1,16) && Cut(5,5,5) && !Cut(4,5,5));
    bool bad=false; try { CheckCut(2,1); } catch(...) { bad=true; } assert(bad);
    assert(Tick(125)==8 && Tick(250)==8 && Tick(100)==10 && Tick(500)==10);
    bad=false; try { Tick(123); } catch(...) { bad=true; } assert(bad);
    TimeOffset t;
    Address ref=Ref(),g{UserDefine::GE_CID,2,10},c{UserDefine::CSI_CID,3,7};
    t.ProcessEntry(g,10000,8); t.ProcessEntry(g,10080,8);
    t.ProcessEntry(c,10100,10); t.ProcessEntry(c,10120,10);
    t.ProcessEntry(ref,10200,8); t.ProcessEntry(ref,10240,8);
    t.ProcessEntry(g,11999,8); // |dt到固定起点|恰好W，仍在同包。
    t.ProcessEntry(g,12000,8); // 新包，前包Ge末次11999，对应Delta-t=-1759。
    t.ProcessEntry(ref,12080,8); t.EndEvent(); // 末包保留。
    assert(t.events==2 && t.reference_events==2);
    assert(t.spectra[g].fine->GetEntries()==2 && t.spectra[c].fine->GetEntries()==2);
    assert(t.spectra[g].fine->GetBinContent(t.spectra[g].fine->FindBin(-1759))==1);
    assert(t.spectra[c].fine->GetBinContent(t.spectra[c].fine->FindBin(120))==1);
    assert(t.spectra[ref].fine->GetEntries()==0);
    TimeOffset reverse;
    reverse.ProcessEntry(ref,10000,8); reverse.ProcessEntry(g,8001,8); reverse.ProcessEntry(g,8000,8); reverse.EndEvent();
    assert(reverse.events==2 && reverse.spectra[g].fine->GetEntries()==1); // 绝对值W边界。
    t.Fill(g,2000); t.Fill(g,-2000); t.Fill(g,9000);
    auto &h=*t.spectra[g].fine;
    assert(h.FindBin(-2000)>0 && h.FindBin(2000)<=h.GetNbinsX());
    assert(h.GetBinContent(h.GetNbinsX()+1)==1);
    assert(h.Integral(0,h.GetNbinsX()+1)==t.spectra[g].coarse->Integral(0,t.spectra[g].coarse->GetNbinsX()+1));
    assert(Offset(22.7,8)==16 && Offset(-22.7,8)==-16 && Offset(29.9,10)==20 && Offset(-29.9,10)==-20);
    std::vector<double> p{10,-20,5,10,60,5,2,2},cov(64,0);
    for(int i=0;i<8;++i) cov[i*8+i]=0.01;
    assert(std::abs(Center(p,cov,2).first-20)<1e-10);
    p[5]=15; assert(std::abs(Center(p,cov,2).first-40)<1e-10);
    auto a=Center(p,cov,2);
    for(int i=0;i<3;++i) std::swap(p[i],p[i+3]);
    assert(std::abs(Center(p,cov,2).first-a.first)<1e-10);
    for(int i:{0,3}) p[i]*=100;
    assert(std::abs(Center(p,cov,2).first-a.first)<1e-10);
    p={10,-20,5,0,60,5,2,2}; assert(Center(p,cov,2).first==-20);
    p={10,-20,5,8,60,15,2,2};
    // 独立中心差分核对JCJ^T，包含非零协方差项。
    cov[1*8+4]=cov[4*8+1]=0.002;
    std::vector<double> gradient(8);
    for(int i=0;i<8;++i) {
        auto lo=p,hi=p; double step=1e-5; lo[i]-=step; hi[i]+=step;
        gradient[i]=(Center(hi,cov,2).first-Center(lo,cov,2).first)/(2*step);
    }
    double variance=0;
    for(int i=0;i<8;++i) for(int j=0;j<8;++j) variance+=gradient[i]*cov[i*8+j]*gradient[j];
    assert(std::abs(std::pow(Center(p,cov,2).second,2)-variance)<1e-7);
    Spectrum synthetic;
    synthetic.fine.reset(new TH1D("synthetic_fine","",HIST_BIN_NUMBER,HIST_X_MIN,HIST_X_MAX));
    synthetic.coarse.reset(new TH1D("synthetic_coarse","",FIT_HIST_BIN_NUMBER,FIT_HIST_X_MIN,FIT_HIST_X_MAX));
    TF1 truth("truth","gaus(0)+gaus(3)+pol1(6)",HIST_X_MIN,HIST_X_MAX);
    truth.SetParameters(400,-180,30,250,60,40,10,0);
    for(auto *hist:{synthetic.fine.get(),synthetic.coarse.get()}) {
        for(int i=1;i<=hist->GetNbinsX();++i)
            hist->SetBinContent(i,truth.Integral(hist->GetBinLowEdge(i),hist->GetBinLowEdge(i+1))/24);
    }
    auto shape=FindShape(*synthetic.fine); assert(shape.signal && shape.two);
    auto result=Analyze(synthetic,true);
    assert(result.fit.numeric && result.fit.components==2);
    double expected=(-180*400*30+60*250*40)/(400*30+250*40);
    assert(std::abs(result.fit.mean-expected)<1);
    assert(Analyze(synthetic,false).status=="not_fitted");
    std::cout<<"Self-check passed: cuts, fixed anchor, +/-W, Ge/CsI, final packet, flow, area/covariance, ROOT fit"<<std::endl;
}

// 可选旧谱只读诊断，绝不作为新实验谱或正式offset输出。
void TimeOffset::InspectSpectrum(const std::string &file,const std::string &name) {
    TFile source(file.c_str(),"READ"); Require(!source.IsZombie(),"Cannot open spectrum source");
    auto *fine=dynamic_cast<TH1D*>(source.Get((name+"_2ns").c_str()));
    auto *coarse=dynamic_cast<TH1D*>(source.Get((name+"_24ns").c_str()));
    Require(fine && coarse,"Missing representative spectrum");
    Spectrum s;
    s.fine.reset(static_cast<TH1D*>(fine->Clone("inspect_fine"))); s.fine->SetDirectory(nullptr);
    s.coarse.reset(static_cast<TH1D*>(coarse->Clone("inspect_coarse"))); s.coarse->SetDirectory(nullptr);
    auto shape=FindShape(*s.fine);
    std::cout<<"seed="<<shape.peak<<" second="<<shape.second<<" two="<<shape.two<<" tails="<<shape.left<<':'<<shape.right<<'\n';
    std::vector<std::pair<double,double>> peaks;
    for(int i=2;i<s.fine->GetNbinsX();++i)
        if(shape.smooth[i]>=shape.smooth[i-1] && shape.smooth[i]>shape.smooth[i+1]) peaks.emplace_back(shape.smooth[i],s.fine->GetBinCenter(i));
    std::sort(peaks.rbegin(),peaks.rend());
    for(size_t i=0;i<std::min(size_t(8),peaks.size());++i) std::cout<<" smooth_max="<<peaks[i].second<<':'<<peaks[i].first;
    std::cout<<'\n';
    auto result=Analyze(s,true);
    std::cout<<std::setprecision(12)<<name<<" status="<<result.status<<" reason="<<result.reason
      <<" mean="<<result.fit.mean<<" error="<<result.fit.error<<" components="<<result.fit.components
      <<" span="<<result.sensitivity<<'\n';
    for(const auto &f:result.trials)
        std::cout<<"  range="<<f.range.low<<':'<<f.range.high<<" model="<<f.components<<" mean="<<f.mean
          <<" deviance="<<f.deviance<<" ndf="<<f.ndf<<" side="<<f.side_deviance<<" peak="<<f.peak_deviance
          <<" BIC_single="<<f.single_bic<<" BIC_double="<<f.double_bic<<'\n';
}
