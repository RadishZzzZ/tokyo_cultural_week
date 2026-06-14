# Tokyo Cultural Week｜东京未来一周文化生活简报

Tokyo Cultural Week 是一个本地运行的 Python + Streamlit App。它从少量公开文化来源整理东京近期活动，经过去重、日期和类别过滤、编辑增强与板块编排后，生成一份浅色卡片式文化生活简报。

当前发布版本为 **v1.0.0**。

## 当前功能

- 选择未来 1、3、5、7、10 或 14 天。
- 按电影、展览、讲座、书店活动、地区活动、舞台、流行文化等类别筛选。
- 从启用的公开来源抓取真实活动。
- 自动补充区域、标签、简介和推荐理由。
- 按本周精选、今晚、展览、电影、讲座和周末散步分板块展示。
- 通过浏览器下载 CSV、Markdown 和 ICS，不自动写入项目目录。
- 单个来源失败时继续处理其他来源。
- 终端打印完整错误，错误日志写入 `logs/app.log`。

## 当前来源

`sources.json` 是来源清单。当前启用 6 个来源条目：

| ID | 来源 | 类型 | 类别 |
| --- | --- | --- | --- |
| `go_tokyo` | GO TOKYO Official Calendar | `go_tokyo_calendar` | 多类别 |
| `tobikan` | Tokyo Metropolitan Art Museum | `tobikan_exhibitions` | 展览 |
| `mori_art_museum` | Mori Art Museum | `mori_known_events` | 展览 |
| `mori_arts_center_gallery` | Mori Arts Center Gallery | `mori_known_events` | 展览 |
| `tokyo_city_view` | Tokyo City View | `mori_known_events` | 流行文化 |
| `aoyama_book_center` | Aoyama Book Center 活动与讲座 | `aoyama_bookstore_events` | 书店活动 |

这些条目对应 4 种已实现 fetcher 类型。来源是否启用以 `sources.json` 的 `enabled` 字段为准。

### 最近在线复核

2026-06-13 使用 14 天范围逐项调用 enabled source：

| 来源 | 返回数量 | 示例 |
| --- | ---: | --- |
| GO TOKYO | 1 | Asakusa Geisha's Ozashiki Odori |
| Tokyo Metropolitan Art Museum | 2 | Andrew Wyeth、Group Show of Contemporary Artists |
| Mori Art Museum | 1 | Ron Mueck |
| Mori Arts Center Gallery | 1 | SANRIO EXHIBITION FINAL |
| Tokyo City View | 1 | Escape from the Observation Deck in Peril |

collector 合并后共 6 条，错误列表为空。在线结果会随日期和外部页面变化，不能作为永久保证。

2026-06-14 在线复核 Aoyama Book Center：集合页发现 14 个带明确月日的活动链接，详情页均可读取完整日期、时间和会场；7 天范围返回 4 条，collector 来源状态为 `success`。

## 项目结构

```text
tokyo_cultural_week/
  app.py                    Streamlit 页面和主流程
  config.py                 类别、板块、路径和网络配置
  models.py                 Event 数据模型
  sources.json              数据源配置
  asset/
    hero_bg.png             Hero 装饰图
  fetchers/
    registry.py             source type 与 fetcher 注册表
    go_tokyo.py             GO TOKYO 日历解析
    tobikan.py              東京都美術館解析
    mori.py                 Mori 系列页面解析
    bookstore_events.py     Aoyama Book Center 活动与讲座解析
    *.py                    其他类别占位或未启用解析器
  services/
    collector.py            配置读取、调用、过滤、去重和排序
    editor.py               区域、标签和推荐文案增强
    recommender.py          简报板块编排
  utils/
    date_utils.py           东京时区和日期范围处理
    logging_utils.py        日志
    output_utils.py         CSV、Markdown、ICS 输出
    text_utils.py           文本清理
  tests/
    test_aoyama_bookstore.py Aoyama Book Center 离线解析测试
    test_smoke.py           MVP 最小 smoke tests
  output/                   生成文件
  logs/app.log              运行日志
  requirements.txt          直接依赖
  requirements.lock.txt     当前环境锁定依赖
```

## 安装与运行

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

也可以不激活虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

默认访问地址：

```text
http://localhost:8501
```

## 输出文件

生成简报后，页面底部提供浏览器下载按钮：

- `tokyo_cultural_week.csv`
- `tokyo_cultural_week.md`
- `tokyo_cultural_week.ics`

下载不会自动写入项目 `output/` 文件夹。`utils/output_utils.py` 中的本地保存函数仅保留给未来开发或调试使用，当前主 UI 不调用。

## 运行 smoke tests

```powershell
python -m pytest -q
```

Smoke tests 只覆盖 MVP 的基础契约：

- `sources.json` 可以读取。
- enabled source 都有 registry 映射。
- `Event.to_dict()` 正常。
- 基本日期范围判断正常。
- editor 和 recommender 可以处理 mock Event。
- collector 始终返回活动、错误和来源状态三项。
- Aoyama Book Center 集合页链接与详情页日期可以解析。

不包含在线抓取测试，避免外部网站波动导致本地测试不稳定。

## 如何新增来源

### 复用已有类型

如果新网站与现有解析器结构一致，通常只需在 `sources.json` 增加一项：

```json
{
  "id": "source_id",
  "name": "Source Name",
  "category": "exhibitions",
  "enabled": true,
  "type": "tobikan_exhibitions",
  "url": "https://example.com/events"
}
```

支持字段：

- `id`：唯一标识。
- `name`：页面和日志使用的来源名称。
- `category`：主要活动类别。
- `enabled`：是否调用。
- `type`：registry 中的 fetcher 类型。
- `url`：来源入口页面。

### 新增解析类型

页面结构不兼容现有类型时：

1. 在 `fetchers/` 中实现一个接收 `source` 和 `days_ahead` 的函数。
2. 返回 `list[Event]`。
3. 在 `fetchers/registry.py` 的 `FETCHER_REGISTRY` 注册新 `type`。
4. 在 `sources.json` 添加来源条目。

不要在 `app.py` 或 `services/collector.py` 中硬编码网站。

未注册的 `type` 会被 collector 跳过，并在终端打印说明。

## 日志与排错

- 完整错误和 traceback：终端。
- 应用日志：`logs/app.log`。
- 单个来源失败不会阻止其他来源继续运行。
- 抓到 0 条时，先扩大时间范围，再查看终端中各来源的返回数量。

外部页面结构可能变化。在线页面可访问不等于解析器一定能产出活动，因此来源维护应同时核对页面结构、日期和实际返回数量。
