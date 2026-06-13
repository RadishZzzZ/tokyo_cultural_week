"""
fetchers/lectures.py

这个文件负责抓取社会学讲座 / 公开讲座 / 学术活动 / Talk event。

第一版说明：
大学公开讲座页面、研究机构活动页、书店 talk event 页面结构差异很大。
为了不写不稳定爬虫，第一版保留接口并返回空列表。

后续适合加入的来源：
- 東京大学公开讲座页面
- 早稲田大学イベント页面
- 上智 / 東工大 / 一橋公开活动
- 本屋 B&B、青山ブックセンター等 Talk event 页面
"""

import traceback
from models import Event


def fetch_lecture_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取讲座 / 学术活动。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。第一版暂时返回空列表。
    """
    try:
        print("[fetcher] lectures：第一版暂未接入稳定讲座数据源，返回空列表。")
        return []

    except Exception:
        print("[fetcher] lectures 抓取失败。")
        traceback.print_exc()
        return []
