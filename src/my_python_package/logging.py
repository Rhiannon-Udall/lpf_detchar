"""Implements logging for this package. Code copied (with slight modification) from `nrsur_catalog`"""

import logging
import sys
import warnings

from loguru import logger

logger.remove(0)

logger_format = "|<blue>MY-PYTHON-PACKAGE</blue>|{time:DD/MM HH:mm:ss}|{level}| <green>{message}</green> "

logger.add(
    sys.stderr,
    format=logger_format,
    colorize=True,
    level="WARNING",
)
logger.add(sys.stdout, format=logger_format, colorize=True, level="INFO")

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
