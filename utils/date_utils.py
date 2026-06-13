"""
utils/date_utils.py

这个文件处理日期相关逻辑。
本项目必须按 Asia/Tokyo 判断“今天”和“未来 7 天”。
如果活动日期范围和目标时间范围有重叠，就保留。
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import traceback
import dateparser
from config import TIMEZONE


def now_tokyo() -> datetime:
    """
    作用：
    获取当前东京时间。

    输入：
    无。

    输出：
    datetime 对象，带 Asia/Tokyo 时区。
    """
    return datetime.now(ZoneInfo(TIMEZONE))


def today_tokyo() -> date:
    """
    作用：
    获取当前东京日期。

    输入：
    无。

    输出：
    date 对象。
    """
    return now_tokyo().date()


def format_datetime_for_filename() -> str:
    """
    作用：
    生成适合放进文件名的时间字符串。

    输入：
    无。

    输出：
    例如 20260511_213000。
    """
    return now_tokyo().strftime("%Y%m%d_%H%M%S")


def parse_date_to_iso(raw_text: str) -> str | None:
    """
    作用：
    尝试把网页或 RSS 里的日期文字解析成 YYYY-MM-DD。

    输入：
    raw_text: 原始日期文字，比如 'May 12, 2026' 或 '2026-05-12'。

    输出：
    成功时返回 YYYY-MM-DD；失败时返回 None。

    注意：
    如果完全没有明确日期，第一版会丢弃该活动或放到日期不明。
    当前项目为了保证“未来 7 天”的准确性，collector 会默认丢弃日期不明活动。
    """
    try:
        if not raw_text:
            return None

        parsed = dateparser.parse(
            raw_text,
            settings={
                "TIMEZONE": TIMEZONE,
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DATES_FROM": "future",
                "DATE_ORDER": "YMD",
            },
        )

        if parsed is None:
            return None

        return parsed.astimezone(ZoneInfo(TIMEZONE)).date().isoformat()

    except Exception:
        print(f"日期解析失败：{raw_text}")
        traceback.print_exc()
        return None


def iso_to_date(iso_text: str | None) -> date | None:
    """
    作用：
    把 YYYY-MM-DD 转成 date 对象。

    输入：
    iso_text: 日期字符串。

    输出：
    date 对象；失败时返回 None。
    """
    try:
        if not iso_text:
            return None
        return datetime.strptime(iso_text, "%Y-%m-%d").date()
    except Exception:
        print(f"ISO 日期转换失败：{iso_text}")
        traceback.print_exc()
        return None


def date_range_overlaps(start_date: str | None, end_date: str | None, days_ahead: int) -> bool:
    """
    作用：
    判断活动日期范围是否和“今天到未来 N 天”有重叠。

    输入：
    - start_date: 活动开始日期，YYYY-MM-DD 或 None
    - end_date: 活动结束日期，YYYY-MM-DD 或 None
    - days_ahead: 从今天起向后看几天

    输出：
    True 表示保留；False 表示不保留。

    规则：
    - 没有 start_date 的活动，第一版不保留，因为无法判断是否在未来 7 天内。
    - 有 start_date 但没有 end_date，就当作单日活动。
    - 有日期范围时，只要和目标范围重叠就保留。
    """
    try:
        event_start = iso_to_date(start_date)
        if event_start is None:
            return False

        event_end = iso_to_date(end_date) if end_date else event_start
        if event_end is None:
            event_end = event_start

        target_start = today_tokyo()
        target_end = target_start + timedelta(days=days_ahead)

        return event_start <= target_end and event_end >= target_start

    except Exception:
        print("日期范围判断失败。")
        traceback.print_exc()
        return False


def is_weekend(iso_text: str | None) -> bool:
    """
    作用：
    判断某个日期是否是周六或周日。

    输入：
    iso_text: YYYY-MM-DD。

    输出：
    True / False。
    """
    d = iso_to_date(iso_text)
    if d is None:
        return False
    return d.weekday() >= 5


def is_today(iso_text: str | None) -> bool:
    """
    作用：
    判断活动是否是今天。

    输入：
    iso_text: YYYY-MM-DD。

    输出：
    True / False。
    """
    d = iso_to_date(iso_text)
    if d is None:
        return False
    return d == today_tokyo()
