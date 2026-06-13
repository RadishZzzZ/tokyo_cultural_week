"""
utils/text_utils.py

这个文件放文字清理工具。
活动标题、地点、简介经常来自网页，可能有多余空格、换行、全角空格。
这里统一做简单清理。
"""

import re


def clean_text(text: str) -> str:
    """
    作用：
    清理字符串中的多余空格、换行和全角空格。

    输入：
    text: 原始文字。

    输出：
    清理后的文字。
    """
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 160) -> str:
    """
    作用：
    把太长的简介截短，避免卡片太臃肿。

    输入：
    - text: 原始文字
    - max_length: 最大长度

    输出：
    截短后的文字。
    """
    text = clean_text(text)
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def normalize_for_dedup(text: str) -> str:
    """
    作用：
    为去重准备文本。把大小写、空格差异尽量抹平。

    输入：
    text: 原始文字。

    输出：
    适合比较的文字。
    """
    text = clean_text(text).lower()
    text = text.replace("　", " ")
    text = re.sub(r"\s+", "", text)
    return text
