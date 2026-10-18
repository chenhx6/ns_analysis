#include "time_offset.hh"
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

namespace fs=std::filesystem;
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
    bool failed=false;
    try { TimeOffset().Process(1,good,(dir/"off").string(),0,false); } catch(...) { failed=true; } assert(failed);
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
    std::cout<<"I/O checks passed: branch/sr/reference errors, no overwrite, FIT=false, mixed ticks"<<std::endl;
}
// 保存的有限样本入口：正式程序不添加测试命令行参数。
int main(int argc,char **argv) {
    try {
        if(argc==2 && std::string(argv[1])=="self") { TimeOffset::SelfCheck(); IOCheck(); return 0; }
        if(argc==4 && std::string(argv[1])=="inspect") { TimeOffset::InspectSpectrum(argv[2],argv[3]); return 0; }
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
