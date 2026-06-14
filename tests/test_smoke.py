from datetime import date
from pathlib import Path

from app import build_light_table_html
from fetchers.registry import get_fetcher, load_sources
from models import Event
from services import collector
from services.editor import enrich_events
from services.recommender import build_sections
from utils import date_utils


def test_sources_config_loads() -> None:
    sources = load_sources()

    assert sources
    assert all(
        {"id", "name", "category", "enabled", "type", "url"} <= source.keys()
        for source in sources
    )


def test_app_download_flow_does_not_call_local_save_helpers() -> None:
    app_source = Path("app.py").read_text(encoding="utf-8")

    assert "save_csv(" not in app_source
    assert "save_markdown(" not in app_source
    assert "save_ics(" not in app_source
    assert "文件已保存到 output 文件夹" not in app_source
    assert "下载不会自动写入项目 output 文件夹" in app_source


def test_page_keeps_downloads_and_source_status_without_raw_preview() -> None:
    app_source = Path("app.py").read_text(encoding="utf-8")

    assert 'class="maintenance-table"' in app_source
    assert "maintenance-table-wrap" in app_source
    assert "st.dataframe(" not in app_source
    assert "原始数据预览" not in app_source
    assert 'st.expander("来源状态")' in app_source
    assert all(
        label in app_source
        for label in ["下载 CSV", "下载 Markdown", "下载 ICS"]
    )


def test_light_table_html_keeps_columns_and_escapes_values() -> None:
    columns = ["来源 ID", "状态", "最近错误摘要"]
    table_html = build_light_table_html(
        [
            {
                "来源 ID": "aoyama_book_center",
                "状态": "成功",
                "最近错误摘要": "<script>unsafe</script>",
            }
        ],
        columns,
    )

    assert all(f"<th>{column}</th>" in table_html for column in columns)
    assert "aoyama_book_center" in table_html
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in table_html
    assert "<script>unsafe</script>" not in table_html


def test_enabled_sources_have_registered_fetchers() -> None:
    enabled_sources = [source for source in load_sources() if source["enabled"]]

    assert enabled_sources
    assert all(get_fetcher(source["type"]) is not None for source in enabled_sources)


def test_event_to_dict_serializes_tags() -> None:
    event = Event(
        title="Mock Exhibition",
        category="exhibitions",
        start_date="2026-06-13",
        tags=["展览", "周末"],
    )

    data = event.to_dict()

    assert data["title"] == "Mock Exhibition"
    assert data["category"] == "exhibitions"
    assert data["tags"] == "展览 / 周末"


def test_date_range_overlaps_basic_ranges(monkeypatch) -> None:
    monkeypatch.setattr(date_utils, "today_tokyo", lambda: date(2026, 6, 13))

    assert date_utils.date_range_overlaps("2026-06-13", None, 7)
    assert date_utils.date_range_overlaps("2026-06-01", "2026-06-14", 7)
    assert date_utils.date_range_overlaps("2026-06-20", None, 7)
    assert not date_utils.date_range_overlaps("2026-06-21", None, 7)
    assert not date_utils.date_range_overlaps(None, None, 7)


def test_editor_and_recommender_accept_mock_event() -> None:
    event = Event(
        title="Mock Tokyo Exhibition",
        category="exhibitions",
        start_date="2026-06-14",
        end_date="2026-06-20",
        location="Ueno, Tokyo",
        description="A mock exhibition used for the MVP smoke test.",
        source_name="Smoke Test",
        source_url="https://example.com/event",
    )

    enriched_events = enrich_events([event])
    sections = build_sections(enriched_events)

    assert len(enriched_events) == 1
    assert enriched_events[0].area
    assert enriched_events[0].recommendation_reason
    assert set(sections) == {
        "tonight",
        "exhibitions",
        "films",
        "lectures",
        "weekend_walk",
        "editors_pick",
    }


def test_collector_records_source_status_and_isolates_failures(monkeypatch) -> None:
    sources = [
        {
            "id": "success",
            "name": "Successful Source",
            "category": "exhibitions",
            "enabled": True,
            "type": "success_type",
            "url": "https://example.com/success",
        },
        {
            "id": "failed",
            "name": "Failed Source",
            "category": "local_events",
            "enabled": True,
            "type": "failed_type",
            "url": "https://example.com/failed",
        },
        {
            "id": "disabled",
            "name": "Disabled Source",
            "category": "mixed",
            "enabled": False,
            "type": "success_type",
            "url": "https://example.com/disabled",
        },
        {
            "id": "unregistered",
            "name": "Unregistered Source",
            "category": "mixed",
            "enabled": True,
            "type": "missing_type",
            "url": "https://example.com/unregistered",
        },
    ]

    def successful_fetcher(source, days_ahead):
        return [Event(title="Mock Event", category="exhibitions")]

    def failed_fetcher(source, days_ahead):
        raise RuntimeError("mock fetch failure")

    fetchers = {
        "success_type": successful_fetcher,
        "failed_type": failed_fetcher,
    }
    monkeypatch.setattr(collector, "load_sources", lambda: sources)
    monkeypatch.setattr(collector, "get_fetcher", fetchers.get)
    monkeypatch.setattr(collector, "filter_by_date", lambda events, days: events)

    events, errors, statuses = collector.collect_events(7, [])
    statuses_by_id = {status["source_id"]: status for status in statuses}

    assert len(events) == 1
    assert len(errors) == 1
    assert statuses_by_id["success"]["status"] == "success"
    assert statuses_by_id["success"]["event_count"] == 1
    assert statuses_by_id["failed"]["status"] == "failed"
    assert "RuntimeError: mock fetch failure" in statuses_by_id["failed"]["last_error"]
    assert statuses_by_id["disabled"]["status"] == "skipped"
    assert statuses_by_id["unregistered"]["status"] == "skipped"


def test_collector_always_returns_three_values_on_config_failure(monkeypatch) -> None:
    def fail_to_load_sources():
        raise ValueError("mock config failure")

    monkeypatch.setattr(collector, "load_sources", fail_to_load_sources)

    result = collector.collect_events(7, [])

    assert len(result) == 3
    events, errors, statuses = result
    assert events == []
    assert errors
    assert statuses == []


def test_collector_always_returns_three_values_on_filter_failure(monkeypatch) -> None:
    source = {
        "id": "success",
        "name": "Successful Source",
        "category": "exhibitions",
        "enabled": True,
        "type": "success_type",
        "url": "https://example.com/success",
    }

    monkeypatch.setattr(collector, "load_sources", lambda: [source])
    monkeypatch.setattr(
        collector,
        "get_fetcher",
        lambda source_type: lambda source_config, days_ahead: [
            Event(title="Mock Event", category="exhibitions")
        ],
    )
    monkeypatch.setattr(
        collector,
        "filter_by_selected_categories",
        lambda events, categories: (_ for _ in ()).throw(ValueError("mock filter failure")),
    )

    result = collector.collect_events(7, [])

    assert len(result) == 3
    events, errors, statuses = result
    assert events == []
    assert errors
    assert len(statuses) == 1
    assert statuses[0]["status"] == "success"
