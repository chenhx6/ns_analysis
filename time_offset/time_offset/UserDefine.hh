#ifndef TIME_OFFSET_USER_DEFINE_HH
#define TIME_OFFSET_USER_DEFINE_HH
#include <array>
#include <utility>

// 实验配置：路径只指向只读输入；输出相对运行目录，默认在源码目录运行。
namespace UserDefine {
constexpr const char *INPUT_DIRECTORY = "/home/ys/data_401/data/chx_20260622/decode_data";
constexpr const char *INPUT_PATTERN = "data_C2_{run}_{run}_wave.root";
constexpr const char *OUTPUT_DIRECTORY = "..";
constexpr const char *TREE_NAME = "tree";
constexpr const char *TS_FIELD = "ts", *CID_FIELD = "cid", *SID_FIELD = "sid";
constexpr const char *CH_FIELD = "ch", *SR_FIELD = "sr";
constexpr int REF_CID = 0, REF_SID = 2, REF_CH = 5;
constexpr int CID_CUT_MIN = 0, CID_CUT_MAX = 1;
constexpr int SID_CUT_MIN = 0, SID_CUT_MAX = 16;
constexpr int CH_CUT_MIN = -1, CH_CUT_MAX = -1;
constexpr int GE_CID = 0, CSI_CID = 1; // Ge末次命中；CsI所有命中。
constexpr long long EVENT_WINDOW_NS = 1999;
constexpr std::array<std::pair<int, int>, 4> SR_TICK_NS{{{125,8},{250,8},{100,10},{500,10}}};
constexpr double HIST_X_MIN = -2001, HIST_X_MAX = 2001;
constexpr int HIST_BIN_NUMBER = 2001;
constexpr double FIT_HIST_X_MIN = -2016, FIT_HIST_X_MAX = 2016;
constexpr int FIT_HIST_BIN_NUMBER = 168;
constexpr bool FIT_ENABLED = true;
// 工程阈值集中在此；时间量均为ns，未用通道例外表。
constexpr double SMOOTH_NS = 50; // 临时高斯平滑的FWHM，抑制8/10ns格点。
constexpr int MIN_PAIRS = 100;
constexpr double PEAK_SIGNIFICANCE = 5, SECOND_HEIGHT_FRACTION = 0.2;
constexpr double SECOND_SEPARATION_NS = 72, VALLEY_FRACTION = 0.85;
constexpr double SHOULDER_RESIDUAL_FRACTION = 0.05; // 单峰残差中可信肩峰候选。
constexpr double TAIL_FRACTION = 0.05, SIDEBAND_BLOCK_NS = 96;
constexpr std::array<int,3> SIDEBAND_BLOCKS{{1,2,4}};
constexpr double SIDEBAND_CURVATURE_Z = 4, BIC_IMPROVEMENT = 10;
constexpr double LOCAL_BACKGROUND_INNER_NS = 300, LOCAL_BACKGROUND_OUTER_NS = 600;
constexpr double MIN_SIGMA_NS = 6, INITIAL_SIGMA_NS = 36;
constexpr double DEVIANCE_REVIEW = 3, COMPONENT_SIGNIFICANCE = 3;
}
#endif
