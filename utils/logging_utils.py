"""
utils/logging_utils.py

这个文件负责设置日志系统。
日志会同时输出到：
1. 终端
2. logs/app.log

这样运行出错时，你既能在终端看到错误，也能把 logs/app.log 发回来排查。
"""

import logging
import sys
import traceback
from config import LOG_DIR, LOG_FILE


def setup_logger() -> logging.Logger:
    """
    作用：
    创建并返回一个 logger。

    输入：
    无。

    输出：
    logging.Logger 对象。
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("tokyo_cultural_week")
        logger.setLevel(logging.INFO)

        # 避免 Streamlit 每次刷新页面时重复添加 handler
        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    except Exception:
        print("日志系统初始化失败。下面是完整错误：")
        traceback.print_exc()
        raise


def log_exception(logger: logging.Logger, message: str) -> None:
    """
    作用：
    打印完整 traceback，并写入日志。

    输入：
    - logger: 日志对象
    - message: 想显示的错误说明

    输出：
    无。
    """
    print(message)
    traceback.print_exc()
    logger.exception(message)
