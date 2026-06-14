"""
数据源类型注册表。

collector 只关心 sources.json 中的配置；这里负责把 source.type
映射到统一的 fetcher 调用接口。
"""

import json
import traceback
from pathlib import Path
from typing import Callable, Optional

from models import Event
from fetchers.bookstore_events import fetch_aoyama_bookstore_events
from fetchers.go_tokyo import fetch_go_tokyo_events
from fetchers.mori import fetch_mori_source
from fetchers.tobikan import fetch_tobikan_exhibitions


SourceConfig = dict
SourceFetcher = Callable[[SourceConfig, int], list[Event]]
REQUIRED_SOURCE_FIELDS = {"id", "name", "category", "enabled", "type", "url"}
SOURCES_FILE = Path(__file__).resolve().parent.parent / "sources.json"


def fetch_go_tokyo_source(source: SourceConfig, days_ahead: int) -> list[Event]:
    return fetch_go_tokyo_events(days_ahead, source)


def fetch_tobikan_source(source: SourceConfig, days_ahead: int) -> list[Event]:
    return fetch_tobikan_exhibitions(days_ahead, source)


FETCHER_REGISTRY: dict[str, SourceFetcher] = {
    "aoyama_bookstore_events": fetch_aoyama_bookstore_events,
    "go_tokyo_calendar": fetch_go_tokyo_source,
    "tobikan_exhibitions": fetch_tobikan_source,
    "mori_known_events": fetch_mori_source,
}


def load_sources(path: Path = SOURCES_FILE) -> list[SourceConfig]:
    """
    读取并校验 sources.json。

    配置文件整体无效时抛出异常，由 collector 统一记录。
    单条配置缺字段时跳过，并在终端打印原因。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        raw_sources = data.get("sources", [])

        if not isinstance(raw_sources, list):
            raise ValueError("sources.json 的 sources 必须是列表。")

        sources: list[SourceConfig] = []
        seen_ids = set()

        for index, source in enumerate(raw_sources):
            if not isinstance(source, dict):
                print(f"[sources] 跳过第 {index + 1} 项：配置必须是对象。")
                continue

            missing_fields = REQUIRED_SOURCE_FIELDS - source.keys()
            if missing_fields:
                missing = ", ".join(sorted(missing_fields))
                print(f"[sources] 跳过第 {index + 1} 项：缺少字段 {missing}。")
                continue

            source_id = str(source["id"]).strip()
            source_name = str(source["name"]).strip()
            source_type = str(source["type"]).strip()
            source_url = str(source["url"]).strip()

            if not source_id:
                print(f"[sources] 跳过第 {index + 1} 项：id 不能为空。")
                continue

            if not source_name or not source_type or not source_url:
                print(
                    f"[sources] 跳过来源 {source_id}："
                    "name、type、url 不能为空。"
                )
                continue

            if not isinstance(source["enabled"], bool):
                print(f"[sources] 跳过来源 {source_id}：enabled 必须是 true 或 false。")
                continue

            if source_id in seen_ids:
                print(f"[sources] 跳过重复 id：{source_id}")
                continue

            seen_ids.add(source_id)
            sources.append(source)

        return sources

    except Exception:
        print(f"[sources] 读取数据源配置失败：{path}")
        traceback.print_exc()
        raise


def get_fetcher(source_type: str) -> Optional[SourceFetcher]:
    return FETCHER_REGISTRY.get(source_type)
