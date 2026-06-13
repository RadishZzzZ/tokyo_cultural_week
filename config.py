"""
config.py

这个文件集中保存整个 App 会用到的固定设置。
这样做的好处是：以后你想改默认天数、类别名称、输出路径、区域关键词时，
不用到处找代码，只改这一个文件即可。
"""

from pathlib import Path

# 默认生成未来几天的文化简报
DEFAULT_DAYS_AHEAD = 7

# 东京时区。日期判断必须以日本时间为准。
TIMEZONE = "Asia/Tokyo"

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 输出文件夹：CSV / Markdown / ICS 会保存到这里
OUTPUT_DIR = BASE_DIR / "output"

# 日志文件夹：错误日志会保存到这里
LOG_DIR = BASE_DIR / "logs"

# 日志文件路径
LOG_FILE = LOG_DIR / "app.log"

# 网络请求的超时时间，单位：秒
REQUEST_TIMEOUT_SECONDS = 15

# User-Agent 用来告诉网站：这是一个普通 Python 学习项目在访问公开页面
USER_AGENT = (
    "TokyoCulturalWeek/0.1 "
    "(local personal Streamlit app; beginner-friendly cultural newsletter generator)"
)

# App 中使用的活动类别
CATEGORY_LABELS = {
    "movies": "🎬 电影",
    "exhibitions": "🖼 展览",
    "lectures": "📚 Talk / Lecture",
    "local_events": "🚶 地区活动",
    "performing_arts": "🎭 舞台 / 表演",
    "pop_culture": "🎮 动漫 / 游戏 / Pop Culture",
    "bookstore_events": "📚 书店活动",
    "music": "🎵 音乐 / Live",
    "other": "✨ 其他",
}

# 侧边栏区域偏好
AREA_OPTIONS = [
    "新宿",
    "渋谷",
    "上野",
    "六本木",
    "銀座",
    "丸の内",
    "吉祥寺",
    "下北沢",
    "代官山",
    "中目黒",
    "池袋",
    "恵比寿",
    "東京23区全体",
    "横浜も含める",
]

# 侧边栏氛围偏好
MOOD_OPTIONS = [
    "一个人适合",
    "下班后适合",
    "周末适合",
    "雨天适合",
    "安静",
    "热闹",
    "学术 / 思考型",
    "艺术 / 审美型",
    "城市散步型",
    "亚文化型",
]

# 根据地点文字判断区域。这里是规则式判断，未来可以换成更准确的地理编码。
AREA_KEYWORDS = {
    "新宿": ["新宿", "Shinjuku"],
    "渋谷": ["渋谷", "渋谷区", "Shibuya"],
    "上野": ["上野", "Ueno"],
    "六本木": ["六本木", "Roppongi"],
    "銀座": ["銀座", "Ginza"],
    "丸の内": ["丸の内", "Marunouchi", "東京駅", "Tokyo Station"],
    "吉祥寺": ["吉祥寺", "Kichijoji"],
    "下北沢": ["下北沢", "Shimokitazawa"],
    "代官山": ["代官山", "Daikanyama"],
    "中目黒": ["中目黒", "Nakameguro"],
    "池袋": ["池袋", "Ikebukuro"],
    "恵比寿": ["恵比寿", "Ebisu"],
    "横浜": ["横浜", "Yokohama"],
}

# 根据关键词自动贴标签
TAG_KEYWORDS = {
    "☔ 雨天适合": ["museum", "gallery", "美術館", "博物館", "映画", "cinema", "theatre", "劇場", "書店"],
    "🧠 社会科学相关": ["sociology", "社会", "policy", "政治", "経済", "公共", "lecture", "talk", "seminar", "大学"],
    "🎨 一个人适合慢慢看": ["exhibition", "gallery", "美術館", "写真", "art", "design", "展示"],
    "📚 偏知识型": ["lecture", "talk", "seminar", "book", "書店", "大学", "公開講座"],
    "🎮 亚文化相关": ["anime", "game", "manga", "comic", "アニメ", "ゲーム", "漫画"],
    "🎬 电影": ["movie", "film", "cinema", "映画"],
    "🖼 展览": ["exhibition", "gallery", "museum", "美術館", "博物館", "展示", "展"],
    "🎵 音乐": ["music", "live", "jazz", "音楽", "ライブ"],
}

# 页面板块名称
SECTIONS = {
    "tonight": "🌙 今晚 / 下班后可以去",
    "exhibitions": "🖼 本周展览",
    "films": "🎬 本周电影",
    "lectures": "📚 Talk / Lecture",
    "weekend_walk": "🚶 周末散步顺路活动",
    "editors_pick": "⭐ 编辑推荐",
}

# 每个板块最多显示几张卡片
MAX_EVENTS_PER_SECTION = 5
