"""
services/collector.py

这个文件负责“收集所有来源的数据”。
它会调用有效 fetcher，合并活动，并做日期过滤、类别过滤、去重、排序。

当前策略：
1. sources.json 集中管理来源是否启用、类型、类别和入口 URL。
2. fetchers/registry.py 按 source.type 选择对应抓取实现。
3. collector 不再直接维护网站列表。
4. 未启用或尚未实现的来源会被优雅跳过，并在终端打印说明。
"""

import traceback
from typing import List, Tuple, TypedDict

from models import Event
from fetchers.registry import get_fetcher, load_sources
from utils.date_utils import date_range_overlaps
from utils.text_utils import normalize_for_dedup


class SourceStatus(TypedDict):
    source_id: str
    source_name: str
    category: str
    enabled: bool
    status: str
    event_count: int
    last_error: str


def _build_source_status(source: dict) -> SourceStatus:
    return {
        "source_id": str(source["id"]),
        "source_name": str(source["name"]),
        "category": str(source["category"]),
        "enabled": bool(source["enabled"]),
        "status": "skipped",
        "event_count": 0,
        "last_error": "",
    }


def _summarize_error(error: Exception, limit: int = 180) -> str:
    detail = " ".join(str(error).split())
    summary = f"{type(error).__name__}: {detail}" if detail else type(error).__name__
    return summary if len(summary) <= limit else f"{summary[:limit - 3]}..."


def filter_by_selected_categories(events: List[Event], selected_categories: List[str]) -> List[Event]:
    """
    作用：
    根据用户在侧边栏选择的类别过滤活动。

    输入：
    - events: Event 列表
    - selected_categories: 用户选择的类别 key 列表

    输出：
    过滤后的 Event 列表。
    """
    if not selected_categories:
        return events

    return [event for event in events if event.category in selected_categories]


def filter_by_date(events: List[Event], days_ahead: int) -> List[Event]:
    """
    作用：
    只保留和“今天到未来 N 天”有重叠的活动。

    输入：
    - events: Event 列表
    - days_ahead: 未来几天

    输出：
    过滤后的 Event 列表。
    """
    return [
        event
        for event in events
        if date_range_overlaps(event.start_date, event.end_date, days_ahead)
    ]


def deduplicate_events(events: List[Event]) -> List[Event]:
    """
    作用：
    根据“标题 + 开始日期 + 地点”进行简单去重。

    输入：
    events: Event 列表。

    输出：
    去重后的 Event 列表。
    """
    seen = set()
    result = []

    for event in events:
        key = (
            normalize_for_dedup(event.title),
            event.start_date or "",
            normalize_for_dedup(event.location),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


def sort_events(events: List[Event]) -> List[Event]:
    """
    作用：
    对活动排序。

    输入：
    events: Event 列表。

    输出：
    排序后的 Event 列表。

    排序规则：
    - 有日期的排前面
    - 日期越早越前
    - 日期相同按 category 排
    - 日期不明放最后
    """
    return sorted(
        events,
        key=lambda event: (
            event.start_date is None,
            event.start_date or "9999-12-31",
            event.category,
            event.title,
        ),
    )


def collect_events(
    days_ahead: int,
    selected_categories: List[str],
) -> Tuple[List[Event], List[str], List[SourceStatus]]:
    """
    作用：
    调用有效 fetcher，收集活动，并做日期过滤、类别过滤、去重、排序。

    输入：
    - days_ahead: 未来几天
    - selected_categories: 用户选择的类别 key 列表

    输出：
    - events: Event 列表
    - errors: 简洁错误说明列表，给页面显示
    - source_statuses: 每个配置来源本次调用的状态、返回数量和错误摘要
    """
    all_events: List[Event] = []
    errors: List[str] = []
    source_statuses: List[SourceStatus] = []

    try:
        sources = load_sources()
    except Exception:
        message = "数据源配置读取失败，无法开始抓取。"
        errors.append(message)
        print(f"[collector] {message}")
        traceback.print_exc()
        return [], errors, source_statuses

    for source in sources:
        try:
            source_id = str(source["id"])
            source_name = str(source["name"])
            source_type = str(source["type"])
            source_status = _build_source_status(source)
            source_statuses.append(source_status)
        except Exception as error:
            message = "来源配置处理失败，但其他来源会继续处理。"
            errors.append(message)
            print(f"[collector] {message}")
            traceback.print_exc()
            continue

        if not source["enabled"]:
            source_status["last_error"] = "来源当前未启用。"
            print(f"[collector] 跳过未启用来源：{source_id} ({source_name})")
            continue

        fetcher_function = get_fetcher(source_type)
        if fetcher_function is None:
            source_status["last_error"] = f"尚未注册 fetcher type：{source_type}"
            print(
                f"[collector] 跳过未实现来源：{source_id} ({source_name})，"
                f"type={source_type}"
            )
            continue

        try:
            print(
                f"[collector] 调用来源：{source_id} ({source_name})，"
                f"type={source_type}"
            )
            events = fetcher_function(source, days_ahead)
            all_events.extend(events)
            source_status["status"] = "success"
            source_status["event_count"] = len(events)
            print(f"[collector] {source_id} 返回 {len(events)} 条。")

        except Exception as error:
            message = f"{source_name} 来源暂时抓取失败，但其他来源会继续处理。"
            errors.append(message)
            source_status["status"] = "failed"
            source_status["last_error"] = _summarize_error(error)
            print(f"[collector] {message}")
            traceback.print_exc()

    try:
        all_events = filter_by_selected_categories(all_events, selected_categories)
        all_events = filter_by_date(all_events, days_ahead)
        all_events = deduplicate_events(all_events)
        all_events = sort_events(all_events)

        print(f"[collector] 合并过滤后最终活动数量：{len(all_events)}")
        return all_events, errors, source_statuses

    except Exception:
        message = "活动合并、过滤、去重或排序时出错。"
        errors.append(message)
        print(f"[collector] {message}")
        traceback.print_exc()
        return [], errors, source_statuses
