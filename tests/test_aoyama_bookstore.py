import pytest

from fetchers.bookstore_events import (
    clean_event_title,
    extract_event_links,
    parse_detail_page,
)
from models import Event
from services.editor import enrich_event
from services.recommender import build_sections


SOURCE = {
    "id": "aoyama_book_center",
    "name": "Aoyama Book Center 活动与讲座",
    "category": "bookstore_events",
    "enabled": True,
    "type": "aoyama_bookstore_events",
    "url": "https://aoyamabc.jp/collections/event",
}


def test_extract_event_links_keeps_only_dated_products() -> None:
    html = b"""
    <a class="product-grid-item"
       href="/collections/event/products/talk">
       7/4 Talk Event
    </a>
    <a class="product-grid-item"
       href="/collections/event/products/course">
       Annual Course
    </a>
    """

    links = extract_event_links(html, SOURCE["url"])

    assert links == ["https://aoyamabc.jp/collections/event/products/talk"]


@pytest.mark.parametrize(
    ("raw_title", "expected"),
    [
        ("【6/16(火)】刊行記念トークイベント", "刊行記念トークイベント"),
        ("【6/ 20 (土)】刊行記念サイン会", "刊行記念サイン会"),
        ("【7/4（土）】出版記念イベント", "出版記念イベント"),
    ],
)
def test_clean_event_title_removes_leading_date(raw_title: str, expected: str) -> None:
    assert clean_event_title(raw_title) == expected


def test_parse_detail_page_builds_bookstore_event() -> None:
    html = """
    <main>
      <h1>【7/4(土)】刊行記念トークイベント</h1>
      <div itemprop="description">
        <table>
          <tr><th>日程</th><td>2026年7月4日 (土)</td></tr>
          <tr><th>時間</th><td>19:00〜20:30</td></tr>
          <tr><th>会場</th><td>本店 大教室</td></tr>
        </table>
        <p>新刊の刊行を記念して、著者を招いたトークイベントを開催します。</p>
      </div>
    </main>
    """.encode("utf-8")

    event = parse_detail_page(
        html,
        "https://aoyamabc.jp/collections/event/products/talk",
        SOURCE,
    )

    assert event.category == "bookstore_events"
    assert event.start_date == "2026-07-04"
    assert event.end_date == "2026-07-04"
    assert event.time == "19:00〜20:30"
    assert event.title == "刊行記念トークイベント"
    assert event.location == "青山ブックセンター本店"
    assert event.area == "表参道・青山"
    assert "📚 书店活动" in event.tags
    assert "💬 小规模活动" in event.tags
    assert event.description
    assert event.source_name == SOURCE["name"]
    assert event.source_url.endswith("/products/talk")


def test_parse_detail_page_rejects_missing_full_date() -> None:
    html = """
    <main>
      <h1>日付不明のトークイベント</h1>
      <div itemprop="description">
        <p>開催日は後日案内される予定です。</p>
      </div>
    </main>
    """.encode("utf-8")

    with pytest.raises(ValueError, match="完整日期"):
        parse_detail_page(
            html,
            "https://aoyamabc.jp/collections/event/products/no-date",
            SOURCE,
        )


@pytest.mark.parametrize(
    ("title", "reason_keyword"),
    [
        ("作者対談トークイベント", "现场交流"),
        ("新刊刊行記念サイン会", "签售"),
        ("新作刊行記念イベント", "新书出版"),
        ("青山の読書イベント", "小规模交流"),
    ],
)
def test_bookstore_recommendation_varies_by_event_type(
    title: str,
    reason_keyword: str,
) -> None:
    event = enrich_event(
        Event(
            title=title,
            category="bookstore_events",
            start_date="2026-07-04",
            location="青山ブックセンター本店",
            area="表参道・青山",
            source_name=SOURCE["name"],
        )
    )

    assert reason_keyword in event.recommendation_reason
    assert "📚 书店活动" in event.tags
    assert "表参道・青山" in event.tags
    assert event.location == "青山ブックセンター本店"


def test_bookstore_event_stays_in_lecture_section() -> None:
    event = enrich_event(
        Event(
            title="刊行記念トークイベント",
            category="bookstore_events",
            start_date="2026-07-04",
            location="青山ブックセンター本店",
            area="表参道・青山",
        )
    )

    sections = build_sections([event])

    assert sections["lectures"] == [event]
