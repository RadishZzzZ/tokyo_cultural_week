"""
fetchers/movies.py

这个文件负责抓取新电影上映信息。

第一版说明：
电影上映信息通常来自映画館官网、映画.com、Filmarks、Time Out Tokyo 等。
这些页面经常有动态结构、地区筛选、反爬或版权限制。
为了第一版稳定，不强行写脆弱爬虫。

当前实现：
- 保留 fetch_movies_events(days_ahead) 接口。
- 返回空列表。
- 终端明确打印说明。
后续可以加入：
- 某个电影院官网的 RSS
- Time Out Tokyo film 页面
- 映画.com 的公开页面，但要注意结构变化
"""

import traceback
from models import Event


def fetch_movies_events(days_ahead: int) -> list[Event]:
    """
    作用：
    抓取本周新电影上映信息。

    输入：
    days_ahead: 未来几天内的活动。

    输出：
    Event 列表。第一版暂时返回空列表。
    """
    try:
        print("[fetcher] movies：第一版暂未接入稳定电影数据源，返回空列表。")
        return []

    except Exception:
        print("[fetcher] movies 抓取失败。")
        traceback.print_exc()
        return []
