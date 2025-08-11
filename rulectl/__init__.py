"""
Rulectl - A tool for analyzing and creating cursor rules in repositories.
"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("rulectl")
    except PackageNotFoundError:
        # Package is not installed, read from version.py
        import os
        import sys
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        sys.path.insert(0, parent_dir)
        try:
            from version import VERSION
            __version__ = VERSION
        except ImportError:
            __version__ = "0.0.0"  # Fallback version
except ImportError:
    # Python < 3.8, use pkg_resources
    try:
        import pkg_resources
        __version__ = pkg_resources.get_distribution("rulectl").version
    except Exception:
        # Try to import from version.py as last resort
        try:
            import os
            import sys
            parent_dir = os.path.dirname(os.path.dirname(__file__))
            sys.path.insert(0, parent_dir)
            from version import VERSION
            __version__ = VERSION
        except ImportError:
            __version__ = "0.0.0"  # Fallback version

__author__ = "Rulectl Team & Contributors" 