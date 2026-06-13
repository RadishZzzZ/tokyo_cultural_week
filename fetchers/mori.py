"""
fetchers/mori.py

这个文件负责抓取 Roppongi Hills / Mori 系列文化空间的当前和即将举行活动。

当前抓取来源：
1. Mori Art Museum / 森美術館
2. Mori Arts Center Gallery / 森アーツセンターギャラリー
3. Tokyo City View

本版本修正：
1. 彻底避免同一标题被错误配上别的活动日期。
2. 对 Mori 当前可识别的三个活动使用“标题白名单 + 官方日期配置”。
3. 页面中只要能找到这些标题，就生成对应 Event。
4. 不再从大区块里随便抽第一个日期，避免 SANRIO / Orb / Ron Mueck 日期互相串。
5. 单个来源失败不影响其他来源。
6. 所有错误打印 traceback。

说明：
这是一种务实写法。Mori 系列页面当前 HTML 混有导航、多个场馆、多个活动。
对这种页面，先用稳定白名单比复杂正则更可靠。
以后如果要泛化，可以再接 OpenAI API 或更精细的详情页解析。
"""

import traceback
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Event
from utils.date_utils import now_tokyo, date_range_overlaps
from utils.text_utils import clean_text, truncate_text, normalize_for_dedup


MORI_SOURCE_PAGES = [
    {
        "source_name": "Mori Art Museum",
        "url": "https://www.mori.art.museum/en/exhibitions/",
    },
    {
        "source_name": "Mori Arts Center Gallery",
        "url": "https://macg.roppongihills.com/en/exhibitions/",
    },
    {
        "source_name": "Tokyo City View",
        "url": "https://tcv.roppongihills.com/en/exhibitions/",
    },
]


# 当前 Mori 系列页面里可稳定识别的活动。
# 注意：这里不是伪造活动，而是用页面中出现的标题触发，然后使用明确日期配置，避免网页大区块导致标题和日期串线。
KNOWN_MORI_EVENTS = [
    {
        "title": "Ron Mueck",
        "category": "exhibitions",
        "start_date": "2026-04-29",
        "end_date": "2026-09-23",
        "location": "Mori Art Museum, Roppongi Hills Mori Tower 53F",
        "area": "六本木",
        "source_name": "Mori Art Museum",
        "source_url": "https://www.mori.art.museum/en/exhibitions/ronmueck/",
        "description": "Ron Mueck exhibition at Mori Art Museum.",
        "keywords": ["Ron Mueck"],
    },
    {
        "title": "SANRIO EXHIBITION FINAL ver. THE BEGINNING of KAWAII",
        "category": "pop_culture",
        "start_date": "2026-04-09",
        "end_date": "2026-06-21",
        "location": "Mori Arts Center Gallery, Roppongi Hills Mori Tower 52F",
        "area": "六本木",
        "source_name": "Mori Arts Center Gallery",
        "source_url": "https://macg.roppongihills.com/en/exhibitions/",
        "description": "SANRIO EXHIBITION FINAL ver. THE BEGINNING of KAWAII at Mori Arts Center Gallery.",
        "keywords": [
            "SANRIO EXHIBITION FINAL ver. THE BEGINNING of KAWAII",
            "SANRIO EXHIBITION",
            "THE BEGINNING of KAWAII",
        ],
    },
    {
        "title": "Escape from the Observation Deck in Peril",
        "category": "pop_culture",
        "start_date": "2026-06-19",
        "end_date": "2026-07-21",
        "location": "Tokyo City View, Roppongi Hills Mori Tower 52F",
        "area": "六本木",
        "source_name": "Tokyo City View",
        "source_url": "https://tcv.roppongihills.com/en/exhibitions/escape2026/",
        "description": "A real escape game event held at Tokyo City View.",
        "keywords": [
            "Escape from the Observation Deck in Peril",
            "Observation Deck in Peril",
            "escape2026",
        ],
    },
]


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


def make_full_url(base_url: str, href: str) -> str:
    """
    作用：
    把相对链接转换成完整链接。

    输入：
    - base_url: 当前页面 URL
    - href: 页面里的链接

    输出：
    完整 URL。
    """
    if not href:
        return base_url
    return urljoin(base_url, href)


def page_contains_event(page_text: str, event_config: dict) -> bool:
    """
    作用：
    判断页面文字中是否出现某个已知活动。

    输入：
    - page_text: 网页全文
    - event_config: KNOWN_MORI_EVENTS 中的一个配置

    输出：
    True / False。
    """
    lowered_text = page_text.lower()

    for keyword in event_config["keywords"]:
        if keyword.lower() in lowered_text:
            return True

    return False


def find_best_source_url(soup: BeautifulSoup, page_url: str, event_config: dict) -> str:
    """
    作用：
    尝试找到更具体的活动链接。

    输入：
    - soup: 当前页面
    - page_url: 当前页面 URL
    - event_config: 活动配置

    输出：
    来源链接。
    """
    try:
        for a_tag in soup.find_all("a", href=True):
            link_text = clean_text(a_tag.get_text(" ", strip=True))

            for keyword in event_config["keywords"]:
                if keyword.lower() in link_text.lower():
                    return make_full_url(page_url, a_tag.get("href", ""))

        return event_config.get("source_url") or page_url

    except Exception:
        print("[mori] 查找活动详情链接失败。")
        traceback.print_exc()
        return event_config.get("source_url") or page_url


def build_event_from_config(event_config: dict, source_url: str) -> Event:
    """
    作用：
    根据已知活动配置生成 Event。

    输入：
    - event_config: 活动配置
    - source_url: 来源链接

    输出：
    Event 对象。
    """
    return Event(
        title=event_config["title"],
        category=event_config["category"],
        start_date=event_config["start_date"],
        end_date=event_config["end_date"],
        time="",
        location=event_config["location"],
        area=event_config["area"],
        description=truncate_text(event_config["description"], 220),
        recommendation_reason="",
        tags=[],
        source_url=source_url,
        source_name=event_config["source_name"],
        fetched_at=now_tokyo().isoformat(timespec="seconds"),
    )


def fetch_one_mori_page(page_config: dict, days_ahead: int) -> list[Event]:
    """
    作用：
    抓取一个 Mori 系列页面，并识别其中出现的已知活动。

    输入：
    - page_config: MORI_SOURCE_PAGES 中的一个页面配置
    - days_ahead: 未来几天

    输出：
    Event 列表。
    """
    events: list[Event] = []

    source_name = page_config["source_name"]
    page_url = page_config["url"]

    try:
        print(f"[fetcher] 开始抓取 Mori 页面：{source_name} - {page_url}")

        response = requests.get(
            page_url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = make_soup_from_response(response)
        page_text = clean_text(soup.get_text(" ", strip=True))

        matched_count = 0
        out_of_range_count = 0

        for event_config in KNOWN_MORI_EVENTS:
            if event_config["source_name"] != source_name:
                continue

            if not page_contains_event(page_text, event_config):
                continue

            matched_count += 1

            if not date_range_overlaps(
                event_config["start_date"],
                event_config["end_date"],
                days_ahead,
            ):
                out_of_range_count += 1
                continue

            source_url = find_best_source_url(soup, page_url, event_config)
            event = build_event_from_config(event_config, source_url)
            events.append(event)

            print(
                f"[mori] 匹配活动：{event.title} "
                f"{event.start_date} - {event.end_date} "
                f"{event.source_name}"
            )

        print(
            f"[mori] {source_name} 调试信息："
            f"页面匹配={matched_count}, "
            f"日期范围外={out_of_range_count}, "
            f"本页保留={len(events)}"
        )

        return events

    except Exception:
        print(f"[fetcher] Mori 页面抓取失败：{source_name}")
        traceback.print_exc()
        return []


def fetch_mori_source(source: dict, days_ahead: int) -> list[Event]:
    """
    按 sources.json 中的一条 Mori 页面配置抓取活动。
    """
    page_config = {
        "source_name": str(source["name"]),
        "url": str(source["url"]),
    }
    return fetch_one_mori_page(page_config, days_ahead)


def deduplicate_mori_events(events: list[Event]) -> list[Event]:
    """
    作用：
    对 Mori 系列活动去重。

    输入：
    events: Event 列表。

    输出：
    去重后的 Event 列表。

    去重规则：
    只按标题去重。
    因为这里每个已知标题对应一个明确活动。
    """
    result: list[Event] = []
    seen = set()

    for event in events:
        key = normalize_for_dedup(event.title)

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


def fetch_mori_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取 Mori Art Museum / Mori Arts Center Gallery / Tokyo City View 的活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。
    """
    all_events: list[Event] = []

    for page_config in MORI_SOURCE_PAGES:
        events = fetch_one_mori_page(page_config, days_ahead)
        all_events.extend(events)

    deduplicated_events = deduplicate_mori_events(all_events)

    print(
        f"[fetcher] Mori 系列来源完成，"
        f"去重前={len(all_events)} 条，去重后={len(deduplicated_events)} 条。"
    )

    return deduplicated_events
