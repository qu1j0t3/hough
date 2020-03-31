from .analyse import analyse_file, analyse_page, get_pages
from .cli import run
from .rotate import rotate
from .stats import histogram


WINDOW_SIZE = 150

__version__ = "0.2.0"

__all__ = ["analyse_file", "analyse_page", "get_pages", "run", "rotate", "histogram"]
