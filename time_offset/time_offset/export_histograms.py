"""用法：python3 export_histograms.py 6015"""
import argparse
from pathlib import Path
import re

import ROOT

# 相对目录从本py文件所在目录计算；输出目录中的{run}替换为命令行编号。
INPUT_DIRECTORY = ".."
OUTPUT_DIRECTORY = "../{run}/24ns"
SUFFIX = "_24ns"


def export_histograms(run):
    """只读ROOT，按名称后缀导出直方图及其已有拟合曲线，不重新拟合。"""
    ROOT.gROOT.SetBatch(True)
    directory = Path(__file__).resolve().parent
    output = directory / OUTPUT_DIRECTORY.format(run=run)
    output.mkdir(parents=True, exist_ok=True)
    filename = directory / INPUT_DIRECTORY / f"time_offset_{run}.root"
    with ROOT.TFile.Open(str(filename), "READ") as source:
        canvas = ROOT.TCanvas("export_canvas", "", 1200, 800)
        names = {key.GetName() for key in source.GetListOfKeys() if key.GetName().endswith(SUFFIX)}
        # 按通道数字排序；编号前缀使图片查看器也按相同顺序翻页。
        names = sorted(names, key=lambda name: [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", name)])
        index = 0
        for name in names:
            histogram = source.Get(name)
            if histogram.InheritsFrom("TH1"):
                index += 1
                canvas.Clear()
                # 给已有拟合曲线留出纵轴空间，避免峰顶被画框裁掉。
                peaks = [histogram.GetMaximum()] + [f.GetMaximum() for f in histogram.GetListOfFunctions() if f.InheritsFrom("TF1")]
                histogram.SetMaximum(1.15 * max(peaks))
                histogram.Draw()
                canvas.SaveAs(str(output / f"{index:04d}_{name}.png"))
        canvas.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="按后缀将ROOT直方图及已有拟合曲线导出为PNG")
    parser.add_argument("run", type=int)
    args = parser.parse_args()
    export_histograms(args.run)
