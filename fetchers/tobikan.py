"""
fetchers/tobikan.py

这个文件负责抓取東京都美術館 Tokyo Metropolitan Art Museum 的展览信息。

本版本修正：
1. 修复日期范围解析错误。
   之前因为正则表达式里有嵌套捕获组，导致 end_date 取错。
2. 避免把 2017～2025 年已经结束的旧展览误判成 2026 年仍在进行。
3. 使用更严格的日期解析规则，不再依赖 dateparser 猜年份。
4. 只保留和未来 days_ahead 天有重叠的展览。
5. 不伪造活动；日期不明确就跳过。
"""

import re
import traceback
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Event
from utils.date_utils import now_tokyo, date_range_overlaps
from utils.text_utils import clean_text, truncate_text


SOURCE_NAME = "Tokyo Metropolitan Art Museum"
BASE_URL = "https://www.tobikan.jp"
EXHIBITION_URL = "https://www.tobikan.jp/en/exhibition/index.html"


MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def make_soup_from_response(response: requests.Response) -> BeautifulSoup:
    """
    作用：
    把 requests 的 response 转成 BeautifulSoup 对象。

    输入：
    response: requests.get() 返回的 Response 对象。

    输出：
    BeautifulSoup 对象。
    """
    return BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")


def make_full_url(url: str, base_url: str = EXHIBITION_URL) -> str:
    """
    作用：
    把相对链接变成完整 URL。

    输入：
    url: 页面里的链接。

    输出：
    完整 URL。
    """
    if not url:
        return base_url

    return urljoin(base_url, url)


def parse_english_date(raw_date: str, fallback_year: Optional[int] = None) -> Optional[str]:
    """
    作用：
    解析英文日期，返回 YYYY-MM-DD。

    输入：
    raw_date:
    例如：
    November 18 (Tue), 2025
    January 8 (Thu), 2026
    January 27 (Tue)

    fallback_year:
    如果 raw_date 自己没有年份，就使用这个年份。

    输出：
    YYYY-MM-DD 或 None。

    为什么不用 dateparser：
    dateparser 在缺少年份时会根据“当前日期”猜年份，
    容易把旧展览误判成未来日期。
    这里手动解析，避免错误。
    """
    try:
        text = clean_text(raw_date)

        # 去掉星期，例如 (Tue)
        text = re.sub(r"\([A-Za-z]+\)", "", text)
        text = text.replace(",", " ")
        text = re.sub(r"\s+", " ", text).strip()

        match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:\s+(\d{4}))?",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        month_name = match.group(1).lower()
        day = int(match.group(2))
        year_text = match.group(3)

        if year_text:
            year = int(year_text)
        elif fallback_year:
            year = fallback_year
        else:
            return None

        month = MONTH_NAME_TO_NUMBER[month_name]
        parsed_date = datetime(year, month, day).date()
        return parsed_date.isoformat()

    except Exception:
        print(f"[tobikan] 单个日期解析失败：{raw_date}")
        traceback.print_exc()
        return None


def parse_date_range(raw_text: str) -> tuple[Optional[str], Optional[str]]:
    """
    作用：
    从一段文字中解析展览日期范围。

    输入：
    raw_text: 包含日期范围的文字。

    输出：
    (start_date, end_date)

    支持例子：
    November 18 (Tue), 2025 – January 8 (Thu), 2026
    January 27 (Tue) – April 12 (Sun), 2026

    重要规则：
    - 如果开始日期没有年份，但结束日期有年份，就用结束日期年份补给开始日期。
    - 如果开始月大于结束月，说明跨年，则开始年份 = 结束年份 - 1。
      例如 November 18 – January 8, 2026
      应该是 2025-11-18 ～ 2026-01-08。
    """
    try:
        text = clean_text(raw_text)

        # 用非捕获组 ?: 避免 group 编号混乱
        date_part_pattern = (
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
            r"\s+\d{1,2}\s*"
            r"(?:\([A-Za-z]+\))?"
            r"\s*,?\s*"
            r"(?:\d{4})?"
        )

        range_match = re.search(
            rf"({date_part_pattern})\s*[–—-]\s*({date_part_pattern})",
            text,
            flags=re.IGNORECASE,
        )

        if not range_match:
            return None, None

        start_raw = clean_text(range_match.group(1))
        end_raw = clean_text(range_match.group(2))

        end_year_match = re.search(r"\d{4}", end_raw)
        start_year_match = re.search(r"\d{4}", start_raw)

        if not end_year_match and not start_year_match:
            return None, None

        end_year = int(end_year_match.group(0)) if end_year_match else None

        if start_year_match:
            start_year = int(start_year_match.group(0))
        else:
            # 开始日期没有年份时，先默认用结束年份
            start_year = end_year

            # 如果开始月份大于结束月份，则说明跨年
            start_month_match = re.search(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)",
                start_raw,
                flags=re.IGNORECASE,
            )
            end_month_match = re.search(
                r"(January|February|March|April|May|June|July|August|September|October|November|December)",
                end_raw,
                flags=re.IGNORECASE,
            )

            if start_month_match and end_month_match and end_year:
                start_month = MONTH_NAME_TO_NUMBER[start_month_match.group(1).lower()]
                end_month = MONTH_NAME_TO_NUMBER[end_month_match.group(1).lower()]

                if start_month > end_month:
                    start_year = end_year - 1

        start_date = parse_english_date(start_raw, fallback_year=start_year)
        end_date = parse_english_date(end_raw, fallback_year=end_year or start_year)

        return start_date, end_date

    except Exception:
        print(f"[tobikan] 日期范围解析失败：{raw_text}")
        traceback.print_exc()
        return None, None


def extract_title_from_block(block_text: str) -> str:
    """
    作用：
    从包含展览信息的一段文字中提取标题。

    输入：
    block_text: 页面中某个链接或区块的文字。

    输出：
    展览标题。
    """
    text = clean_text(block_text)

    remove_words = [
        "Special Exhibitions",
        "Thematic Exhibitions",
        "Ueno Artist Project",
        "Current Exhibitions",
        "Upcoming Exhibitions",
        "Past Exhibitions",
    ]

    for word in remove_words:
        text = text.replace(word, "")

    date_start = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}",
        text,
        flags=re.IGNORECASE,
    )

    if date_start:
        title = text[:date_start.start()]
    else:
        title = text

    title = clean_text(title)

    if len(title) < 5:
        title = truncate_text(text, 80)

    return title


def looks_like_exhibition_block(text: str) -> bool:
    """
    作用：
    判断一个文本块是否像展览信息。

    输入：
    text: 页面文本块。

    输出：
    True / False。
    """
    if len(text) < 30:
        return False

    has_month = any(
        month in text
        for month in [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
    )

    has_range_mark = "–" in text or "-" in text or "—" in text

    return has_month and has_range_mark


def fetch_tobikan_exhibitions(
    days_ahead: int,
    source: Optional[dict] = None,
) -> list[Event]:
    """
    作用：
    抓取東京都美術館展览信息。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。失败时返回空列表。
    """
    events: list[Event] = []
    exhibition_url = str(source.get("url", EXHIBITION_URL)) if source else EXHIBITION_URL
    source_name = str(source.get("name", SOURCE_NAME)) if source else SOURCE_NAME

    try:
        print(f"[fetcher] 开始抓取 {source_name}：{exhibition_url}")

        response = requests.get(
            exhibition_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = make_soup_from_response(response)

        candidate_blocks = []

        # 优先从 a 标签抓。a 标签通常更接近具体展览。
        for a_tag in soup.find_all("a", href=True):
            block_text = clean_text(a_tag.get_text(" ", strip=True))

            if looks_like_exhibition_block(block_text):
                candidate_blocks.append(
                    (block_text, make_full_url(a_tag.get("href", ""), exhibition_url))
                )

        # 如果 a 标签抓得太少，再从 li/article/section 补充，避免漏掉。
        for block in soup.find_all(["article", "section", "li"]):
            block_text = clean_text(block.get_text(" ", strip=True))

            if looks_like_exhibition_block(block_text):
                link = block.find("a", href=True)
                source_url = (
                    make_full_url(link.get("href", ""), exhibition_url)
                    if link
                    else exhibition_url
                )
                candidate_blocks.append((block_text, source_url))

        print(f"[tobikan] 候选区块数量：{len(candidate_blocks)}")

        seen_keys = set()
        dropped_out_of_range = 0
        dropped_no_date = 0

        for block_text, source_url in candidate_blocks[:120]:
            try:
                start_date, end_date = parse_date_range(block_text)

                if not start_date:
                    dropped_no_date += 1
                    continue

                if not date_range_overlaps(start_date, end_date, days_ahead):
                    dropped_out_of_range += 1
                    continue

                title = extract_title_from_block(block_text)

                if not title:
                    continue

                dedup_key = f"{title}|{start_date}|{end_date}"
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                description = truncate_text(block_text, 220)

                event = Event(
                    title=title,
                    category="exhibitions",
                    start_date=start_date,
                    end_date=end_date,
                    time="",
                    location="Tokyo Metropolitan Art Museum, Ueno",
                    area="上野",
                    description=description,
                    recommendation_reason="",
                    tags=[],
                    source_url=source_url,
                    source_name=source_name,
                    fetched_at=now_tokyo().isoformat(timespec="seconds"),
                )

                print(f"[tobikan] 保留展览：{event.title} {event.start_date} - {event.end_date}")
                events.append(event)

            except Exception:
                print("[tobikan] 单个候选区块解析失败。")
                traceback.print_exc()

        print(
            f"[tobikan] 调试信息：无日期丢弃={dropped_no_date}, "
            f"日期范围外丢弃={dropped_out_of_range}, 最终保留={len(events)}"
        )

        print(f"[fetcher] 東京都美術館展览完成，最终保留 {len(events)} 条。")
        return events

    except Exception:
        print("[fetcher] 東京都美術館展览抓取失败。")
        traceback.print_exc()
        return []
