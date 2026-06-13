"""
services/recommender.py

这个文件负责把活动分配到页面板块：
- 今晚 / 下班后可以去
- 本周展览
- 本周电影
- Talk / Lecture
- 周末散步顺路活动
- 编辑推荐

第一版用简单规则，不调用 AI。
"""

from typing import Dict, List, Set
from config import MAX_EVENTS_PER_SECTION, SECTIONS
from models import Event
from utils.date_utils import is_today, is_weekend


def event_id(event: Event) -> str:
    """
    作用：
    生成一个活动 ID，用来避免同一个活动重复进入太多板块。

    输入：
    event: 一个 Event。

    输出：
    字符串 ID。
    """
    return f"{event.title}|{event.start_date}|{event.location}"


def take_events(candidates: List[Event], used: Set[str], limit: int) -> List[Event]:
    """
    作用：
    从候选活动里取出最多 limit 个未使用活动。

    输入：
    - candidates: 候选活动
    - used: 已经被其他板块使用过的活动 ID
    - limit: 最多数量

    输出：
    Event 列表。
    """
    result = []
    for event in candidates:
        if len(result) >= limit:
            break
        key = event_id(event)
        if key in used:
            continue
        result.append(event)
        used.add(key)
    return result


def build_sections(events: List[Event]) -> Dict[str, List[Event]]:
    """
    作用：
    把活动分配到各个简报板块。

    输入：
    events: 已经编辑增强后的 Event 列表。

    输出：
    dict，key 是 section id，value 是 Event 列表。
    """
    used: Set[str] = set()
    sections: Dict[str, List[Event]] = {key: [] for key in SECTIONS.keys()}

    tonight_candidates = [
        event for event in events
        if is_today(event.start_date) or "🌙 下班后适合" in event.tags
    ]

    exhibition_candidates = [
        event for event in events
        if event.category == "exhibitions"
    ]

    film_candidates = [
        event for event in events
        if event.category == "movies"
    ]

    lecture_candidates = [
        event for event in events
        if event.category in ["lectures", "bookstore_events"] or "📚 偏知识型" in event.tags
    ]

    weekend_walk_candidates = [
        event for event in events
        if is_weekend(event.start_date) or "🚶 可以顺路散步" in event.tags
    ]

    editors_pick_candidates = [
        event for event in events
        if event.category in ["exhibitions", "lectures", "local_events", "bookstore_events", "pop_culture"]
    ]

    sections["tonight"] = take_events(tonight_candidates, used, MAX_EVENTS_PER_SECTION)
    sections["exhibitions"] = take_events(exhibition_candidates, used, MAX_EVENTS_PER_SECTION)
    sections["films"] = take_events(film_candidates, used, MAX_EVENTS_PER_SECTION)
    sections["lectures"] = take_events(lecture_candidates, used, MAX_EVENTS_PER_SECTION)
    sections["weekend_walk"] = take_events(weekend_walk_candidates, used, MAX_EVENTS_PER_SECTION)
    sections["editors_pick"] = take_events(editors_pick_candidates, used, MAX_EVENTS_PER_SECTION)

    # 如果某些板块为空，编辑推荐可以补充一些尚未出现的活动
    if not sections["editors_pick"]:
        sections["editors_pick"] = take_events(events, used, MAX_EVENTS_PER_SECTION)

    return sections
