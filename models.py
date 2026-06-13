"""
models.py

这个文件定义 App 内部统一使用的 Event 数据结构。
所有 fetcher 抓到的活动，都要整理成 Event。
这样后面的编辑、去重、排序、保存 CSV、生成 Markdown 都可以使用同一种格式。
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class Event:
    """
    Event 表示一个文化活动。

    字段说明：
    - title: 活动名称
    - category: 活动类别，例如 movies / exhibitions / lectures
    - start_date: 开始日期，格式建议为 YYYY-MM-DD；没有日期时可以是 None
    - end_date: 结束日期，格式建议为 YYYY-MM-DD；没有结束日期时可以是 None
    - time: 时间文字，例如 19:00；没有时间时可以是空字符串
    - location: 地点名称
    - area: 区域，例如 渋谷 / 上野；可以由 editor.py 自动推断
    - description: 简短介绍
    - recommendation_reason: 推荐理由
    - tags: 标签列表
    - source_url: 来源链接
    - source_name: 来源名称
    - fetched_at: 抓取时间
    """

    title: str
    category: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    time: str = ""
    location: str = ""
    area: str = ""
    description: str = ""
    recommendation_reason: str = ""
    tags: List[str] = field(default_factory=list)
    source_url: str = ""
    source_name: str = ""
    fetched_at: str = ""

    def to_dict(self) -> dict:
        """
        作用：
        把 Event 转成普通 dict，方便保存 CSV 或显示 dataframe。

        输入：
        self，也就是当前 Event 对象。

        输出：
        dict，其中 tags 会被转成用 / 连接的字符串。
        """
        data = asdict(self)
        data["tags"] = " / ".join(self.tags)
        return data
