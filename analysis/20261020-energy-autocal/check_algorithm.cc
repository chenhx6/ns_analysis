// Saved C++ checks and explicitly simulated input: never used as experimental calibration results.
#include "autocal.hh"
#include <cassert>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include "TKey.h"
#include "TNamed.h"
#include <iostream>
#include "TFile.h"
#include "TTree.h"
#include "TList.h"
#include "TROOT.h"
#include "TRandom3.h"
#include "TMatrixDSym.h"

// Exercise known quadratic centroids with non-uniform X errors; reject duplicate centroids and preserve 3-point limits.
void CheckCalibration() {
    std::vector<SourceLine> refs;
    for (double e:{100.,300.,600.,900.,1400.}) refs.push_back({"simulation",e,.001,10.,{}});
    TH1D h("unit","",65536,-.5,65535.5);h.SetDirectory(nullptr);
    auto create=[&](int n,double error_scale,bool perturb) {
        ChannelResult r;
        for (int i=0;i<n;++i) {
            double E=refs[i].energy, a0=1.5,a1=.35,a2=2e-6;
            double mean=(-a1+std::sqrt(a1*a1+4*a2*(E-a0)))/(2*a2);
            FittedPeak p;p.index=i+1;p.ref_E=E;p.ref_err=.001;p.mean=mean;p.mean_err=error_scale*(i+1)*.03;p.used=true;
            if (perturb && i==2) p.mean+=15.;
            r.peaks.push_back(p);
        }
        FitCalibration(r,h,refs);return r;
    };
    auto ideal=create(5,1.,false);
    assert(ideal.status=="success" && ideal.candidate && ideal.ndf==2);
    assert(std::abs(ideal.a[0]-1.5)<.01 && std::abs(ideal.a[1]-.35)<1e-5 && std::abs(ideal.a[2]-2e-6)<1e-8);
    auto noisy=create(5,1.,true), imprecise=create(5,20.,true);
    assert(noisy.status=="poor_fit" || noisy.status=="validation_insufficient");
    assert(imprecise.error[1]>5*noisy.error[1]); // EX propagation must affect covariance.
    auto three=create(3,1.,false),two=create(2,1.,false);
    assert(three.status=="validation_insufficient" && three.ndf==0 && std::isnan(three.probability));
    assert(!two.candidate && two.status=="failed_insufficient_peaks");
    ChannelResult duplicate=ideal;duplicate.peaks[1].mean=duplicate.peaks[0].mean;
    FitCalibration(duplicate,h,refs);assert(duplicate.status=="failed_peak_order");
}

// Known peak locations span the complete source library; sparse ambiguities must not become usable solutions.
void CheckMatcher() {
    PeakFinder finder;
    std::vector<SourceLine> refs;
    for (double e:{81.,121.8,244.7,276.4,302.85,344.28,356.01,383.85,778.9,867.38,964.08,1112.08,1408.01})
        refs.push_back({"simulation",e,.001,10.,{}});
    std::vector<PeakCandidate> candidates;
    for (auto r:refs) candidates.push_back({r.energy/.35,1000.,3.});
    auto match=finder.Match(candidates,refs);
    assert(match.valid && !match.ambiguous && match.pairs.size()==refs.size());
    assert(std::abs(match.gain-.35)<1e-8);
    assert(!finder.Match({{100.,20.,3.},{200.,20.,3.}},refs).valid);
    // Two complete spectra at different gains produce two equally valid associations.
    candidates.clear();
    for (auto r:refs) {candidates.push_back({r.energy/.35,1000.,3.});candidates.push_back({r.energy/.12,1000.,3.});}
    std::sort(candidates.begin(),candidates.end(),[](auto a,auto b){return a.x<b.x;});
    auto ambiguous=finder.Match(candidates,refs);assert(ambiguous.ambiguous);
}

// Generate a seeded two-channel tree, including an older cycle and a deliberately incompatible branch file.
void Fixture(const std::string& path) {
    TFile file(path.c_str(),"RECREATE");TTree tree("tree","SIMULATED gamma source events");
    Short_t cid=0,sid=42,ch=7;UShort_t evte=0;
    tree.Branch("cid",&cid,"cid/S");tree.Branch("sid",&sid,"sid/S");tree.Branch("ch",&ch,"ch/S");tree.Branch("evte",&evte,"evte/s");
    TRandom3 rng(6082);
    for (int i=0;i<100;++i) {evte=i;tree.Fill();}
    tree.Write();
    for (double energy:{121.7817,244.6974,276.3989,302.8508,344.2785,356.0129,383.8485,411.1165,443.965,778.9045,867.380,964.079,1085.837,1112.076,1408.013}) {
        for (int i=0;i<12000;++i) {evte=std::lround(rng.Gaus(energy/.35,2.8));tree.Fill();}
    }
    for (int i=0;i<20000;++i) {evte=rng.Integer(5000);tree.Fill();}
    ch=9;
    for (int i=0;i<1000;++i) {evte=rng.Integer(5000);tree.Fill();}
    tree.Write();file.Close();
    TFile bad((path+".bad.root").c_str(),"RECREATE");TTree wrong("tree","wrong branch type");
    int wrong_id=0;wrong.Branch("cid",&wrong_id,"cid/I");wrong.Fill();wrong.Write();bad.Close();
}

// Independently recompute energy residuals, effective-variance chi2, coefficients and saved peak predictions.
void Inspect(const std::string& path,long long expected,int channels) {
    TFile file(path.c_str(),"READ");assert(!file.IsZombie());
    TIter keys(file.GetListOfKeys());long long count=0;int seen=0;
    while (auto* key=dynamic_cast<TKey*>(keys())) {
        if (std::string(key->GetName())=="h2_energy_cal") continue;
        auto* h=dynamic_cast<TH1D*>(key->ReadObj());assert(h);++seen;
        count+=std::llround(h->Integral(0,h->GetNbinsX()+1));
        auto* meta=dynamic_cast<TNamed*>(h->GetListOfFunctions()->FindObject("autocal_result"));assert(meta);
        std::istringstream in(meta->GetTitle());std::string status,reason;bool candidate=false;int n=0,ndf=0;
        in>>std::quoted(status)>>std::quoted(reason)>>candidate>>n>>ndf;
        auto number=[&](){std::string word;in>>word;return std::stod(word);};
        double chi2=number(),prob=number(),rms=number(),maxde=number();
        for (int i=0;i<4;++i) number();
        double a[3],error[3];for (double& v:a) v=number();for (double& v:error) v=number();
        size_t peaks=0;in>>peaks;double sq=0.,maxabs=0.,effective_chi2=0.;int used=0;
        auto* curve=dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject("energy_pol2"));
        for (size_t k=0;k<peaks;++k) {
            int index=0;in>>index;
            double energy=number(),ey=number(),x=number(),ex=number(),sigma=number(),lo=number(),hi=number();
            bool include;std::string why,fn;in>>include>>std::quoted(why)>>std::quoted(fn);
            auto* f=dynamic_cast<TF1*>(h->GetListOfFunctions()->FindObject(fn.c_str()));
            if (include) {
                assert(f && std::isfinite(x) && ex>0 && ey>=0 && sigma>0);
                assert(f->Eval(x)>0.); // Checks exact fitted function serialization.
                if (curve) {
                    double de=energy-curve->Eval(x),slope=a[1]+2*a[2]*x;
                    sq+=de*de;maxabs=std::max(maxabs,std::abs(de));
                    effective_chi2+=de*de/(ey*ey+slope*slope*ex*ex);++used;
                    for (int p=0;p<3;++p) assert(std::abs(curve->GetParameter(p)-a[p])<1e-12*std::max(1.,std::abs(a[p])));
                }
            }
            (void)lo;(void)hi;
        }
        if (candidate) {
            assert(curve && used==n && used>=3);
            assert(std::abs(std::sqrt(sq/n)-rms)<1e-7 && std::abs(maxabs-maxde)<1e-7);
            assert(std::abs(effective_chi2-chi2)<1e-5*std::max(1.,chi2));
            if (ndf==0) assert(std::isnan(prob));
        }
        delete h;
    }
    assert(count==expected && seen==channels);
    std::cout<<"ROOT independently verified: "<<seen<<" channels, "<<count<<" entries\n";
}

int main(int argc,char** argv) {
    gROOT->SetBatch(true);
    if (argc==2) {CheckCalibration();CheckMatcher();Fixture(argv[1]);std::cout<<"Algorithm and simulated fixture checks passed\n";return 0;}
    if (argc==4) {Inspect(argv[1],std::stoll(argv[2]),std::stoi(argv[3]));return 0;}
    return 2;
}
