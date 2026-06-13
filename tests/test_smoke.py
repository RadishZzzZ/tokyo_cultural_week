from datetime import date

from fetchers.registry import get_fetcher, load_sources
from models import Event
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
