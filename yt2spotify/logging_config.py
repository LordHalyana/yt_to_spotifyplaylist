import logging
from rich.logging import RichHandler

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        RichHandler(
            rich_tracebacks=True, show_time=False, show_level=True, show_path=False
        )
    ],
)
logger = logging.getLogger("yt2spotify")
