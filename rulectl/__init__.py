"""
Rulectl - A tool for analyzing and creating cursor rules in repositories.
"""

try:
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("rulectl")
    except PackageNotFoundError:
        # Package is not installed, read from setup.py
        import os
        import re
        setup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup.py")
        if os.path.exists(setup_path):
            with open(setup_path, "r") as f:
                content = f.read()
                match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    __version__ = match.group(1)
                else:
                    __version__ = "0.0.0"  # Fallback version
        else:
            __version__ = "0.0.0"  # Fallback version
except ImportError:
    # Python < 3.8, use pkg_resources
    try:
        import pkg_resources
        __version__ = pkg_resources.get_distribution("rulectl").version
    except Exception:
        __version__ = "0.0.0"  # Fallback version

__author__ = "Rulectl Team & Contributors" 