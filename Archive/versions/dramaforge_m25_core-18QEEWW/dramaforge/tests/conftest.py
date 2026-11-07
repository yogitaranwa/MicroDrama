"""Compatibility for the legacy ViMax suite on Python 3.10 (m19): the
project targets >=3.12, where tomllib is stdlib. Shim it with tomli so the
legacy tests exercise the same code paths on 3.10."""
import sys

if "tomllib" not in sys.modules:
    try:
        import tomllib  # noqa: F401
    except ModuleNotFoundError:
        import tomli
        sys.modules["tomllib"] = tomli
