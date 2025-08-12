#!/usr/bin/env python3
"""
Setup script for Rulectl CLI tool.
"""

from setuptools import setup, find_packages
from pathlib import Path
import sys
import os

# Add parent directory to path to import version
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version import VERSION

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = ""
readme_path = this_directory / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="rulectl",
    version=VERSION,
    author="Rulectl Team",
    author_email="info@rulectl.com",
    description="A CLI tool for analyzing and creating cursor rules in repositories",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/actual-software/rulectl",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "colorama>=0.4.6",
        "pathspec>=0.11.0",
        "pyyaml>=6.0",
        "keyring>=24.3.0",  # For secure credential storage
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=1.0.0",
        ],
        "build": [
            "PyInstaller>=5.13.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rulectl=rulectl.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 