"""
utils/output_utils.py

这个文件负责把活动保存为 CSV、Markdown 和 ICS。
同时也提供给 Streamlit 下载按钮使用的字符串内容。
"""

import csv
import traceback
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from config import OUTPUT_DIR, SECTIONS
from models import Event
from utils.date_utils import format_datetime_for_filename, now_tokyo


CSV_FIELDS = [
    "title",
    "category",
    "start_date",
    "end_date",
    "time",
    "location",
    "area",
    "description",
    "recommendation_reason",
    "tags",
    "source_url",
    "source_name",
    "fetched_at",
]


def ensure_output_dir() -> None:
    """
    作用：
    确保 output 文件夹存在。

    输入：
    无。

    输出：
    无。
    """
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        print("创建 output 文件夹失败。")
        traceback.print_exc()
        raise


def events_to_csv_text(events: List[Event]) -> str:
    """
    作用：
    把活动列表转换成 CSV 文字，供 Streamlit 下载按钮使用。

    输入：
    events: Event 列表。

    输出：
    CSV 格式字符串。
    """
    try:
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_dict())
        return output.getvalue()

    except Exception:
        print("生成 CSV 文字失败。")
        traceback.print_exc()
        raise


def save_csv(events: List[Event]) -> Path:
    """
    作用：
    保存 CSV 文件到 output 文件夹。

    输入：
    events: Event 列表。

    输出：
    保存后的文件路径。
    """
    try:
        ensure_output_dir()
        path = OUTPUT_DIR / f"tokyo_cultural_week_{format_datetime_for_filename()}.csv"
        csv_text = events_to_csv_text(events)
        path.write_text(csv_text, encoding="utf-8-sig")
        return path

    except Exception:
        print("CSV 保存失败。")
        traceback.print_exc()
        raise


def sections_to_markdown(sections: Dict[str, List[Event]]) -> str:
    """
    作用：
    把分板块后的活动转换成 Markdown 简报。

    输入：
    sections: key 是 section id，value 是 Event 列表。

    输出：
    Markdown 字符串。
    """
    try:
        lines = []
        lines.append("# Tokyo Cultural Week｜东京未来一周文化生活简报")
        lines.append("")
        lines.append(f"生成时间：{now_tokyo().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for section_key, section_title in SECTIONS.items():
            lines.append(f"## {section_title}")
            lines.append("")

            section_events = sections.get(section_key, [])
            if not section_events:
                lines.append("本板块暂时没有抓到合适活动。")
                lines.append("")
                continue

            for event in section_events:
                date_text = event.start_date or "日期不明"
                if event.end_date and event.end_date != event.start_date:
                    date_text = f"{event.start_date} ～ {event.end_date}"

                lines.append(f"### {event.title}")
                lines.append(f"- 日期：{date_text}")
                lines.append(f"- 时间：{event.time or '未注明'}")
                lines.append(f"- 地点：{event.location or '未注明'}｜{event.area or '区域不明'}")
                lines.append(f"- 简介：{event.description or '暂无简介'}")
                lines.append(f"- 推荐理由：{event.recommendation_reason or '暂无推荐理由'}")
                lines.append(f"- 标签：{' / '.join(event.tags) if event.tags else '暂无标签'}")
                lines.append(f"- 来源：[{event.source_name}]({event.source_url})" if event.source_url else f"- 来源：{event.source_name}")
                lines.append("")

        return "\n".join(lines)

    except Exception:
        print("生成 Markdown 文字失败。")
        traceback.print_exc()
        raise


def save_markdown(sections: Dict[str, List[Event]]) -> Path:
    """
    作用：
    保存 Markdown 文件到 output 文件夹。

    输入：
    sections: 分板块后的活动。

    输出：
    保存后的文件路径。
    """
    try:
        ensure_output_dir()
        path = OUTPUT_DIR / f"tokyo_cultural_week_{format_datetime_for_filename()}.md"
        md_text = sections_to_markdown(sections)
        path.write_text(md_text, encoding="utf-8")
        return path

    except Exception:
        print("Markdown 保存失败。")
        traceback.print_exc()
        raise


def escape_ics_text(text: str) -> str:
    """
    作用：
    转义 ICS 文件中的特殊字符。

    输入：
    text: 原始文字。

    输出：
    转义后的文字。
    """
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def events_to_ics_text(events: List[Event]) -> str:
    """
    作用：
    把活动转换成 ICS 日历文件内容。

    输入：
    events: Event 列表。

    输出：
    ICS 格式字符串。

    规则：
    - 只写入有明确 start_date 的活动。
    - 没有具体时间时，作为全天活动。
    """
    try:
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Tokyo Cultural Week//Local Streamlit App//CN",
            "CALSCALE:GREGORIAN",
        ]

        generated_at = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        for index, event in enumerate(events):
            if not event.start_date:
                continue

            uid = f"tokyo-cultural-week-{index}-{event.start_date}@local"
            description = (
                f"{event.description}\n\n"
                f"推荐理由：{event.recommendation_reason}\n"
                f"来源：{event.source_url}"
            )

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{generated_at}")
            lines.append(f"SUMMARY:{escape_ics_text(event.title)}")
            lines.append(f"LOCATION:{escape_ics_text(event.location)}")
            lines.append(f"DESCRIPTION:{escape_ics_text(description)}")

            if event.time:
                # 第一版不强行解析复杂时间，避免错误。
                # 有日期但时间不稳定时，仍按全天事件写入。
                lines.append(f"DTSTART;VALUE=DATE:{event.start_date.replace('-', '')}")
            else:
                lines.append(f"DTSTART;VALUE=DATE:{event.start_date.replace('-', '')}")

            if event.end_date:
                lines.append(f"DTEND;VALUE=DATE:{event.end_date.replace('-', '')}")
            else:
                lines.append(f"DTEND;VALUE=DATE:{event.start_date.replace('-', '')}")

            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    except Exception:
        print("生成 ICS 文字失败。")
        traceback.print_exc()
        raise


def save_ics(events: List[Event]) -> Path:
    """
    作用：
    保存 ICS 文件到 output 文件夹。

    输入：
    events: Event 列表。

    输出：
    保存后的文件路径。
    """
    try:
        ensure_output_dir()
        path = OUTPUT_DIR / f"tokyo_cultural_week_{format_datetime_for_filename()}.ics"
        ics_text = events_to_ics_text(events)
        path.write_text(ics_text, encoding="utf-8")
        return path

    except Exception:
        print("ICS 保存失败。")
        traceback.print_exc()
        raise
