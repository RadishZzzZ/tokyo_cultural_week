# Project Status

## 项目名称

Tokyo Cultural Week｜东京未来一周文化生活简报

## 当前目标

构建一个本地运行的文化简报 App，从少量真实公开来源收集东京未来若干天的文化活动，经过去重、日期和类别过滤、编辑增强与板块编排后，以卡片形式展示，并支持导出 CSV、Markdown 和 ICS。

## 当前版本

v1.0.0

发布状态：MVP 0.1 已完成收口，当前文档版本统一为 `v1.0.0`，准备创建首次 GitHub 发布提交与标签。

## 已完成内容

- Streamlit 本地页面、侧边栏设置和活动卡片展示。
- 页面已改为暖白浅色主题，包含杂志式 Hero、弱化侧栏和 newsletter 风格活动卡片。
- 第二轮 UI 精修已统一侧栏输入控件、多选标签、步进按钮、复选框、折叠区与弹出选项的浅色样式。
- Hero 保留淡色 `TOKYO` 背景字，并加入渐变标题、刊期标记、抽象圆形和极淡东京城市线稿。
- 成功、说明、警告和错误信息改为柔和的编辑注释卡；当前来源改为淡蓝灰说明块。
- 顶部页签图标改为 newsletter 图标，侧栏使用简洁 `TCW` 文字标识。
- 主页面按“本周精选、今晚、展览、电影、讲座、周末散步”顺序展示。
- 活动卡片聚焦标题、日期、地点、推荐理由、标签和来源链接，原始数据仍保留在底部折叠区。
- 侧栏时间范围精简为 `1天 / 3天 / 5天 / 7天 / 10天 / 14天`，默认 7 天。
- 活动类别改为逐行 checkbox，全部取消时会提示至少选择一个类别并禁用生成按钮。
- 保存设置已从侧栏移除；CSV、Markdown、ICS 下载与自动保存集中在结果末尾。
- 来源状态精简为启用数量和“更多来源将逐步接入”。
- Hero 增加极淡网格、封面角标和细腻渐变层次，保留原有标题、`TOKYO` 背景字与城市线稿。
- Hero 下方新增静态 `This week's mood` 关键词栏，导语缩短为编辑式一句话。
- Hero 装饰图改为右下角局部 `contain` 图片层，避免横幅比例下被 `cover` 严重裁切，并保持标题与 `TOKYO` 水印清晰。
- 已在收集流程中启用 5 个来源条目：GO TOKYO、Tokyo Metropolitan Art Museum、Mori Art Museum、Mori Arts Center Gallery、Tokyo City View。
- 已使用 `sources.json` 集中管理来源的 id、名称、类别、启用状态、类型和 URL。
- collector 已改为读取来源配置，并通过 `fetchers/registry.py` 按类型调用 fetcher。
- Mori Art Museum、Mori Arts Center Gallery、Tokyo City View 可在配置中分别启停。
- 未实现的来源类型会被跳过，并在终端打印原因，不会中断其他来源。
- 统一的 `Event` 数据模型。
- 日期过滤、类别过滤、简单去重和排序。
- 基于规则的区域推断、标签、简介和推荐理由补充。
- 简报板块编排：今晚、展览、电影、讲座、周末散步、编辑推荐。
- 页面下载和本地保存 CSV、Markdown、ICS。
- 单个来源失败后继续处理其他来源。
- 终端错误输出和 `logs/app.log` 日志。
- `output/` 中存在 2026-05-11 生成的三组历史导出文件。
- 已新增 `tests/test_smoke.py`，覆盖来源配置、registry、`Event.to_dict()`、日期范围、editor 和 recommender 基础契约。
- 已将 `pytest` 加入 `requirements.txt`，当前锁定版本为 `pytest==9.0.3`。
- 2026-06-13 在线复核 5 个 enabled source：返回数量依次为 1、2、1、1、1；collector 合并为 6 条且错误列表为空。
- Tokyo City View 已从结束的 `Orb` 活动更新为 2026-06-19 至 2026-07-21 的 `Escape from the Observation Deck in Peril`。
- GO TOKYO 已修复 Windows GBK 终端打印日文标题时可能中断解析的问题。
- 已增加发布用 `.gitignore`，排除虚拟环境、缓存、日志、自动导出、环境变量和常见密钥文件。

## 未完成内容

- 电影、讲座、书店、舞台、流行文化 fetcher 目前只保留接口并返回空列表。
- `exhibitions.py` 和 `local_events.py` 存在解析实现，但当前收集器未调用；其稳定性未在本次状态扫描中验证。
- 新的页面解析类型仍需要实现对应 fetcher，并在注册表中登记一次；相同类型的来源只需增加配置。
- 数据源覆盖较少，板块可能为空或内容偏向展览。
- 抓取逻辑依赖外部网页结构，站点变化后可能失效。
- 当前只有最小 smoke tests，没有 fetcher HTML 固定样本测试或 CI。
- 没有数据库、缓存、定时任务、部署配置或历史数据管理。
- 项目目录当前不是 Git 仓库。

## 当前目录结构简述

```text
app.py                 Streamlit 页面和主流程
config.py              类别、板块、路径、网络等配置
models.py              Event 数据模型
sources.json            数据源清单、启用状态、类型和入口 URL
fetchers/registry.py    来源类型与 fetcher 的注册映射、配置读取校验
fetchers/              各来源类型的解析实现和类别占位抓取器
services/              收集、编辑增强、推荐分板块
utils/                 日期、文本、日志、导出工具
output/                CSV、Markdown、ICS 历史输出
logs/app.log           运行日志
requirements*.txt      直接依赖和锁定依赖
README.md              使用说明
```

## 当前运行命令

Windows PowerShell，在项目根目录执行：

```powershell
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

若不激活虚拟环境，可直接执行：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

默认访问地址为 `http://localhost:8501`。

## 当前已知问题

- 实际启用来源以 5 个配置条目、3 种 fetcher 类型组织，类别筛选项仍多于当前可稳定产出的类别。
- Mori 类型仍使用已知活动标题和日期配置，不是通用页面解析器。
- 多个类别 fetcher 是占位实现，电影和讲座等板块通常没有数据。
- 外部网页抓取缺少固定 HTML 样本回归测试，页面结构变化仍需人工在线复核。
- Mori 类型仍依赖已知活动标题和日期配置，活动换期时需要维护 `KNOWN_MORI_EVENTS`。
- 当前 UI 仍使用纯 Streamlit 与 CSS；不同 Streamlit 版本升级后，部分基于 `data-testid` 的样式选择器可能需要微调。
- Streamlit 运行时 DOM 仍可能随版本升级变化；升级后需复核 selectbox、checkbox 和侧栏卡片的样式选择器。

## 下一步建议

1. 为三个真实 fetcher 增加少量固定 HTML 样本回归测试。
2. 在 Mori 活动换期时更新已知活动配置，并重新运行在线复核。
3. 后续为常见 JSON-LD 活动页面提取一个可复用类型。
