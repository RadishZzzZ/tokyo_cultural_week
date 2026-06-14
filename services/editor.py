"""
services/editor.py

这个文件是“编辑层”。

它负责把 fetcher 抓到的原始活动，整理成更像文化简报的内容：
1. 清理标题和简介
2. 推断 area
3. 自动补充 tags
4. 自动生成 recommendation_reason

本版本重点：
- 推荐理由不再像程序模板
- 根据区域、类别、标题生成更自然的 newsletter 风格文案
- 仍然不调用 AI API，先用规则实现
"""

from typing import List

from config import AREA_KEYWORDS, TAG_KEYWORDS, CATEGORY_LABELS
from models import Event
from utils.date_utils import is_weekend, is_today
from utils.text_utils import clean_text, truncate_text


def guess_area(event: Event) -> str:
    """
    作用：
    根据 location、title、description 中的关键词推断区域。

    输入：
    event: 一个 Event。

    输出：
    区域文字，例如 渋谷 / 上野 / 六本木 / 東京23区全体。
    """
    if event.area:
        return clean_text(event.area)

    combined_text = f"{event.location} {event.title} {event.description}"

    for area, keywords in AREA_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in combined_text.lower():
                return area

    return "東京23区全体"


def assign_tags(event: Event) -> List[str]:
    """
    作用：
    根据类别、关键词、日期自动给活动贴标签。

    输入：
    event: 一个 Event。

    输出：
    标签列表。
    """
    tags = list(event.tags) if event.tags else []
    combined_text = f"{event.title} {event.description} {event.location} {event.category}".lower()

    category_base_tags = {
        "movies": "🎬 电影",
        "exhibitions": "🖼 展览",
        "lectures": "📚 偏知识型",
        "local_events": "🚶 可以顺路散步",
        "performing_arts": "🎭 舞台 / 表演",
        "pop_culture": "🎮 亚文化相关",
        "bookstore_events": "📚 书店活动",
        "music": "🎵 音乐",
        "other": "✨ 其他",
    }

    if event.category in category_base_tags:
        tags.append(category_base_tags[event.category])

    if event.category == "bookstore_events":
        tags.append("💬 小规模活动")

    for tag, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in combined_text:
                tags.append(tag)
                break

    if is_today(event.start_date):
        tags.append("🌙 下班后适合")

    if is_weekend(event.start_date):
        tags.append("🚶 周末适合")

    if event.start_date and event.end_date and event.start_date != event.end_date:
        tags.append("🎟 期間限定")

    if event.area:
        tags.append(event.area)

    result = []
    for tag in tags:
        if tag and tag not in result:
            result.append(tag)

    return result


def build_area_phrase(area: str) -> str:
    """
    作用：
    把 area 转成自然中文短语。

    输入：
    area: 区域名。

    输出：
    适合放进推荐理由的短语。
    """
    if not area or area == "東京23区全体":
        return "东京市内"

    return f"{area}一带"


def generate_description(event: Event) -> str:
    """
    作用：
    如果原始简介太短或为空，生成一个更自然的基础简介。

    输入：
    event: Event。

    输出：
    description 文字。
    """
    title = event.title
    area_phrase = build_area_phrase(event.area)

    if event.description and len(event.description) >= 20:
        return truncate_text(event.description, 220)

    if event.category == "exhibitions":
        return f"{title} 是本期值得留意的展览项目，适合安排在{area_phrase}散步或看展路线中。"

    if event.category == "pop_culture":
        return f"{title} 偏向视觉文化、角色文化或流行文化主题，适合作为轻松的周末目的地。"

    if event.category == "performing_arts":
        return f"{title} 是一项现场表演或传统文化活动，适合想体验东京城市日常之外另一面的观众。"

    if event.category == "local_events":
        return f"{title} 适合作为本周城市散步的一站，可以顺路感受东京不同区域的活动氛围。"

    if event.category == "bookstore_events":
        return f"{title} 适合喜欢书店、作者分享或小型 talk event 的人。"

    if event.category == "lectures":
        return f"{title} 偏知识型，适合想听讲座、了解城市文化或社会议题的人。"

    if event.category == "movies":
        return f"{title} 可以作为下班后或周末的短时间文化安排。"

    return f"{title} 是本周可以留意的东京文化活动之一。"


def generate_recommendation_reason(event: Event) -> str:
    """
    作用：
    生成更自然的文化简报式推荐理由。

    输入：
    event: 一个 Event。

    输出：
    推荐理由文字。
    """
    title_lower = event.title.lower()
    area_phrase = build_area_phrase(event.area)

    # 具体活动优先：这样卡片更像编辑挑选，而不是统一模板
    if "andrew wyeth" in title_lower:
        return "适合想看具象绘画、美国乡土风景和安静画面的人。上野路线也很好安排，适合一个人慢慢看。"

    if "group show of contemporary artists" in title_lower:
        return "偏向当代艺术群展，适合想轻量补充东京艺术现场的人。免费展览的话，也很适合作为上野散步中的一站。"

    if "ron mueck" in title_lower:
        return "六本木本期比较有存在感的展览。作品通常带有强烈身体感和现实感，适合想看一点有冲击力展览的人。"

    if "sanrio" in title_lower or "kawaii" in title_lower:
        return "比传统美术馆更轻松，适合和朋友一起去。喜欢角色文化、かわいい文化或日本流行视觉的人会更容易进入。"

    if "orb:" in title_lower or "movements of the earth" in title_lower:
        return "偏动漫与知识视觉文化的活动。适合想找一个不太沉重、又有话题性的周末去处。"

    if "geisha" in title_lower or "浅草芸者" in event.title:
        return "浅草的传统艺能活动，适合想在东京日常之外感受一点江户气息的人。和浅草散步放在一起会比较自然。"

    # 类别级别兜底
    if event.category == "exhibitions":
        if event.area == "上野":
            return "上野一带适合慢慢看展，也适合和公园、咖啡或博物馆路线一起安排。一个人去也比较舒服。"
        if event.area == "六本木":
            return "六本木的展览比较适合下班后或周末顺路安排。看完还能接夜景、书店或咖啡。"
        if event.area == "恵比寿":
            return "恵比寿路线适合摄影、影像和城市散步。适合一个人慢慢看，也适合雨天安排。"
        return f"{area_phrase}的展览选项，适合想给本周留一点审美时间的人。"

    if event.category == "pop_culture":
        return "偏轻松的流行文化活动，适合和朋友一起去，也适合作为周末顺路目的地。"

    if event.category == "performing_arts":
        return "现场表演类活动比展览更有时间感，适合想让本周安排稍微特别一点的人。"

    if event.category == "local_events":
        return "适合放进城市散步路线里，不一定要专程前往，但很适合作为顺路发现。"

    if event.category == "bookstore_events":
        if "サイン会" in event.title:
            return "适合想参加签售、近距离接触作者或创作者的书籍爱好者，也可以顺便留意这次刊行背后的作品。"
        if "トークイベント" in event.title:
            return "以作者或创作者对谈为主，适合想听现场交流、了解书中观点与创作过程的人。"
        if "刊行記念" in event.title or "出版記念" in event.title:
            return "围绕新书出版展开，可以从作者与创作者背景进入作品，也适合关注近期出版话题的人。"
        return "适合喜欢书店、作者分享和小规模交流的人。比大型活动更安静，也更容易留下思考余味。"

    if event.category == "lectures":
        return "偏知识型，适合想在工作之外补充一点社会、城市或文化议题的人。"

    if event.category == "movies":
        return "适合下班后或周末安排一场短时间文化休息。"

    return "适合作为本周东京文化生活的小入口，轻量但不敷衍。"


def enrich_event(event: Event) -> Event:
    """
    作用：
    对单个活动进行编辑增强。

    输入：
    event: 原始 Event。

    输出：
    增强后的 Event。
    """
    event.title = clean_text(event.title)
    event.location = clean_text(event.location)
    event.source_name = clean_text(event.source_name)

    event.area = guess_area(event)

    event.description = clean_text(event.description)
    event.description = generate_description(event)

    event.tags = assign_tags(event)

    if not event.recommendation_reason:
        event.recommendation_reason = generate_recommendation_reason(event)
    else:
        event.recommendation_reason = clean_text(event.recommendation_reason)

    return event


def enrich_events(events: List[Event]) -> List[Event]:
    """
    作用：
    批量增强活动。

    输入：
    events: Event 列表。

    输出：
    增强后的 Event 列表。
    """
    return [enrich_event(event) for event in events]
