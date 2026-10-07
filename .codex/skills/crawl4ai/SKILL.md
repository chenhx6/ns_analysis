---
name: crawl4ai
description: 使用项目内 Crawl4AI 读取网页、抽取正文或结构化字段，并将抓取结果保存到本项目。
---

# 项目网页抓取

上游源码：`analysis/vendor/crawl4ai/`；版本和许可证见 `analysis/third_party/`。完整 Python extras 安装在 `.runtime/site-packages/`，专用解释器和 Chromium 位于 `.runtime/`。通过 `python3 analysis/scripts/project_runtime.py python <script>` 启动，以设置项目内缓存及数据盘执行兼容层。

读取上游示例和当前 API 后使用 `AsyncWebCrawler`、`BrowserConfig`、`CrawlerRunConfig`。抓取脚本放入 `analysis/<任务名>/`，小型报告放入该任务的 `reports/`；大批量 HTML、截图和抽取数据写入项目内专用中间数据目录。输入为用户指定的网页和任务范围，不自行扩大抓取范围或发送消息。

支持常规 Playwright 与 undetected Patchright Chromium；浏览器在临时执行缓存中运行，项目内保留完整安装副本。不运行上游 `crawl4ai-setup --with-deps` 路径，因为该路径会尝试系统安装。模型权重按实际任务下载到 `.runtime/huggingface/`，不把包安装误称为已下载全部模型。
