from .analyse import analyse_file, analyse_page, get_pages
from .cli import run
from .rotate import rotate
from .stats import histogram


try:
    from importlib.metadata import version, PackageNotFoundError  # type: ignore
except ImportError:  # pragma: no cover
    from importlib_metadata import version, PackageNotFoundError  # type: ignore


try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"

WINDOW_SIZE = 150

__all__ = ["analyse_file", "analyse_page", "get_pages", "run", "rotate", "histogram"]
