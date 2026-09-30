# Third-Party Software Notices & Licenses

This document lists the open-source third-party software components, libraries, and tools used by the **Integrated Secure Data Sanitization & Digital Forensics Platform**, along with their respective license types and copyright notices.

---

## Direct Python Runtime Dependencies

| Library | Version / Constraint | License | Project URL / Description |
| :--- | :--- | :--- | :--- |
| **PySide6** | `>=6.6.0` | LGPLv3 / Commercial | [Qt for Python](https://www.qt.io/qt-for-python) - Official Python bindings for the Qt application framework. |
| **SQLAlchemy** | `>=2.0.0` | MIT License | [SQLAlchemy](https://www.sqlalchemy.org/) - Database Abstraction Library and Object Relational Mapper. |
| **python-magic** | `>=0.4.27` | MIT License | [python-magic](https://github.com/ahupp/python-magic) - Python interface to libmagic file type identification. |
| **Pillow** | `>=10.0.0` | HPND License | [Pillow](https://python-pillow.org/) - Python Imaging Library fork for image processing and verification. |
| **pypdf** | `>=3.17.0` | BSD-3-Clause | [pypdf](https://github.com/py-pdf/pypdf) - Pure-python PDF library capable of extracting document metadata. |
| **cryptography** | `>=41.0.0` | Apache-2.0 / BSD-3-Clause | [cryptography](https://cryptography.io/) - Cryptographic recipes and primitives for Python. |
| **psutil** | `>=5.9.0` | BSD-3-Clause | [psutil](https://github.com/giampaolo/psutil) - Cross-platform process and system utilization monitoring. |
| **PyYAML** | `>=6.0` | MIT License | [PyYAML](https://pyyaml.org/) - YAML parser and emitter for platform configuration. |
| **Jinja2** | `>=3.1.0` | BSD-3-Clause | [Jinja2](https://palletsprojects.com/p/jinja/) - Modern and designer-friendly templating language for Python. |

---

## Development, Quality Assurance & Testing Dependencies

| Library | Version / Constraint | License | Project URL / Description |
| :--- | :--- | :--- | :--- |
| **pytest** | `>=7.4.0` | MIT License | [pytest](https://pytest.org/) - Mature Python testing framework. |
| **pytest-cov** | `>=4.1.0` | MIT License | [pytest-cov](https://github.com/pytest-dev/pytest-cov) - Coverage plugin for pytest. |
| **pytest-qt** | `>=4.2.0` | MIT License | [pytest-qt](https://github.com/pytest-dev/pytest-qt) - PyTest support for PyQt and PySide applications. |
| **black** | `>=23.0.0` | MIT License | [black](https://github.com/psf/black) - Uncompromising Python code formatter. |
| **mypy** | `>=1.5.0` | MIT License | [mypy](https://mypy-lang.org/) - Optional static typing for Python. |

---

## External System Utilities & Tooling

| Component | Standard License | Purpose |
| :--- | :--- | :--- |
| **The Sleuth Kit (TSK)** | IBM Public License / CPL / GPLv2 | File system analysis tools (`mmls`, `fls`, `icat`, `fsstat`) used for forensic recovery. |
| **util-linux (`lsblk`, `wipefs`)** | GPLv2 / LGPLv2.1 | Block device enumeration and partition table inspection. |
| **GNU Coreutils (`dd`, `sync`)** | GPLv3 | Low-level disk writing, block copying, and cache flushing. |

---

## License Compliance Notice

All dependencies and libraries listed above are compatible with the distribution of this platform. In accordance with LGPLv3 requirements for PySide6, this platform dynamically links against Qt libraries, allowing end-users to swap or upgrade Qt shared library components independently.
