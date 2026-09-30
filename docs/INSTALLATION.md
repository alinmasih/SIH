# Forensic Platform - Installation & Deployment Guide

**Version:** 1.0.0  
**Target Platform:** Linux (Ubuntu 22.04 / 24.04 LTS, Debian 12, Fedora 39+, Arch Linux).

---

## 1. System Requirements

### Minimum Hardware
- **CPU:** 64-bit x86_64 or ARM64 Dual-Core Processor (2.0 GHz+).
- **RAM:** 4 GB RAM (8 GB+ recommended for carving disk images > 50 GB).
- **Storage:** 500 MB free disk space for platform installation; additional high-speed storage for forensic disk images and recovery exports.
- **Display:** 1280 x 800 minimum resolution (1920 x 1080 recommended).

### Software Environment
- **Operating System:** Linux (Kernel 5.15 or newer).
- **Python:** Version 3.10, 3.11, 3.12, 3.13, or 3.14.
- **Display Server:** X11 or Wayland (XWayland supported).

---

## 2. System Dependencies

Before setting up the Python virtual environment, ensure required system packages and forensic libraries are installed.

### Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    sleuthkit \
    libgl1-mesa-glx \
    libegl1 \
    libxkbcommon-x11-0 \
    libfontconfig1 \
    libdbus-1-3
```

### Fedora:
```bash
sudo dnf install -y \
    python3 \
    python3-pip \
    sleuthkit \
    mesa-libGL \
    libxkbcommon-x11 \
    fontconfig
```

### Arch Linux:
```bash
sudo pacman -S --needed \
    python \
    python-pip \
    sleuthkit \
    mesa \
    libxkbcommon-x11 \
    fontconfig
```

---

## 3. Automated Installation (Recommended)

The platform includes an automated setup script that creates the virtual environment, installs Python wheels, initializes default configuration schemas, and verifies tests.

```bash
# Clone or navigate to the repository directory
cd /path/to/sih

# Grant execution rights and run setup
chmod +x setup.sh
./setup.sh
```

---

## 4. Manual Installation

If you prefer configuring the environment manually:

### Step 1: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Python Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

### Step 3: Verify Installation
```bash
python3 scripts/verify_phase8.py
```

---

## 5. Launching the Application

### Graphical User Interface (GUI)
```bash
# With virtual environment activated:
python3 scripts/launch_gui.py

# Or run module directly:
python3 -m forensics_platform
```

### Headless / Automated Verification
When running in automated CI pipelines or headless servers without a monitor:
```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/ -v
```

---

## 6. Desktop Integration (.desktop Entry)

To add the Forensic Platform to your Linux application launcher:
```bash
cp forensics-platform.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

---

## 7. Permissions for Drive Sanitization

In production environments, sanitizing physical block devices (`/dev/sdX`) requires raw device write access:
- Run the platform with administrative privileges:
  ```bash
  sudo $(which python3) scripts/launch_gui.py
  ```
- Alternatively, configure `udev` rules to grant a dedicated `forensics` user group access to target forensic drive bays.
