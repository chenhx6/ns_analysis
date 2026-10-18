#include "../../../time_offset/time_offset/time_offset.cc"
#include <TFile.h>
#include <TTree.h>
#include <TKey.h>
#include <TParameter.h>
#include <TF1.h>
#include <TMatrixDSym.h>
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unistd.h>

// 仅此开发测试编译单元访问内部步骤；不向正式程序增加测试命令。
struct TimeOffsetChecks { static void SelfCheck(); };
// 确定性算法检查；合成数据只存在于测试内存，不混入实验结果。
void TimeOffsetChecks::SelfCheck() {
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
void InspectSpectrum(const std::string &file,const std::string &name) {
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

using Row=std::map<std::string,std::string>;
// 简单无引号CSV是本程序固定输出；读取时保留末尾空字段。
std::vector<std::string> Split(const std::string &s,char delimiter=',') {
    std::vector<std::string> values;
    size_t start=0,end;
    while((end=s.find(delimiter,start))!=std::string::npos) { values.push_back(s.substr(start,end-start)); start=end+1; }
    values.push_back(s.substr(start)); return values;
}
std::vector<Row> Rows(const std::string &path) {
    std::ifstream file(path); assert(file);
    std::string line; std::getline(file,line); auto header=Split(line);
    std::vector<Row> rows;
    while(std::getline(file,line)) {
        auto cells=Split(line); assert(cells.size()==header.size());
        Row row;
        for(size_t i=0;i<header.size();++i) row[header[i]]=cells[i];
        rows.push_back(row);
    }
    return rows;
}
// ROOT/CSV独立回读：计数含flow、函数参数/面积中心/协方差/截断逐行一致。
void CheckOutputs(const std::string &base,bool fit) {
    TFile file((base+".root").c_str(),"READ"); assert(!file.IsZombie());
    auto rows=Rows(base+".csv"); assert(!rows.empty());
    int expected_histograms=0,actual_histograms=0;
    for(auto *object:*file.GetListOfKeys()) {
        auto *key=dynamic_cast<TKey*>(object); assert(key);
        if(std::string(key->GetClassName())=="TH1D") ++actual_histograms;
    }
    for(auto row:rows) {
        std::string name="cid"+row["cid"]+"_sid"+row["sid"]+"_ch"+row["ch"];
        auto *fine=dynamic_cast<TH1D*>(file.Get((name+"_2ns").c_str()));
        auto *coarse=dynamic_cast<TH1D*>(file.Get((name+"_24ns").c_str()));
        double pairs=std::stod(row["pairs"]);
        if(pairs==0) { assert(!fine && !coarse); }
        else {
            expected_histograms+=2; assert(fine && coarse);
            assert(fine->GetEntries()==pairs && coarse->GetEntries()==pairs);
            assert(fine->Integral(0,fine->GetNbinsX()+1)==pairs);
            assert(coarse->Integral(0,coarse->GetNbinsX()+1)==pairs);
            assert(fine->GetNbinsX()==UserDefine::HIST_BIN_NUMBER && coarse->GetNbinsX()==UserDefine::FIT_HIST_BIN_NUMBER);
            assert(fine->GetXaxis()->GetXmin()==UserDefine::HIST_X_MIN && fine->GetXaxis()->GetXmax()==UserDefine::HIST_X_MAX);
            assert(coarse->GetXaxis()->GetXmin()==UserDefine::FIT_HIST_X_MIN && coarse->GetXaxis()->GetXmax()==UserDefine::FIT_HIST_X_MAX);
            if(!fit) assert(!coarse->GetFunction("time_fit"));
        }
        auto status=row["status"];
        assert(status=="reference" || status=="not_fitted" || status=="no_peak" || status=="fit_failed" || status=="review" || status=="ok");
        if(status=="reference") { assert(row["final_mean"]=="0" && row["time_offset"]=="0" && !fine && !coarse); continue; }
        if(!fit) assert(status=="not_fitted");
        if(status=="not_fitted" || status=="no_peak" || status=="fit_failed") {
            assert(row["final_mean"].empty() && row["time_offset"].empty()); continue;
        }
        assert(fit && coarse);
        auto *f=coarse->GetFunction("time_fit"); assert(f);
        bool two=row["model"]=="double_gauss_pol1";
        double mean=f->GetParameter(1),variance=0,bin=coarse->GetBinWidth(1);
        int n=f->GetNpar();
        auto *cov=dynamic_cast<TMatrixDSym*>(file.Get((name+"_covariance").c_str())); assert(cov && cov->GetNrows()==n);
        std::vector<double> gradient(n,0);
        gradient[1]=1;
        if(two) {
            double w1=f->GetParameter(0)*f->GetParameter(2),w2=f->GetParameter(3)*f->GetParameter(5),sum=w1+w2;
            mean=(w1*f->GetParameter(1)+w2*f->GetParameter(4))/sum;
            gradient.assign(n,0);
            for(int k:{0,3}) {
                gradient[k]=f->GetParameter(k+2)*(f->GetParameter(k+1)-mean)/sum;
                gradient[k+1]=f->GetParameter(k)*f->GetParameter(k+2)/sum;
                gradient[k+2]=f->GetParameter(k)*(f->GetParameter(k+1)-mean)/sum;
            }
        }
        for(int i=0;i<n;++i) for(int j=0;j<n;++j) variance+=gradient[i]*(*cov)(i,j)*gradient[j];
        assert(std::abs(mean-std::stod(row["final_mean"]))<1e-7);
        assert(std::abs(std::sqrt(variance)-std::stod(row["mean_error_ns"]))<1e-6);
        for(int j=0;j<(two?2:1);++j) {
            double area=f->GetParameter(3*j)*f->GetParameter(3*j+2)*std::sqrt(2*std::acos(-1.0))/bin;
            assert(std::abs(area-std::stod(row[j?"area2":"area1"]))<1e-6*std::max(1.0,area));
        }
        if(!row["time_offset"].empty()) {
            int tick=std::stoi(row["tick_ns"]);
            assert(std::stod(row["time_offset"])==tick*std::trunc(mean/tick));
        }
        assert(f->GetXmin()>=-UserDefine::EVENT_WINDOW_NS && f->GetXmax()<=UserDefine::EVENT_WINDOW_NS);
        if(status=="ok") assert(std::stod(row["side_deviance_ndf"])<=UserDefine::DEVIANCE_REVIEW);
    }
    assert(expected_histograms==actual_histograms);
    assert(file.Get("configuration") && file.Get("source") && file.Get("processed_entries"));
    assert(fs::file_size(base+".md")>0);
    std::cout<<"Output checks passed: "<<rows.size()<<" CSV channels, "<<actual_histograms<<" nonempty histograms"<<std::endl;
}
// 测试文件写在独立临时目录；错误输入不得生成成功结果。
void IOCheck() {
    fs::path dir=fs::temp_directory_path()/("chx-time-offset-io-"+std::to_string(getpid()));
    fs::create_directory(dir);
    auto fixture=[&](const char *name,int mode) {
        std::string path=(dir/name).string(); TFile file(path.c_str(),"CREATE");
        TTree tree("tree",""); Hit h;
        tree.Branch("ts",&h.ts,"ts/L"); tree.Branch("cid",&h.cid,"cid/S"); tree.Branch("sid",&h.sid,"sid/S");
        tree.Branch("ch",&h.ch,"ch/S"); if(mode!=3) tree.Branch("sr",&h.sr,"sr/S");
        h={1000,0,2,Short_t(mode==1?6:5),250}; if(mode==2) h.sr=123; tree.Fill();
        h={1010,0,2,6,250}; tree.Fill();
        if(mode==4) { h={810,0,2,6,100}; tree.Fill(); } // 同通道8/10ns tick。
        tree.Write(); return path;
    };
    auto good=fixture("good.root",0);
    TimeOffset().Process(1,good,(dir/"off").string(),0,false);
    CheckOutputs((dir/"off/time_offset_1").string(),false);
    // 覆盖已有结果时旧ROOT对象、旧计数和CSV/MD尾部必须全部消失。
    {
        TFile previous((dir/"off/time_offset_1.root").c_str(),"UPDATE");
        TNamed("stale_test_object","previous output").Write();
    }
    for(const char *ext:{".csv",".md"})
        std::ofstream((dir/(std::string("off/time_offset_1")+ext)).string(),std::ios::app)<<"STALE_TEST_SUFFIX\n";
    TimeOffset().Process(1,good,(dir/"off").string(),1,false);
    CheckOutputs((dir/"off/time_offset_1").string(),false);
    {
        TFile recreated((dir/"off/time_offset_1.root").c_str(),"READ");
        assert(!recreated.Get("stale_test_object") && !recreated.Get("cid0_sid2_ch6_2ns"));
        assert(Rows((dir/"off/time_offset_1.csv").string()).size()==1);
    }
    for(const char *ext:{".csv",".md"}) {
        std::ifstream file(dir/(std::string("off/time_offset_1")+ext));
        std::string content((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
        assert(content.find("STALE_TEST_SUFFIX")==std::string::npos);
    }
    TimeOffset().Process(1,good,(dir/"off").string(),0,false);
    CheckOutputs((dir/"off/time_offset_1").string(),false);
    bool failed=false;
    for(auto name_mode:std::vector<std::pair<const char*,int>>{{"no_ref.root",1},{"sr.root",2},{"missing.root",3}}) {
        auto input=fixture(name_mode.first,name_mode.second),output=(dir/(std::string(name_mode.first)+"-out")).string();
        failed=false; try { TimeOffset().Process(1,input,output,0,false); } catch(...) { failed=true; }
        assert(failed && !fs::exists(fs::path(output)/"time_offset_1.root"));
    }
    auto mixed=fixture("mixed.root",4);
    TimeOffset().Process(1,mixed,(dir/"mixed-out").string(),0,false);
    auto rows=Rows((dir/"mixed-out/time_offset_1.csv").string());
    for(const auto &row:rows) if(row.at("ch")=="6") assert(row.at("tick_ns").empty() && row.at("time_offset").empty());
    fs::remove_all(dir); // 只移除本测试明确创建的独立目录。
    std::cout<<"I/O checks passed: branch/sr/reference errors, RECREATE overwrite, FIT=false, mixed ticks"<<std::endl;
}
// 保存的有限样本入口：正式程序不添加测试命令行参数。
int main(int argc,char **argv) {
    try {
        if(argc==2 && std::string(argv[1])=="self") { TimeOffsetChecks::SelfCheck(); IOCheck(); return 0; }
        if(argc==4 && std::string(argv[1])=="inspect") { InspectSpectrum(argv[2],argv[3]); return 0; }
        if((argc==4 || argc==5) && std::string(argv[1])=="check") {
            CheckOutputs(argv[2],std::stoi(argv[3])!=0);
            if(argc==5) {
                TFile file((std::string(argv[2])+".root").c_str(),"READ");
                auto *count=dynamic_cast<TParameter<Long64_t>*>(file.Get("processed_entries"));
                assert(count && count->GetVal()==std::stoll(argv[4]));
                std::cout<<"Processed entry count confirmed: "<<count->GetVal()<<std::endl;
            }
            return 0;
        }
        if(argc==4 && std::string(argv[1])=="compare") {
            TFile a(argv[2],"READ"),b(argv[3],"READ"); assert(!a.IsZombie()&&!b.IsZombie());
            for(auto *object:*a.GetListOfKeys()) {
                auto *key=dynamic_cast<TKey*>(object);
                if(std::string(key->GetClassName())!="TH1D") continue;
                auto *x=dynamic_cast<TH1D*>(a.Get(key->GetName())),*y=dynamic_cast<TH1D*>(b.Get(key->GetName()));
                assert(x&&y&&x->GetEntries()==y->GetEntries()&&x->GetNbinsX()==y->GetNbinsX());
                for(int i=0;i<=x->GetNbinsX()+1;++i) assert(x->GetBinContent(i)==y->GetBinContent(i));
            }
            std::cout<<"FIT on/off spectra agree bin by bin, including flow"<<std::endl; return 0;
        }
        if(argc==7 && std::string(argv[1])=="sample") {
            TimeOffset().Process(std::stoi(argv[2]),argv[3],argv[4],std::stoll(argv[5]),std::stoi(argv[6])!=0); return 0;
        }
        throw std::runtime_error("Usage: verify self | sample run input output entries fit | check base fit | compare a.root b.root | inspect file name");
    } catch(const std::exception &e) { std::cerr<<e.what()<<'\n'; return 1; }
}
