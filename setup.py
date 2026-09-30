"""
Setup configuration for Forensics Platform.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from version.py
version_file = Path(__file__).parent / "src" / "forensics_platform" / "version.py"
version_dict = {}
with open(version_file) as f:
    exec(f.read(), version_dict)

VERSION = version_dict['VERSION']

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="forensics-platform",
    version=VERSION,
    description="Integrated Secure Data Sanitization & Digital Forensics Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Research & Forensic Engineering Team",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "PySide6>=6.6.0",
        "SQLAlchemy>=2.0.0",
        "python-magic>=0.4.27",
        "Pillow>=10.0.0",
        "pypdf>=3.17.0",
        "cryptography>=41.0.0",
        "psutil>=5.9.0",
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-qt>=4.2.0",
            "pylint>=3.0.0",
            "black>=23.0.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "forensics-platform=forensics_platform.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Security",
        "Topic :: System :: Filesystems",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    project_urls={
        "Documentation": "https://github.com/yourusername/forensics-platform",
        "Source": "https://github.com/yourusername/forensics-platform",
    },
)
