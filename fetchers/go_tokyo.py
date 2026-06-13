"""
fetchers/go_tokyo.py

这个文件负责抓取 GO TOKYO 官方活动日历中的东京活动。

当前版本已经确认可以抓到 GO TOKYO 的真实活动链接，例如：
/en/event/tokyotouristinfo/20260411.html

本版本修正：
1. 使用 response.content 而不是 response.text，避免日文乱码。
2. 用 BeautifulSoup(..., from_encoding="utf-8") 明确指定 UTF-8。
3. 保留 /en/event/ 活动详情页链接规则。
4. 保留日期范围解析，例如 2026.4.11 - 2026.7.11。
5. 保留完整 traceback，方便排查错误。

注意：
这个 fetcher 不伪造活动。
如果一个活动没有明确日期，或者日期解析失败，就不会加入结果。
"""

import re
import sys
import traceback
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Event
from utils.date_utils import now_tokyo, parse_date_to_iso, date_range_overlaps
from utils.text_utils import clean_text, truncate_text


BASE_URL = "https://www.gotokyo.org"
CALENDAR_URL = "https://www.gotokyo.org/en/calendar/index.html"
SOURCE_NAME = "GO TOKYO Official Calendar"


def safe_console_text(value: str) -> str:
    """
    把网页文字转换成当前终端可打印的形式。

    Windows 使用 GBK 终端时，日文字符不应让调试输出中断活动解析。
    """
    text = str(value)
    encoding = sys.stdout.encoding or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def make_soup_from_response(response: requests.Response) -> BeautifulSoup:
    """
    作用：
    把 requests 的 response 转成 BeautifulSoup 对象。

    输入：
    response: requests.get() 返回的 Response 对象。

    输出：
    BeautifulSoup 对象。

    为什么不用 response.text：
    有些网页虽然本身是 UTF-8，但 requests 可能会猜错编码。
    如果直接用 response.text，日文可能会变成 æµ...ã... 这种乱码。
    所以这里使用 response.content，也就是原始 bytes，
    再让 BeautifulSoup 按 utf-8 解析。
    """
    return BeautifulSoup(response.content, "html.parser", from_encoding="utf-8")


def make_full_url(url: str) -> str:
    """
    作用：
    把 GO TOKYO 页面里的相对链接转换成完整链接。

    输入：
    url: 可能是 /en/event/tokyotouristinfo/20260411.html，也可能已经是完整 URL。

    输出：
    完整 URL。
    """
    if not url:
        return ""

    if url.startswith("http"):
        return url

    if url.startswith("/"):
        return BASE_URL + url

    return BASE_URL + "/" + url


def remove_common_site_suffix(title: str) -> str:
    """
    作用：
    清理网页 title 里常见的网站后缀。

    输入：
    title: 原始标题。

    输出：
    清理后的标题。
    """
    title = clean_text(title)

    suffixes = [
        "| The Official Tokyo Travel Guide, GO TOKYO",
        "| GO TOKYO",
        "／東京の観光公式サイトGO TOKYO",
    ]

    for suffix in suffixes:
        title = title.replace(suffix, "")

    return clean_text(title)


def extract_event_links(soup: BeautifulSoup) -> list[str]:
    """
    作用：
    从 GO TOKYO Calendar 页面中提取活动详情页链接。

    输入：
    soup: BeautifulSoup 解析后的 Calendar 页面。

    输出：
    活动详情页 URL 列表。

    说明：
    GO TOKYO 的活动页通常类似：
    /en/event/tokyotouristinfo/20260411.html

    所以这里寻找：
    - 包含 /en/event/
    - 以 .html 结尾
    的链接。
    """
    links: list[str] = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")

        if "/en/event/" not in href:
            continue

        if not href.endswith(".html"):
            continue

        full_url = make_full_url(href)

        if full_url in seen:
            continue

        seen.add(full_url)
        links.append(full_url)

    print(f"[go_tokyo] extract_event_links 找到活动链接：{len(links)}")
    for sample_url in links[:5]:
        print(f"[go_tokyo] 示例活动链接：{sample_url}")

    return links


def extract_title(soup: BeautifulSoup) -> str:
    """
    作用：
    从详情页中提取活动标题。

    输入：
    soup: BeautifulSoup 解析后的活动详情页。

    输出：
    标题文字。
    """
    h1 = soup.find("h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))

    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(" ", strip=True)
        return remove_common_site_suffix(title)

    return ""


def extract_description(soup: BeautifulSoup) -> str:
    """
    作用：
    从详情页中提取简介。

    输入：
    soup: BeautifulSoup 解析后的活动详情页。

    输出：
    简介文字。
    """
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return truncate_text(clean_text(meta.get("content", "")), 220)

    paragraphs = soup.find_all("p")
    for p in paragraphs:
        text = clean_text(p.get_text(" ", strip=True))
        if len(text) >= 60:
            return truncate_text(text, 220)

    return ""


def extract_location(soup: BeautifulSoup) -> str:
    """
    作用：
    从详情页中提取地点。

    输入：
    soup: BeautifulSoup 解析后的活动详情页。

    输出：
    地点文字。

    说明：
    GO TOKYO 活动详情页中，地址通常出现在页面正文里。
    第一版用规则抓取，如果失败就返回 Tokyo。
    """
    try:
        page_text = clean_text(soup.get_text(" ", strip=True))

        address_match = re.search(
            r"([A-Za-z0-9\- ]+,\s*[A-Za-z ]+City,\s*Tokyo)",
            page_text,
        )
        if address_match:
            return clean_text(address_match.group(1))

        location_keywords = ["Location", "Venue", "Place", "Address"]

        for keyword in location_keywords:
            index = page_text.lower().find(keyword.lower())
            if index != -1:
                fragment = page_text[index:index + 180]
                fragment = clean_text(fragment)
                if len(fragment) > len(keyword):
                    return truncate_text(fragment, 120)

        return "Tokyo"

    except Exception:
        print("[go_tokyo] 地点解析失败。")
        traceback.print_exc()
        return "Tokyo"


def extract_time(soup: BeautifulSoup) -> str:
    """
    作用：
    从详情页中提取活动时间。

    输入：
    soup: BeautifulSoup 解析后的活动详情页。

    输出：
    时间文字，例如 13:00 - 15:30。
    """
    try:
        page_text = clean_text(soup.get_text(" ", strip=True))

        time_match = re.search(r"\d{1,2}:\d{2}\s*[-–—]\s*\d{1,2}:\d{2}", page_text)
        if time_match:
            return clean_text(time_match.group(0))

        single_time_match = re.search(r"\d{1,2}:\d{2}", page_text)
        if single_time_match:
            return clean_text(single_time_match.group(0))

        return ""

    except Exception:
        print("[go_tokyo] 时间解析失败。")
        traceback.print_exc()
        return ""


def normalize_dot_date(raw_date: str) -> str:
    """
    作用：
    把 GO TOKYO 常见的点号日期转换成 dateparser 更容易识别的格式。

    输入：
    raw_date:
    例如 2026.4.11

    输出：
    例如 2026-4-11
    """
    return raw_date.replace(".", "-")


def extract_date_range_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    作用：
    从详情页全文中提取日期范围。

    输入：
    text: 页面全文。

    输出：
    (start_date, end_date)
    两者都是 YYYY-MM-DD 或 None。

    支持的常见格式：
    - 2026.4.11 - 2026.7.11
    - 2026-4-11 - 2026-7-11
    - Apr 11, 2026 - Jul 11, 2026
    """
    try:
        clean = clean_text(text)

        dot_range_match = re.search(
            r"(\d{4}\.\d{1,2}\.\d{1,2})\s*[-–—]\s*(\d{4}\.\d{1,2}\.\d{1,2})",
            clean,
        )

        if dot_range_match:
            start_raw = normalize_dot_date(dot_range_match.group(1))
            end_raw = normalize_dot_date(dot_range_match.group(2))
            start_date = parse_date_to_iso(start_raw)
            end_date = parse_date_to_iso(end_raw)
            return start_date, end_date

        dot_single_match = re.search(r"\d{4}\.\d{1,2}\.\d{1,2}", clean)
        if dot_single_match:
            start_raw = normalize_dot_date(dot_single_match.group(0))
            start_date = parse_date_to_iso(start_raw)
            return start_date, None

        month_pattern = (
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[a-z]*\.?\s+\d{1,2},\s+\d{4}"
        )

        range_match = re.search(
            rf"({month_pattern})\s*[-–—]\s*({month_pattern})",
            clean,
            flags=re.IGNORECASE,
        )

        if range_match:
            start_raw = range_match.group(1)
            end_raw = range_match.group(2)
            start_date = parse_date_to_iso(start_raw)
            end_date = parse_date_to_iso(end_raw)
            return start_date, end_date

        single_match = re.search(month_pattern, clean, flags=re.IGNORECASE)
        if single_match:
            start_raw = single_match.group(0)
            start_date = parse_date_to_iso(start_raw)
            return start_date, None

        iso_range_match = re.search(
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*[-–—]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            clean,
        )

        if iso_range_match:
            start_date = parse_date_to_iso(iso_range_match.group(1))
            end_date = parse_date_to_iso(iso_range_match.group(2))
            return start_date, end_date

        iso_single_match = re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", clean)
        if iso_single_match:
            start_date = parse_date_to_iso(iso_single_match.group(0))
            return start_date, None

        return None, None

    except Exception:
        print("[go_tokyo] 日期范围解析失败。")
        traceback.print_exc()
        return None, None


def guess_category(title: str, description: str) -> str:
    """
    作用：
    根据标题和简介粗略判断活动类别。

    输入：
    - title: 活动标题
    - description: 活动简介

    输出：
    category 字符串。
    """
    text = f"{title} {description}".lower()

    if any(word in text for word in ["exhibition", "museum", "gallery", "art", "展", "美術館", "博物館"]):
        return "exhibitions"

    if any(word in text for word in ["theatre", "theater", "performing", "stage", "dance", "kabuki", "noh", "geisha"]):
        return "performing_arts"

    if any(word in text for word in ["market", "festival", "matsuri", "illumination", "fireworks"]):
        return "local_events"

    if any(word in text for word in ["anime", "manga", "game", "esports", "pop"]):
        return "pop_culture"

    return "local_events"


def parse_event_detail_page(
    url: str,
    days_ahead: int,
    source_name: str = SOURCE_NAME,
) -> Optional[Event]:
    """
    作用：
    访问并解析单个 GO TOKYO 活动详情页。

    输入：
    - url: 活动详情页 URL。
    - days_ahead: 未来几天。

    输出：
    Event 或 None。
    如果解析失败、没有日期、日期不在范围内，就返回 None。
    """
    try:
        print(f"[go_tokyo] 解析详情页：{url}")

        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = make_soup_from_response(response)
        page_text = clean_text(soup.get_text(" ", strip=True))

        title = extract_title(soup)
        description = extract_description(soup)
        location = extract_location(soup)
        time_text = extract_time(soup)
        start_date, end_date = extract_date_range_from_text(page_text)

        printable_title = safe_console_text(title)
        print(
            f"[go_tokyo] 解析结果：title={printable_title}, "
            f"start={start_date}, end={end_date}, time={time_text}"
        )

        if not title:
            print(f"[go_tokyo] 丢弃：无标题 url={url}")
            return None

        if not start_date:
            print(f"[go_tokyo] 丢弃：无可解析日期 title={printable_title}")
            return None

        if not date_range_overlaps(start_date, end_date, days_ahead):
            print(
                f"[go_tokyo] 丢弃：不在未来 {days_ahead} 天内 "
                f"title={printable_title} date={start_date} end={end_date}"
            )
            return None

        category = guess_category(title, description)

        return Event(
            title=title,
            category=category,
            start_date=start_date,
            end_date=end_date,
            time=time_text,
            location=location,
            area="",
            description=description,
            recommendation_reason="",
            tags=[],
            source_url=url,
            source_name=source_name,
            fetched_at=now_tokyo().isoformat(timespec="seconds"),
        )

    except Exception:
        print(f"[go_tokyo] 活动详情页解析失败：{url}")
        traceback.print_exc()
        return None


def fetch_go_tokyo_events(
    days_ahead: int,
    source: Optional[dict] = None,
) -> list[Event]:
    """
    作用：
    抓取 GO TOKYO 官方日历中的活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。
    """
    events: list[Event] = []
    calendar_url = str(source.get("url", CALENDAR_URL)) if source else CALENDAR_URL
    source_name = str(source.get("name", SOURCE_NAME)) if source else SOURCE_NAME

    try:
        print(f"[fetcher] 开始抓取 {source_name}：{calendar_url}")

        response = requests.get(
            calendar_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = make_soup_from_response(response)

        event_links = extract_event_links(soup)
        print(f"[go_tokyo] Calendar 页面发现活动详情链接数量：{len(event_links)}")

        for url in event_links[:40]:
            event = parse_event_detail_page(url, days_ahead, source_name)
            if event is not None:
                events.append(event)

        print(f"[fetcher] GO TOKYO 官方日历完成，最终保留 {len(events)} 条。")
        return events

    except Exception:
        print("[fetcher] GO TOKYO 官方日历抓取失败。")
        traceback.print_exc()
        return []
