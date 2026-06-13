"""
fetchers/bookstore_events.py

这个文件负责抓取书店活动。

第一版说明：
东京书店活动很适合这个 App，但不同书店页面结构差异很大。
为了稳定，第一版不强行解析，先保留接口。

后续可加入：
- 本屋 B&B
- 青山ブックセンター
- 代官山 蔦屋書店
- ジュンク堂 / 丸善 活动页面
"""

import traceback
from models import Event


def fetch_bookstore_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取书店活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。第一版暂时返回空列表。
    """
    try:
        print("[fetcher] bookstore_events：第一版暂未接入稳定书店活动数据源，返回空列表。")
        return []

    except Exception:
        print("[fetcher] bookstore_events 抓取失败。")
        traceback.print_exc()
        return []
