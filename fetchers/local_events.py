"""
fetchers/local_events.py

这个文件负责抓取地区活动 / 展会 / 节庆 / 市集类活动。

本版本比第一版更强：
1. 优先尝试读取网页中的 JSON-LD 结构化数据。
2. 如果 JSON-LD 里有 Event，就直接解析 Event。
3. 如果没有 JSON-LD Event，再尝试普通 HTML 链接。
4. 会在终端打印调试信息：
   - 找到多少个 JSON-LD script
   - 找到多少个 Event 候选
   - 因为无日期丢弃多少条
   - 最后保留多少条

注意：
这里仍然坚持“不伪造活动”原则。
如果没有明确日期，就不会加入结果。
"""

import json
import traceback
from typing import Any

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Event
from utils.date_utils import now_tokyo, parse_date_to_iso, date_range_overlaps
from utils.text_utils import clean_text, truncate_text


def make_full_url(url: str, base_url: str) -> str:
    """
    作用：
    把相对链接变成完整链接。

    输入：
    - url: 可能是完整链接，也可能是 /events/xxx
    - base_url: 网站首页，例如 https://tokyocheapo.com

    输出：
    完整 URL。
    """
    if not url:
        return ""
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return base_url.rstrip("/") + url
    return base_url.rstrip("/") + "/" + url


def get_location_text(location_data: Any) -> str:
    """
    作用：
    从 JSON-LD 的 location 字段里提取地点文字。

    输入：
    location_data: 可能是字符串、dict、list。

    输出：
    地点文字。
    """
    try:
        if not location_data:
            return ""

        if isinstance(location_data, str):
            return clean_text(location_data)

        if isinstance(location_data, list):
            parts = [get_location_text(item) for item in location_data]
            return clean_text(" / ".join([p for p in parts if p]))

        if isinstance(location_data, dict):
            name = location_data.get("name", "")

            address = location_data.get("address", "")
            if isinstance(address, dict):
                address_text = " ".join(
                    [
                        str(address.get("streetAddress", "")),
                        str(address.get("addressLocality", "")),
                        str(address.get("addressRegion", "")),
                        str(address.get("postalCode", "")),
                    ]
                )
            else:
                address_text = str(address or "")

            return clean_text(f"{name} {address_text}")

        return ""

    except Exception:
        print("[local_events] location 解析失败。")
        traceback.print_exc()
        return ""


def find_event_objects(obj: Any) -> list[dict]:
    """
    作用：
    在任意 JSON 结构中递归寻找 @type 为 Event 的对象。

    输入：
    obj: JSON 解析后的对象，可能是 dict 或 list。

    输出：
    Event dict 列表。
    """
    result = []

    try:
        if isinstance(obj, dict):
            type_value = obj.get("@type")

            is_event = False
            if isinstance(type_value, str):
                is_event = type_value.lower() == "event"
            elif isinstance(type_value, list):
                is_event = any(str(item).lower() == "event" for item in type_value)

            if is_event:
                result.append(obj)

            for value in obj.values():
                result.extend(find_event_objects(value))

        elif isinstance(obj, list):
            for item in obj:
                result.extend(find_event_objects(item))

    except Exception:
        print("[local_events] JSON-LD 递归解析失败。")
        traceback.print_exc()

    return result


def parse_json_ld_events(soup: BeautifulSoup, days_ahead: int, source_name: str, base_url: str) -> tuple[list[Event], int, int]:
    """
    作用：
    从网页里的 JSON-LD script 中解析 Event。

    输入：
    - soup: BeautifulSoup 对象
    - days_ahead: 未来几天
    - source_name: 来源名称
    - base_url: 网站基础 URL

    输出：
    - events: 保留下来的 Event 列表
    - candidate_count: Event 候选数量
    - dropped_no_date_count: 因为没有日期被丢弃的数量
    """
    events: list[Event] = []
    candidate_count = 0
    dropped_no_date_count = 0

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    print(f"[local_events] 找到 JSON-LD script 数量：{len(scripts)}")

    for script in scripts:
        try:
            raw_json = script.string or script.get_text()
            if not raw_json:
                continue

            data = json.loads(raw_json)
            event_objects = find_event_objects(data)

            for item in event_objects:
                candidate_count += 1

                title = clean_text(item.get("name", ""))
                description = truncate_text(clean_text(item.get("description", "")), 180)
                source_url = make_full_url(str(item.get("url", "")), base_url)
                location = get_location_text(item.get("location"))

                raw_start_date = item.get("startDate", "")
                raw_end_date = item.get("endDate", "")

                start_date = parse_date_to_iso(str(raw_start_date))
                end_date = parse_date_to_iso(str(raw_end_date)) if raw_end_date else None

                if not title:
                    continue

                if not start_date:
                    dropped_no_date_count += 1
                    print(f"[local_events] 丢弃：无可解析日期 title={title} raw_start_date={raw_start_date}")
                    continue

                if not date_range_overlaps(start_date, end_date, days_ahead):
                    continue

                events.append(
                    Event(
                        title=title,
                        category="local_events",
                        start_date=start_date,
                        end_date=end_date,
                        time="",
                        location=location or "Tokyo",
                        area="東京23区全体",
                        description=description,
                        recommendation_reason="",
                        tags=[],
                        source_url=source_url,
                        source_name=source_name,
                        fetched_at=now_tokyo().isoformat(timespec="seconds"),
                    )
                )

        except Exception:
            print("[local_events] 某个 JSON-LD script 解析失败。")
            traceback.print_exc()

    return events, candidate_count, dropped_no_date_count


def parse_html_link_events(soup: BeautifulSoup, days_ahead: int, source_name: str, base_url: str) -> tuple[list[Event], int, int]:
    """
    作用：
    从普通 HTML 链接中尝试解析活动。

    输入：
    - soup: BeautifulSoup 对象
    - days_ahead: 未来几天
    - source_name: 来源名称
    - base_url: 网站基础 URL

    输出：
    - events: 保留下来的 Event 列表
    - candidate_count: 候选链接数量
    - dropped_no_date_count: 因为没有日期被丢弃的数量
    """
    events: list[Event] = []
    candidate_count = 0
    dropped_no_date_count = 0

    links = soup.find_all("a", href=True)
    print(f"[local_events] HTML 链接总数：{len(links)}")

    for link in links:
        try:
            href = link.get("href", "")
            title = clean_text(link.get_text(" ", strip=True))

            if not title or len(title) < 4:
                continue

            if "/events/" not in href:
                continue

            candidate_count += 1

            parent_text = ""
            if link.parent:
                parent_text = clean_text(link.parent.get_text(" ", strip=True))

            grandparent_text = ""
            if link.parent and link.parent.parent:
                grandparent_text = clean_text(link.parent.parent.get_text(" ", strip=True))

            raw_text = clean_text(f"{title} {parent_text} {grandparent_text}")
            start_date = parse_date_to_iso(raw_text)

            if not start_date:
                dropped_no_date_count += 1
                if dropped_no_date_count <= 10:
                    print(f"[local_events] HTML 候选无日期，丢弃：{title}")
                continue

            if not date_range_overlaps(start_date, None, days_ahead):
                continue

            events.append(
                Event(
                    title=title,
                    category="local_events",
                    start_date=start_date,
                    end_date=None,
                    time="",
                    location="Tokyo",
                    area="東京23区全体",
                    description=truncate_text(raw_text, 180),
                    recommendation_reason="",
                    tags=[],
                    source_url=make_full_url(href, base_url),
                    source_name=source_name,
                    fetched_at=now_tokyo().isoformat(timespec="seconds"),
                )
            )

        except Exception:
            print("[local_events] HTML 链接解析失败。")
            traceback.print_exc()

    return events, candidate_count, dropped_no_date_count


def fetch_local_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取东京本周地区活动、节庆、市集等。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。失败时返回空列表。
    """
    source_name = "Tokyo Cheapo Events"
    base_url = "https://tokyocheapo.com"
    url = "https://tokyocheapo.com/events/this-week/"

    try:
        print(f"[fetcher] 开始抓取地区活动来源：{source_name} - {url}")

        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        json_events, json_candidates, json_dropped = parse_json_ld_events(
            soup=soup,
            days_ahead=days_ahead,
            source_name=source_name,
            base_url=base_url,
        )

        html_events, html_candidates, html_dropped = parse_html_link_events(
            soup=soup,
            days_ahead=days_ahead,
            source_name=source_name,
            base_url=base_url,
        )

        events = json_events + html_events

        print(
            "[fetcher] 地区活动调试信息："
            f"JSON-LD候选={json_candidates}, "
            f"JSON-LD无日期丢弃={json_dropped}, "
            f"HTML候选={html_candidates}, "
            f"HTML无日期丢弃={html_dropped}, "
            f"最终保留={len(events)}"
        )

        print(f"[fetcher] 地区活动来源完成：{source_name}，抓到 {len(events)} 条。")
        return events

    except Exception:
        print(f"[fetcher] 地区活动来源失败：{source_name}")
        traceback.print_exc()
        return []