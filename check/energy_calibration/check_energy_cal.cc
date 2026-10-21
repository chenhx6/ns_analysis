// check_energy_cal.cc
// 读取 ROOT 文件中的 (cid, sid, ch, evte)，用 cal.dat 的刻度系数
// E = a0 + a1*evte + a2*evte*evte 计算能量，绘制 TH2D (x=能量, y=探测器编号) colz。
//
// 用法: root -l -b -q 'check_energy_cal.cc'
//   或修改下方路径后编译运行。

#include "TFile.h"
#include "TTree.h"
#include "TH2D.h"
#include "TCanvas.h"
#include "TStyle.h"

#include <fstream>
#include <sstream>
#include <iostream>
#include <map>
#include <tuple>

// ============ 用户输入区 ============
// ROOT 原始文件地址
const char* rootFilePath = "/home/ys/data_401/data/chx_20260622/decode_data/data_C1_6082_notwave.root";
// 能量刻度系数文件地址
const char* calFilePath  = "./cal.dat";
// ====================================

// 刻度系数结构
struct CalParam {
    double a0, a1, a2;
};

void check_energy_cal()
{
    // --- 1. 读取刻度系数 ---
    // key: (cid, sid, ch) -> CalParam
    std::map<std::tuple<int,int,int>, CalParam> calMap;

    std::ifstream calFile(calFilePath);
    if (!calFile.is_open()) {
        std::cerr << "无法打开刻度系数文件: " << calFilePath << std::endl;
        return;
    }

    std::string line;
    std::getline(calFile, line); // 跳过表头
    while (std::getline(calFile, line)) {
        if (line.empty()) continue;
        std::istringstream iss(line);
        int cid, sid, ch;
        double a0, a1, a2;
        if (!(iss >> cid >> sid >> ch >> a0 >> a1 >> a2)) continue;
        calMap[std::make_tuple(cid, sid, ch)] = {a0, a1, a2};
    }
    calFile.close();
    std::cout << "读取刻度系数: " << calMap.size() << " 个通道" << std::endl;

    // 为每个通道分配一个探测器编号 (y 轴), 按 (cid, sid, ch) 排序
    std::map<std::tuple<int,int,int>, int> detIndex;
    int idx = 0;
    for (auto &kv : calMap) {
        detIndex[kv.first] = idx++;
    }
    int nDet = idx;

    // --- 2. 打开 ROOT 文件 ---
    TFile *f = TFile::Open(rootFilePath);
    if (!f || f->IsZombie()) {
        std::cerr << "无法打开 ROOT 文件: " << rootFilePath << std::endl;
        return;
    }
    TTree *tree = (TTree*)f->Get("tree");
    if (!tree) {
        std::cerr << "未找到 tree" << std::endl;
        return;
    }

    Short_t cid, sid, ch;
    UShort_t evte;
    tree->SetBranchAddress("cid",  &cid);
    tree->SetBranchAddress("sid",  &sid);
    tree->SetBranchAddress("ch",   &ch);
    tree->SetBranchAddress("evte", &evte);

    // --- 3. 创建 TH2D ---
    // x: 能量 (keV), y: 探测器编号
    TH2D *h2 = new TH2D("h2_ecal", "Energy Calibration Check;Energy (keV);Detector",
                         4000, 0, 4000, nDet, 0, nDet);

    // 设置 y 轴标签: "cid-sid-ch"
    for (auto &kv : detIndex) {
        auto &key = kv.first;
        char label[32];
        snprintf(label, sizeof(label), "%d-%d-%d",
                 std::get<0>(key), std::get<1>(key), std::get<2>(key));
        h2->GetYaxis()->SetBinLabel(kv.second + 1, label);
    }

    // --- 4. 遍历 tree, 刻度并填充 ---
    Long64_t nEntries = tree->GetEntries();
    std::cout << "总事件数: " << nEntries << std::endl;

    for (Long64_t i = 0; i < nEntries; i++) {
        tree->GetEntry(i);
        auto key = std::make_tuple((int)cid, (int)sid, (int)ch);
        auto it = calMap.find(key);
        if (it == calMap.end()) continue; // 无刻度系数, 跳过

        double e = (double)evte;
        double energy = it->second.a0 + it->second.a1 * e + it->second.a2 * e * e;
        h2->Fill(energy, detIndex[key] + 0.5);
    }

    // --- 5. 绘图 ---
    gStyle->SetOptStat(0);
    TCanvas *c1 = new TCanvas("c1", "Energy Calibration Check", 1200, 800);
    c1->SetLogz();
    h2->Draw("colz");
    c1->SaveAs("h2_energy_cal.root");
    std::cout << "已保存: h2_energy_cal.root" << std::endl;

    f->Close();
}

