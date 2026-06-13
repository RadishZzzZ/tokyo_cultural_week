"""
fetchers/pop_culture.py

这个文件负责抓取动漫 / 游戏 / pop culture 活动。

第一版说明：
动漫、游戏活动可能来自官方活动页、展会官网、Akiba 相关网站等。
由于来源差异大，第一版先保留接口。
"""

import traceback
from models import Event


def fetch_pop_culture_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取动漫 / 游戏 / pop culture 活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。第一版暂时返回空列表。
    """
    try:
        print("[fetcher] pop_culture：第一版暂未接入稳定亚文化活动数据源，返回空列表。")
        return []

    except Exception:
        print("[fetcher] pop_culture 抓取失败。")
        traceback.print_exc()
        return []
