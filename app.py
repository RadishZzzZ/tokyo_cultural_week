"""
app.py

这是 Streamlit App 的主入口。
运行命令：

streamlit run app.py

它负责：
1. 显示页面标题和说明
2. 显示侧边栏设置
3. 点击按钮后收集活动
4. 调用编辑层增强活动
5. 调用推荐层分板块
6. 用卡片方式显示文化简报
7. 提供 CSV / Markdown / ICS 下载
8. 错误时终端打印完整 traceback，页面显示简洁错误

本版本重点：
- 暖白色、浅色卡片和杂志式留白
- Hero 标题区域加入编辑刊物标识和极淡东京城市线稿
- 活动卡片只保留阅读决策需要的核心信息
- 侧边栏控件和页面提示统一为浅色 editorial 风格
"""

import base64
import html
import traceback
from pathlib import Path

import streamlit as st

from config import (
    DEFAULT_DAYS_AHEAD,
    CATEGORY_LABELS,
    SECTIONS,
)
from services.collector import collect_events
from services.editor import enrich_events
from services.recommender import build_sections
from fetchers.registry import load_sources
from utils.logging_utils import setup_logger, log_exception
from utils.output_utils import (
    events_to_csv_text,
    sections_to_markdown,
    events_to_ics_text,
)


logger = setup_logger()
BASE_DIR = Path(__file__).resolve().parent
HERO_BG_PATHS = [
    BASE_DIR / "assets" / "hero_bg.png",
    BASE_DIR / "asset" / "hero_bg.png",
]

SECTION_DISPLAY_ORDER = [
    "editors_pick",
    "tonight",
    "exhibitions",
    "films",
    "lectures",
    "weekend_walk",
]

SECTION_DISPLAY_TITLES = {
    "editors_pick": "⭐ 本周精选",
    "tonight": "🌙 今晚 / 下班后可以去",
    "exhibitions": "🖼 本周展览",
    "films": "🎬 本周电影",
    "lectures": "📚 Talk / Lecture",
    "weekend_walk": "🚶 周末散步顺路活动",
}

SIDEBAR_CATEGORY_LABELS = {
    **CATEGORY_LABELS,
    "local_events": "🏮 地区活动",
}


def format_date_range(event) -> str:
    """
    作用：
    把活动日期格式化成页面上容易看的文字。

    输入：
    event: Event 对象。

    输出：
    日期文字。
    """
    if not event.start_date:
        return "日期不明"

    if event.end_date and event.end_date != event.start_date:
        return f"{event.start_date} ～ {event.end_date}"

    return event.start_date


def safe_text(value: str) -> str:
    """
    作用：
    对要放进 HTML 的文字做转义，避免特殊字符破坏页面。

    输入：
    value: 原始文字。

    输出：
    HTML 安全文字。
    """
    if value is None:
        return ""
    return html.escape(str(value))


def inject_css() -> None:
    """
    作用：
    注入页面 CSS。

    输入：
    无。

    输出：
    无。
    """
    st.markdown(
        """
        <style>
        :root {
            --tcw-paper: #f7f3eb;
            --tcw-card: #fffdf8;
            --tcw-ink: #25231f;
            --tcw-muted: #716c63;
            --tcw-line: #e7dfd1;
            --tcw-accent: #ad4b3b;
            --tcw-accent-dark: #87382d;
            --tcw-sage: #6f8069;
            --tcw-blue: #667d86;
            --tcw-focus: rgba(173, 75, 59, 0.18);
        }

        .stApp {
            background:
                radial-gradient(circle at 85% 0%, rgba(220, 183, 134, 0.16), transparent 30rem),
                linear-gradient(180deg, #fbf8f2 0%, var(--tcw-paper) 100%);
            color: var(--tcw-ink);
        }

        [data-testid="stHeader"] {
            background: rgba(251, 248, 242, 0.88);
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            color: #776f64;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, #f4f0e8 0%, #eee9df 100%);
            border-right: 1px solid var(--tcw-line);
        }

        [data-testid="stSidebar"] * {
            color: #4f4a43;
        }

        [data-testid="stSidebarContent"] {
            padding-top: 1.4rem;
        }

        [data-testid="stSidebar"] h2 {
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 1.08rem !important;
            font-weight: 650 !important;
        }

        [data-testid="stSidebar"] hr {
            border-color: #ddd5c8;
        }

        .tcw-sidebar-brand {
            padding: 0 0 22px;
            margin-bottom: 18px;
            border-bottom: 1px solid #ddd5c8;
        }

        .tcw-sidebar-monogram {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            margin-bottom: 11px;
            border: 1px solid #cbbbaa;
            border-radius: 50%;
            color: var(--tcw-accent);
            font-family: Georgia, serif;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: -0.04em;
            background: rgba(255, 253, 248, 0.72);
        }

        .tcw-sidebar-name {
            color: #38332d;
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 1.05rem;
            font-weight: 650;
            line-height: 1.3;
        }

        .tcw-sidebar-caption {
            margin-top: 5px;
            color: #8a8176;
            font-size: 0.76rem;
            letter-spacing: 0.05em;
        }

        /* Streamlit form controls: keep the sidebar light and editorial. */
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="base-input"],
        [data-testid="stSidebar"] input {
            border-color: #d8ccbd !important;
            background: #fffdf8 !important;
            color: #413b34 !important;
            box-shadow: none !important;
        }

        [data-testid="stSidebar"] [data-baseweb="input"]:focus-within,
        [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within,
        [data-testid="stSidebar"] [data-baseweb="base-input"]:focus-within {
            border-color: #b98273 !important;
            box-shadow: 0 0 0 3px var(--tcw-focus) !important;
        }

        [data-testid="stSidebar"] [role="combobox"] {
            background: transparent !important;
            color: #413b34 !important;
        }

        [data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
            border-radius: 12px !important;
            background: #fffdf8 !important;
        }

        [data-testid="stSidebar"] [data-testid="stCheckbox"] label {
            color: #554e46 !important;
        }

        [data-testid="stSidebar"] [data-testid="stCheckbox"] span[data-checked="true"] {
            border-color: var(--tcw-accent) !important;
            background: var(--tcw-accent) !important;
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 16px 16px 14px;
            border: 1px solid #ddd1c2 !important;
            border-radius: 15px !important;
            background: rgba(255, 253, 248, 0.8) !important;
            box-shadow: 0 5px 16px rgba(86, 66, 42, 0.035);
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]
        [data-testid="stCheckbox"] {
            margin-bottom: 0.16rem;
            min-height: 2rem;
        }

        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]
        [data-testid="stCheckbox"] label {
            align-items: center;
            gap: 0.55rem;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .sidebar-section-label {
            margin-bottom: 10px;
            color: #3e3831;
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 0.98rem;
            font-weight: 650;
        }

        .sidebar-section-note {
            margin: -3px 0 10px;
            color: #8a8176;
            font-size: 0.77rem;
            line-height: 1.55;
        }

        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {
            border-color: #ded3c5 !important;
            background: #fffdf8 !important;
            color: #413b34 !important;
        }

        [role="option"] {
            background: #fffdf8 !important;
            color: #413b34 !important;
        }

        [role="option"]:hover,
        [aria-selected="true"][role="option"] {
            background: #f3e9dd !important;
            color: #6f3e34 !important;
        }

        .block-container {
            max-width: 920px;
            padding-top: 2.1rem;
            padding-bottom: 5rem;
            padding-left: 2.4rem;
            padding-right: 2.4rem;
        }

        h1 {
            color: var(--tcw-ink) !important;
        }

        h2 {
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 1.55rem !important;
            font-weight: 650 !important;
            line-height: 1.4 !important;
            color: #332f29 !important;
            margin-top: 2.8rem !important;
            margin-bottom: 1rem !important;
            letter-spacing: -0.01em;
        }

        h3 {
            font-size: 1.25rem !important;
        }

        p, li, div {
            font-size: 1.0rem;
        }

        .tcw-hero {
            position: relative;
            overflow: hidden;
            isolation: isolate;
            padding: 48px 50px 44px;
            margin: 8px 0 28px;
            border: 1px solid #eadfce;
            border-radius: 30px;
            background:
                linear-gradient(rgba(118, 94, 70, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(118, 94, 70, 0.035) 1px, transparent 1px),
                radial-gradient(circle at 86% 18%, rgba(177, 111, 86, 0.13), transparent 17rem),
                linear-gradient(120deg, rgba(255, 253, 248, 0.99), rgba(244, 230, 209, 0.94));
            background-size: 42px 42px, 42px 42px, auto, auto;
            box-shadow: 0 18px 50px rgba(90, 70, 45, 0.09);
        }

        .tcw-hero-art {
            position: absolute;
            right: -2%;
            bottom: -28%;
            width: 68%;
            height: auto;
            max-height: 145%;
            object-fit: contain;
            object-position: right bottom;
            opacity: 0.28;
            filter: sepia(0.18) saturate(0.72) contrast(0.82) brightness(1.08);
            mix-blend-mode: multiply;
            pointer-events: none;
            z-index: 0;
        }

        .tcw-hero-content {
            position: relative;
            z-index: 3;
        }

        .tcw-hero::after {
            content: "TOKYO";
            position: absolute;
            right: -12px;
            bottom: -24px;
            color: rgba(185, 79, 61, 0.065);
            font-family: Georgia, serif;
            font-size: 6.8rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            z-index: 1;
        }

        .tcw-hero::before {
            content: "";
            position: absolute;
            top: -75px;
            right: 105px;
            width: 190px;
            height: 190px;
            border: 1px solid rgba(137, 92, 69, 0.1);
            border-radius: 50%;
            z-index: 1;
        }

        .tcw-hero-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            margin-bottom: 24px;
        }

        .tcw-kicker {
            color: var(--tcw-accent);
            font-size: 0.78rem;
            font-weight: 750;
            letter-spacing: 0.18em;
            text-transform: uppercase;
        }

        .tcw-issue {
            color: #8c796b;
            font-family: Georgia, serif;
            font-size: 0.73rem;
            letter-spacing: 0.12em;
            white-space: nowrap;
        }

        .tcw-title {
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: clamp(2.35rem, 6vw, 4.15rem);
            font-weight: 650;
            line-height: 1.02;
            letter-spacing: -0.045em;
            margin-bottom: 16px;
            background: linear-gradient(100deg, #2d2923 10%, #6d4137 58%, #9d5b49 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .tcw-subtitle {
            color: #4c463d;
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 1.35rem;
            line-height: 1.5;
            margin-bottom: 16px;
        }

        .tcw-deck {
            max-width: 610px;
            color: var(--tcw-muted);
            font-size: 1.02rem;
            line-height: 1.85;
        }

        .tcw-cityline {
            position: absolute;
            right: 24px;
            bottom: 18px;
            width: 310px;
            height: 86px;
            color: rgba(104, 88, 72, 0.13);
            z-index: 2;
        }

        .tcw-cityline path,
        .tcw-cityline line,
        .tcw-cityline polyline {
            fill: none;
            stroke: currentColor;
            stroke-width: 1.2;
            vector-effect: non-scaling-stroke;
        }

        .tcw-cover-mark {
            position: absolute;
            top: 22px;
            right: 24px;
            width: 7px;
            height: 7px;
            border: 1px solid rgba(145, 76, 58, 0.32);
            transform: rotate(45deg);
            z-index: 3;
        }

        .weekly-mood {
            display: flex;
            align-items: baseline;
            gap: 18px;
            padding: 2px 4px 16px;
            margin: -8px 0 4px;
            border-bottom: 1px solid #e5dccf;
        }

        .weekly-mood-label {
            flex: 0 0 auto;
            color: var(--tcw-accent);
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.13em;
            text-transform: uppercase;
        }

        .weekly-mood-words {
            color: #71695f;
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 0.94rem;
            line-height: 1.75;
            letter-spacing: 0.015em;
        }

        .newsletter-note {
            padding: 14px 4px 15px 18px;
            border-left: 2px solid #c9b39e;
            color: #696258;
            margin: 10px 0 24px;
            line-height: 1.75;
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 0.94rem;
        }

        .event-card {
            position: relative;
            border: 1px solid var(--tcw-line);
            border-radius: 22px;
            padding: 25px 28px 24px;
            margin: 14px 0 20px;
            background: rgba(255, 253, 248, 0.96);
            box-shadow: 0 10px 28px rgba(86, 66, 42, 0.07);
        }

        .event-title {
            font-family: Georgia, "Noto Serif SC", serif;
            font-size: 1.28rem;
            font-weight: 650;
            margin-bottom: 13px;
            color: #2d2923;
            line-height: 1.5;
        }

        .event-category {
            display: inline-block;
            margin-bottom: 11px;
            color: var(--tcw-accent);
            font-size: 0.77rem;
            font-weight: 750;
            letter-spacing: 0.06em;
        }

        .event-meta {
            color: #746d63;
            font-size: 0.93rem;
            margin-bottom: 7px;
            line-height: 1.65;
        }

        .event-reason {
            margin-top: 17px;
            padding-top: 16px;
            border-top: 1px solid #eee6da;
            line-height: 1.8;
            color: #464038;
            font-size: 1rem;
        }

        .label {
            color: var(--tcw-sage);
            font-weight: 750;
        }

        .event-tags {
            margin-top: 15px;
            color: #766c5f;
            font-size: 0.88rem;
            line-height: 1.75;
        }

        .event-source {
            margin-top: 12px;
            font-size: 0.88rem;
            color: #8a8175;
        }

        .event-source a {
            color: var(--tcw-accent-dark) !important;
            text-decoration: none;
            font-weight: 700;
        }

        .event-source a:hover {
            text-decoration: underline;
        }

        .empty-section {
            border: 1px dashed #d9cebf;
            border-radius: 16px;
            padding: 17px 20px;
            margin: 10px 0 25px;
            color: #8a8175;
            background: rgba(255, 253, 248, 0.5);
            font-size: 0.93rem;
            line-height: 1.7;
        }

        .sidebar-note {
            color: #766f65;
            font-size: 0.86rem;
            line-height: 1.55;
        }

        .source-status {
            color: #526568;
            font-size: 0.84rem;
            line-height: 1.7;
        }

        .source-status strong {
            color: #3f5559;
            font-weight: 700;
        }

        .editorial-notice {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 15px 17px;
            margin: 12px 0 16px;
            border: 1px solid;
            border-radius: 16px;
            box-shadow: 0 5px 16px rgba(86, 66, 42, 0.035);
            color: #4f4a43;
            line-height: 1.65;
        }

        .editorial-notice-mark {
            flex: 0 0 auto;
            width: 8px;
            height: 8px;
            margin-top: 8px;
            border-radius: 50%;
            background: currentColor;
            opacity: 0.65;
        }

        .editorial-notice-info {
            border-color: #d8e0df;
            background: #f0f4f3;
            color: #566a6d;
        }

        .editorial-notice-success {
            border-color: #d7e2d3;
            background: #f1f6ef;
            color: #5b7057;
        }

        .editorial-notice-warning {
            border-color: #ead9bd;
            background: #faf2e5;
            color: #806646;
        }

        .editorial-notice-error {
            border-color: #e8cbc5;
            background: #faefec;
            color: #8a4c42;
        }

        div.stButton > button[kind="primary"] {
            min-height: 3.25rem;
            padding: 0.75rem 1.65rem;
            border: 1px solid var(--tcw-accent);
            border-radius: 999px;
            background: linear-gradient(110deg, #a94637, #bd6650);
            box-shadow: 0 9px 24px rgba(173, 75, 59, 0.2);
            color: white;
            font-size: 1rem;
            font-weight: 720;
        }

        div.stButton > button[kind="primary"]:hover {
            border-color: var(--tcw-accent-dark);
            background: var(--tcw-accent-dark);
            color: white;
        }

        div.stDownloadButton > button {
            border: 1px solid #d8cbbb;
            border-radius: 999px;
            background: #fffdf8;
            color: #514a41;
        }

        div.stDownloadButton > button:hover {
            border-color: var(--tcw-accent);
            color: var(--tcw-accent-dark);
        }

        [data-testid="stAlert"] {
            border: 1px solid #e4d8c9 !important;
            border-radius: 16px;
            background: #f8f2e9 !important;
            color: #5d554b !important;
            box-shadow: none !important;
        }

        [data-testid="stExpander"] {
            border-color: #ded5c8;
            border-radius: 16px;
            background: rgba(255, 253, 248, 0.58);
        }

        .maintenance-table-wrap {
            width: 100%;
            overflow-x: auto;
            margin-top: 0.65rem;
            border: 1px solid #ddd3c6;
            border-radius: 14px;
            background: #fffdf8;
        }

        .maintenance-table {
            width: 100%;
            min-width: 760px;
            border-collapse: collapse;
            color: #514a41;
            font-size: 0.84rem;
            line-height: 1.5;
        }

        .maintenance-table th {
            padding: 0.75rem 0.85rem;
            border-bottom: 1px solid #d8cbbb;
            background: #f2ece2;
            color: #63594d;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-align: left;
            white-space: nowrap;
        }

        .maintenance-table td {
            max-width: 320px;
            padding: 0.72rem 0.85rem;
            border-bottom: 1px solid #ebe3d8;
            background: #fffdf8;
            color: #514a41;
            text-align: left;
            vertical-align: top;
            overflow-wrap: anywhere;
        }

        .maintenance-table tbody tr:nth-child(even) td {
            background: #fbf7f0;
        }

        .maintenance-table tbody tr:last-child td {
            border-bottom: 0;
        }

        .maintenance-table-empty {
            padding: 1rem;
            color: #81776b;
            font-size: 0.86rem;
        }

        @media (max-width: 700px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .tcw-hero {
                padding: 34px 26px 32px;
                border-radius: 24px;
            }

            .tcw-hero::after {
                font-size: 4.5rem;
            }

            .tcw-hero-topline {
                align-items: flex-start;
                flex-direction: column;
                gap: 6px;
            }

            .tcw-cityline {
                right: -45px;
                width: 250px;
                opacity: 0.72;
            }

            .tcw-hero-art {
                right: -20%;
                bottom: -12%;
                width: 92%;
                max-height: 120%;
                object-position: right bottom;
                opacity: 0.2;
            }

            .weekly-mood {
                align-items: flex-start;
                flex-direction: column;
                gap: 4px;
            }

            .event-card {
                padding: 22px 20px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    """
    作用：
    显示杂志式 Hero 标题区域。
    """
    try:
        hero_bg_path = next(path for path in HERO_BG_PATHS if path.exists())
        image_data = base64.b64encode(hero_bg_path.read_bytes()).decode("ascii")
        hero_art = (
            f'<img class="tcw-hero-art" '
            f'src="data:image/png;base64,{image_data}" alt="" aria-hidden="true">'
        )
    except Exception:
        print(f"[ui] Hero 背景图读取失败，已检查：{HERO_BG_PATHS}")
        traceback.print_exc()
        hero_art = ""

    st.html(
        f"""
        <section class="tcw-hero">
            {hero_art}
            <div class="tcw-hero-content">
                <div class="tcw-hero-topline">
                    <div class="tcw-kicker">A weekly cultural note from Tokyo</div>
                    <div class="tcw-issue">WEEKLY EDITION · TOKYO</div>
                </div>
                <div class="tcw-title">Tokyo Cultural Week</div>
                <div class="tcw-subtitle">东京未来一周文化生活简报</div>
                <div class="tcw-deck">
                    这一周值得出门的展览、电影、讲座与城市活动。
                    给周末看展、下班散步和临时起意留一点空间。
                </div>
            </div>
            <span class="tcw-cover-mark"></span>
            <svg class="tcw-cityline" viewBox="0 0 320 90" aria-hidden="true">
                <path d="M2 78 H318"/>
                <path d="M16 78 V57 H43 V78 M28 57 V45 H35 V57"/>
                <path d="M55 78 V49 H83 V78 M61 57 H77 M61 65 H77"/>
                <path d="M94 78 V61 H115 V78"/>
                <path d="M126 78 V43 H154 V78 M132 51 H148 M132 60 H148"/>
                <path d="M164 78 V55 H187 V78"/>
                <path d="M202 78 V37 H229 V78 M208 46 H223 M208 55 H223"/>
                <path d="M244 78 V58 H266 V78"/>
                <path d="M278 78 V49 H304 V78 M284 58 H298"/>
                <path d="M235 78 L246 27 L257 78 M241 49 H251 M244 38 H249"/>
                <path d="M247 27 L247 14"/>
                <path d="M9 70 C78 65, 141 73, 196 67 S279 63, 313 69"/>
            </svg>
        </section>
        """
    )


def render_weekly_mood() -> None:
    """
    作用：
    在 Hero 下方显示本周文化生活关键词。
    """
    st.html(
        """
        <div class="weekly-mood">
            <div class="weekly-mood-label">This week's mood</div>
            <div class="weekly-mood-words">
                展览 · 城市散步 · Talk Event · 安静周末
            </div>
        </div>
        """
    )


def render_editorial_notice(message: str, tone: str = "info") -> None:
    """
    作用：
    用柔和编辑注释卡替代系统感较强的提示框。
    """
    safe_message = safe_text(message)
    safe_tone = tone if tone in {"info", "success", "warning", "error"} else "info"
    st.html(
        f"""
        <div class="editorial-notice editorial-notice-{safe_tone}">
            <span class="editorial-notice-mark"></span>
            <div>{safe_message}</div>
        </div>
        """
    )


def render_intro_note() -> None:
    """
    作用：
    显示简报说明。

    输入：
    无。

    输出：
    无。
    """
    st.html(
        """
        <div class="newsletter-note">
        给这一周留一点看展、散步和临时出门的空间。
        </div>
        """
    )


def render_event_card(event) -> None:
    """
    作用：
    在 Streamlit 页面上显示单张活动卡片。

    输入：
    event: Event 对象。

    输出：
    无。直接在页面渲染。
    """
    category_label = CATEGORY_LABELS.get(event.category, event.category)
    tags_text = " / ".join(event.tags) if event.tags else "暂无标签"
    date_text = format_date_range(event)
    location_text = event.location or "未注明"
    area_text = event.area or "区域不明"

    title = safe_text(event.title)
    category_label = safe_text(category_label)
    date_text = safe_text(date_text)
    location_text = safe_text(location_text)
    area_text = safe_text(area_text)
    recommendation_reason = safe_text(
        event.recommendation_reason or event.description or "本周可以留意的东京文化活动。"
    )
    tags_text = safe_text(tags_text)
    source_name = safe_text(event.source_name or "来源链接")
    source_url = html.escape(event.source_url or "", quote=True)

    if source_url:
        source_html = f'<a href="{source_url}" target="_blank">{source_name}</a>'
    else:
        source_html = source_name

    st.html(
        f"""
        <div class="event-card">
            <div class="event-category">{category_label}</div>
            <div class="event-title">{title}</div>
            <div class="event-meta">日期 · {date_text}</div>
            <div class="event-meta">地点 · {location_text} · {area_text}</div>
            <div class="event-reason"><span class="label">本周推荐：</span>{recommendation_reason}</div>
            <div class="event-tags">{tags_text}</div>
            <div class="event-source">查看来源 · {source_html}</div>
        </div>
        """
    )


def render_empty_section_message() -> None:
    """
    作用：
    显示空板块提示。

    输入：
    无。

    输出：
    无。
    """
    st.html(
        """
        <div class="empty-section">
            本期暂时没有选出合适内容。等接入更多来源后，这里会出现更多电影、讲座、书店活动和小型现场。
        </div>
        """
    )


def render_sections(sections) -> None:
    """
    作用：
    按板块显示所有活动卡片。

    输入：
    sections: recommender.py 返回的分板块 dict。

    输出：
    无。直接在页面渲染。
    """
    for section_key in SECTION_DISPLAY_ORDER:
        section_title = SECTION_DISPLAY_TITLES.get(
            section_key,
            SECTIONS.get(section_key, section_key),
        )
        st.markdown(f"## {section_title}")

        section_events = sections.get(section_key, [])
        if not section_events:
            render_empty_section_message()
            continue

        for event in section_events:
            render_event_card(event)


def build_light_table_html(rows: list[dict], columns: list[str]) -> str:
    """
    把维护信息转换成经过转义的浅色 HTML 表格。
    """
    header_html = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in columns
    )

    if rows:
        body_html = "".join(
            "<tr>"
            + "".join(
                f"<td>{html.escape(str(row.get(column, '') or '—'))}</td>"
                for column in columns
            )
            + "</tr>"
            for row in rows
        )
    else:
        body_html = (
            f'<tr><td class="maintenance-table-empty" colspan="{len(columns)}">'
            "暂无数据"
            "</td></tr>"
        )

    return (
        '<div class="maintenance-table-wrap">'
        '<table class="maintenance-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody>"
        "</table>"
        "</div>"
    )


def render_light_table(rows: list[dict], columns: list[str]) -> None:
    st.html(build_light_table_html(rows, columns))


def render_source_statuses(source_statuses: list[dict]) -> None:
    """
    在结果底部以低干扰折叠区展示本次来源抓取状态。
    """
    if not source_statuses:
        return

    status_labels = {
        "success": "成功",
        "failed": "失败",
        "skipped": "跳过",
    }
    rows = [
        {
            "来源 ID": status["source_id"],
            "来源名称": status["source_name"],
            "类别": status["category"],
            "已启用": "是" if status["enabled"] else "否",
            "状态": status_labels.get(status["status"], status["status"]),
            "返回数量": status["event_count"],
            "最近错误摘要": status["last_error"] or "—",
        }
        for status in source_statuses
    ]

    with st.expander("来源状态"):
        st.caption("显示本次生成时各来源的调用结果；详细错误仍记录在终端和日志中。")
        render_light_table(rows, list(rows[0].keys()))


def render_sidebar_settings() -> dict:
    """
    作用：
    显示侧边栏设置，并返回用户设置。

    输入：
    无。

    输出：
    dict，包含 days_ahead 和 selected_categories。
    """
    st.sidebar.markdown(
        """
        <div class="tcw-sidebar-brand">
            <div class="tcw-sidebar-monogram">TCW</div>
            <div class="tcw-sidebar-name">Tokyo Cultural Week</div>
            <div class="tcw-sidebar-caption">WEEKLY CULTURE FILTER</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.header("筛选本周简报")

    time_options = [1, 3, 5, 7, 10, 14]
    days_ahead = st.sidebar.selectbox(
        "时间范围",
        options=time_options,
        index=time_options.index(DEFAULT_DAYS_AHEAD)
        if DEFAULT_DAYS_AHEAD in time_options
        else 3,
        format_func=lambda value: f"{value}天",
        help="选择这期简报覆盖的日期范围。",
    )

    st.sidebar.markdown(
        '<div class="sidebar-section-label">显示类别</div>'
        '<div class="sidebar-section-note">勾选想放进本期简报的文化活动。</div>',
        unsafe_allow_html=True,
    )

    selected_categories = []
    with st.sidebar.container(border=True):
        for category_key, category_label in SIDEBAR_CATEGORY_LABELS.items():
            if st.checkbox(
                category_label,
                value=True,
                key=f"category_{category_key}",
            ):
                selected_categories.append(category_key)

    try:
        enabled_sources = [
            source for source in load_sources()
            if source.get("enabled") is True
        ]
    except Exception:
        enabled_sources = []

    with st.sidebar.container(border=True):
        st.markdown(
            f"""
            <div class="sidebar-section-label">来源状态</div>
            <div class="source-status">
                <strong>当前启用来源：</strong>{len(enabled_sources)} 个<br>
                更多来源将逐步接入。
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "days_ahead": int(days_ahead),
        "selected_categories": selected_categories,
    }


def main() -> None:
    """
    作用：
    Streamlit 主函数。页面所有逻辑从这里开始。

    输入：
    无。

    输出：
    无。直接渲染网页。
    """
    try:
        st.set_page_config(
            page_title="Tokyo Cultural Week",
            page_icon="🗞️",
            layout="wide",
        )

        inject_css()

        settings = render_sidebar_settings()

        render_hero()
        render_weekly_mood()
        render_intro_note()

        has_selected_categories = bool(settings["selected_categories"])
        if not has_selected_categories:
            render_editorial_notice("请至少选择一个类别。", "warning")

        if st.button(
            "生成本周文化简报",
            type="primary",
            disabled=not has_selected_categories,
        ):
            with st.spinner("正在整理这一期 Tokyo Cultural Week..."):
                try:
                    logger.info("开始生成文化简报。")

                    events, fetch_errors, source_statuses = collect_events(
                        days_ahead=settings["days_ahead"],
                        selected_categories=settings["selected_categories"],
                    )

                    if fetch_errors:
                        for message in fetch_errors:
                            render_editorial_notice(message, "warning")

                    enriched_events = enrich_events(events)
                    sections = build_sections(enriched_events)

                    if not enriched_events:
                        render_editorial_notice(
                            "这一期暂时没有抓到符合日期范围的真实活动。可以扩大未来天数，或继续增加数据源。",
                            "warning",
                        )
                    else:
                        render_editorial_notice(
                            f"本期共整理 {len(enriched_events)} 条真实活动。",
                            "success",
                        )

                        if len(enriched_events) < 8:
                            render_editorial_notice(
                                "这一期内容还偏轻。当前来源主要集中在官方活动日历和美术馆，后续接入摄影美术馆、书店活动和电影来源后会更丰满。",
                                "info",
                            )

                        render_sections(sections)

                        st.markdown("---")
                        st.subheader("下载")
                        st.caption(
                            "需要时可以下载当前结果。"
                            "下载不会自动写入项目 output 文件夹。"
                        )

                        csv_text = events_to_csv_text(enriched_events)
                        md_text = sections_to_markdown(sections)
                        ics_text = events_to_ics_text(enriched_events)

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.download_button(
                                "下载 CSV",
                                data=csv_text,
                                file_name="tokyo_cultural_week.csv",
                                mime="text/csv",
                            )

                        with col2:
                            st.download_button(
                                "下载 Markdown",
                                data=md_text,
                                file_name="tokyo_cultural_week.md",
                                mime="text/markdown",
                            )

                        with col3:
                            st.download_button(
                                "下载 ICS",
                                data=ics_text,
                                file_name="tokyo_cultural_week.ics",
                                mime="text/calendar",
                            )

                    render_source_statuses(source_statuses)
                    logger.info("文化简报生成完成。")

                except Exception:
                    render_editorial_notice(
                        "生成简报时发生错误。请查看终端完整 traceback，或打开 logs/app.log。",
                        "error",
                    )
                    log_exception(logger, "生成简报时发生错误。")

    except Exception:
        print("Streamlit 页面运行错误。")
        traceback.print_exc()
        logger.exception("Streamlit 页面运行错误。")
        render_editorial_notice(
            "页面运行错误。请查看终端完整 traceback。",
            "error",
        )


if __name__ == "__main__":
    main()
