"""
青山ブックセンター“イベント・講座”页面抓取器。

集合页只提供月日，详情页提供完整年份、时间、会场和活动简介。
为了避免年份猜测，本抓取器只使用详情页中的明确日期。
"""

import re
import traceback
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Event
from utils.date_utils import date_range_overlaps, now_tokyo
from utils.text_utils import clean_text, truncate_text


DEFAULT_LOCATION = "青山ブックセンター本店"
DEFAULT_AREA = "表参道・青山"
DATED_TITLE_PATTERN = re.compile(r"\d{1,2}\s*/\s*\d{1,2}")
LEADING_DATE_PATTERN = re.compile(
    r"^\s*【\s*\d{1,2}\s*/\s*\d{1,2}\s*"
    r"(?:\([^】]*\)|（[^】]*）)?\s*】\s*"
)
FULL_DATE_PATTERN = re.compile(
    r"日程\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日"
)


def clean_event_title(title: str) -> str:
    return clean_text(LEADING_DATE_PATTERN.sub("", clean_text(title)))


def extract_event_links(collection_html: bytes, collection_url: str) -> list[str]:
    soup = BeautifulSoup(collection_html, "html.parser", from_encoding="utf-8")
    links: list[str] = []
    seen = set()

    for anchor in soup.select('a.product-grid-item[href*="/collections/event/products/"]'):
        title = clean_text(anchor.get_text(" ", strip=True))
        href = anchor.get("href", "")
        if not href or not DATED_TITLE_PATTERN.search(title):
            continue

        event_url = urljoin(collection_url, href)
        if event_url in seen:
            continue

        seen.add(event_url)
        links.append(event_url)

    return links


def parse_detail_page(
    detail_html: bytes,
    detail_url: str,
    source: dict,
) -> Event:
    soup = BeautifulSoup(detail_html, "html.parser", from_encoding="utf-8")
    title_node = soup.select_one("main h1")
    description_node = soup.select_one('[itemprop="description"]')

    title = (
        clean_event_title(title_node.get_text(" ", strip=True))
        if title_node
        else ""
    )
    if not title:
        raise ValueError(f"活动详情页缺少标题：{detail_url}")
    if description_node is None:
        raise ValueError(f"活动详情页缺少正文区域：{detail_url}")

    detail_text = clean_text(description_node.get_text(" ", strip=True))
    date_match = FULL_DATE_PATTERN.search(detail_text)
    if date_match is None:
        raise ValueError(f"活动详情页缺少可解析的完整日期：{detail_url}")

    year, month, day = (int(value) for value in date_match.groups())
    start_date = f"{year:04d}-{month:02d}-{day:02d}"

    time_text = ""
    info_table = description_node.find("table")
    if info_table:
        for row in info_table.select("tr"):
            cells = [
                clean_text(cell.get_text(" ", strip=True))
                for cell in row.select("th, td")
            ]
            if len(cells) >= 2 and cells[0] == "時間":
                time_text = cells[1]
                break

    description = ""
    for paragraph in description_node.find_all("p", recursive=False):
        paragraph_text = clean_text(paragraph.get_text(" ", strip=True))
        if len(paragraph_text) >= 20:
            description = truncate_text(paragraph_text, 180)
            break

    if not description:
        description = "青山ブックセンター本店で開催されるイベント・講座です。"

    return Event(
        title=title,
        category=str(source.get("category") or "bookstore_events"),
        start_date=start_date,
        end_date=start_date,
        time=time_text,
        location=DEFAULT_LOCATION,
        area=DEFAULT_AREA,
        description=description,
        tags=["📚 书店活动", "💬 小规模活动"],
        source_url=detail_url,
        source_name=str(source.get("name") or "Aoyama Book Center 活动与讲座"),
        fetched_at=now_tokyo().isoformat(),
    )


def fetch_aoyama_bookstore_events(source: dict, days_ahead: int) -> list[Event]:
    source_name = str(source["name"])
    collection_url = str(source["url"])
    headers = {"User-Agent": USER_AGENT}

    print(f"[fetcher] 开始抓取 {source_name}：{collection_url}")
    response = requests.get(
        collection_url,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    event_links = extract_event_links(response.content, collection_url)
    print(f"[aoyama_book_center] 找到明确日期的活动链接：{len(event_links)}")
    if not event_links:
        raise ValueError("集合页未找到带明确月日的活动详情链接。")

    events: list[Event] = []
    parse_errors: list[str] = []
    parsed_count = 0

    for detail_url in event_links:
        try:
            detail_response = requests.get(
                detail_url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            detail_response.raise_for_status()
            event = parse_detail_page(detail_response.content, detail_url, source)
            parsed_count += 1

            if date_range_overlaps(event.start_date, event.end_date, days_ahead):
                events.append(event)
                print(
                    f"[aoyama_book_center] 保留活动："
                    f"{event.start_date} {detail_url}"
                )
            else:
                print(
                    f"[aoyama_book_center] 日期范围外："
                    f"{event.start_date} {detail_url}"
                )

        except Exception as error:
            parse_errors.append(f"{detail_url}: {type(error).__name__}: {error}")
            print(f"[aoyama_book_center] 详情页解析失败：{detail_url}")
            traceback.print_exc()

    if parsed_count == 0 and parse_errors:
        raise RuntimeError(
            f"{len(parse_errors)} 个活动详情页均解析失败；"
            f"最近错误：{parse_errors[-1]}"
        )

    print(
        f"[fetcher] {source_name} 完成："
        f"详情解析成功 {parsed_count} 条，日期范围内 {len(events)} 条，"
        f"解析失败 {len(parse_errors)} 条。"
    )
    return events
