"""
fetchers/performing_arts.py

这个文件负责抓取舞台 / 表演 / 小剧场类活动。

第一版说明：
舞台和小剧场信息通常分散在剧场官网、票务网站和活动平台。
为了避免不稳定抓取，第一版先保留接口。
"""

import traceback
from models import Event


def fetch_performing_arts_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取舞台 / 表演活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。第一版暂时返回空列表。
    """
    try:
        print("[fetcher] performing_arts：第一版暂未接入稳定舞台活动数据源，返回空列表。")
        return []

    except Exception:
        print("[fetcher] performing_arts 抓取失败。")
        traceback.print_exc()
        return []
