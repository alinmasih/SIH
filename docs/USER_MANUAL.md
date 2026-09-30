# Forensic Platform - Comprehensive User Manual

**Version:** 1.0.0  
**Target Audience:** Digital Forensic Investigators, Law Enforcement Technicians, Incident Responders, Compliance & Information Security Officers.

---

## Table of Contents
1. [Introduction & Core Philosophy](#1-introduction--core-philosophy)
2. [Launching the Platform](#2-launching-the-platform)
3. [User Interface Overview](#3-user-interface-overview)
4. [Case Management](#4-case-management)
5. [Evidence Acquisition & Management](#5-evidence-acquisition--management)
6. [File Recovery (Filesystem Analysis)](#6-file-recovery-filesystem-analysis)
7. [File Carving Engine (Raw Media Scanning)](#7-file-carving-engine-raw-media-scanning)
8. [Drive Sanitization (NIST SP 800-88 / DoD)](#8-drive-sanitization-nist-sp-800-88--dod)
9. [Secure File Eraser](#9-secure-file-eraser)
10. [Cryptographic Audit Log Explorer](#10-cryptographic-audit-log-explorer)
11. [Forensic Reporting & Sanitization Certificates](#11-forensic-reporting--sanitization-certificates)
12. [Troubleshooting & FAQs](#12-troubleshooting--faqs)

---

## 1. Introduction & Core Philosophy

The **Integrated Secure Data Sanitization & Digital Forensics Platform** is an enterprise-grade desktop environment built to handle the end-to-end lifecycle of digital media investigations and compliant media decommissioning.

### Key Capabilities
- **Forensic Integrity:** Strict read-only evidence access with automated SHA-256 and MD5 integrity verification.
- **Deep Signature Carving:** Recovers deleted, orphaned, and fragmented files from unallocated space without relying on filesystem metadata.
- **Standards-Compliant Sanitization:** Certified NIST SP 800-88 Rev 1 (Clear / Purge) and DoD 5220.22-M overwriting with statistical LBA sampling verification.
- **Cryptographic Audit Trail:** Immutable, SHA-256 hash-chained event logging ensuring court-admissible chain of custody and tamper detection.
- **Simulation Mode Interlocks:** Prevents accidental wiping of host drives by default unless explicitly configured with confirmation counters.

---

## 2. Launching the Platform

### Quick Launch (Virtual Environment)
To launch the graphical interface from the repository root:
```bash
# Activate virtual environment
source venv/bin/activate

# Launch via convenience launcher
python3 scripts/launch_gui.py

# Or launch as a Python module
python3 -m forensics_platform
```

### Simulation Mode vs. Production Mode
- **Simulation Mode (Default):** All drive wiping operations run in virtual memory and safe simulation loops. Destructive write operations to physical host disks are strictly blocked.
- **Production Mode:** Requires root privileges (`sudo`). Enables raw block device writes (`/dev/sdX`, `/dev/nvmeX`). System disks and mounted partitions are permanently locked by safety interlocks.

---

## 3. User Interface Overview

The interface consists of three primary regions:
1. **Sidebar Navigation (Left):** Access to all 10 core views:
   - 📊 **Dashboard:** Real-time platform metrics, recent cases, and quick shortcuts.
   - 📁 **Cases:** Create, filter, inspect, and close investigation cases.
   - 🗂️ **Evidence:** Register disk images, verify hash baselines, and review chain of custody.
   - 🔍 **File Recovery:** Browse partition tables and recover deleted files from filesystems.
   - 🧩 **File Carving:** Deep header/footer signature scanning across raw images.
   - 💾 **Drive Eraser:** NIST SP 800-88 compliant drive sanitization.
   - 🗑️ **File Eraser:** Cryptographic shredding and metadata scrubbing for files and folders.
   - 📋 **Audit Logs:** Real-time tamper-evident audit log ledger.
   - 📄 **Reports:** Generate, preview, and verify court-admissible PDF/HTML reports.
   - ⚙️ **Settings:** Platform preferences and external tool paths.
2. **Theme Switcher (Bottom Left):** Switch between High-Contrast Dark Theme (default) and Clean Light Theme at runtime.
3. **Content Area (Center/Right):** Dynamic stacked workspace displaying active module controls, tables, and progress bars.

---

## 4. Case Management

Every forensic operation and sanitization process must be bound to an authorized Case to preserve legal accountability.

### Creating a New Case
1. Navigate to **Cases** or click **New Case** on the Dashboard.
2. Click **+ New Case**.
3. Enter:
   - **Case Number:** Unique agency identifier (e.g., `CASE-2026-CRIM-042`).
   - **Case Title:** Descriptive name of the matter.
   - **Lead Investigator:** Name or badge number of examiner.
   - **Description:** Scope, authority, and background details.
4. Click **Create Case**. The platform provisions dedicated case directories on disk and records a cryptographically signed event in the audit trail.

---

## 5. Evidence Acquisition & Management

### Registering Seized Evidence
1. Navigate to **Evidence** and click **+ Register Evidence**.
2. Select the **Associated Case**.
3. Choose the **Source Type**: `Disk Image (.dd, .raw, .img)`, `E01 Expert Witness`, `Physical Drive`, or `Logical Filesystem`.
4. Specify the path to the evidence file.
5. Provide device model, serial number, and acquisition notes.
6. Click **Register Evidence**. The background `HashWorker` calculates the dual SHA-256 and MD5 cryptographic baseline.

### Integrity Verification
To prove evidence has remained unaltered:
1. Select the evidence item from the Evidence table.
2. Click **Verify Integrity**.
3. The platform re-reads the entire raw image, computes a new SHA-256 hash, and compares it with the baseline recorded at acquisition time.
4. Verification status (Pass/Fail) is logged in the immutable audit ledger.

---

## 6. File Recovery (Filesystem Analysis)

File Recovery parses intact or damaged filesystem structures (FAT32, NTFS, EXT4, exFAT) using SleuthKit integration.

1. Navigate to **File Recovery**.
2. Select the evidence image and partition.
3. Click **Scan Filesystem**.
4. Browse recovered directories, inspect deletion flags, and view timestamps (`MACB`: Modified, Accessed, Created, Born).
5. Select deleted files and click **Export Recovered Files** to export them into the case recovery folder.

---

## 7. File Carving Engine (Raw Media Scanning)

When filesystems are formatted, corrupted, or wiped, file carving scans raw disk sectors for distinct binary file signatures (magic bytes).

### Carving Workflow
1. Navigate to **File Carving**.
2. Select the **Evidence Image** or raw device.
3. Select target formats:
   - `JPEG` (EXIF validation, markers `FF D8 ... FF D9`)
   - `PNG` (IHDR, IDAT chunks, CRC-32 checksum verification)
   - `PDF` (Version check, xref table, and `%%EOF` marker)
   - `ZIP` / `DOCX` / `XLSX` (PK archive headers and central directory parsing)
4. Choose **Sector Alignment** (default 512 bytes for high performance) or **Byte-by-Byte** for deep carving.
5. Set minimum **Confidence Threshold** (e.g., 60%).
6. Click **Start Carving Engine**.
7. Carved files are automatically validated, assigned confidence scores, SHA-256 hashed, and stored in `cases/<case_id>/carved/`.

---

## 8. Drive Sanitization (NIST SP 800-88 / DoD)

### Safety Interlocks
The platform incorporates non-bypassable safety mechanisms:
- **System Disk Lock:** The drive hosting `/`, `/boot`, or swap is permanently locked against erasure.
- **Mounted Partition Lock:** Any media with mounted filesystems cannot be erased until unmounted.
- **Triple Confirmation:** Requires explicit confirmation dialogs before invoking destructive commands.

### Supported Sanitization Standards
- **NIST SP 800-88 Rev 1 Clear:** Single pass overwriting with fixed byte patterns (zeros) followed by verification.
- **NIST SP 800-88 Rev 1 Purge:** Cryptographic sanitize or multi-pass overwrite rendering data unrecoverable even with laboratory techniques.
- **DoD 5220.22-M:** 3-pass overwrite (Pass 1: zeros, Pass 2: ones, Pass 3: pseudo-random data).

### Verification & Certification
Upon completion of the wipe, the **VerificationEngine** performs statistical LBA sampling across the drive to prove zero plaintext remnants exist. An official **NIST SP 800-88 Certificate of Sanitization** is generated automatically.

---

## 9. Secure File Eraser

For surgical data destruction of individual files or directory trees:
1. Navigate to **File Eraser**.
2. Click **Add Files** or **Add Directory**.
3. Choose the shredding method:
   - `DoD 5220.22-M` (3 passes)
   - `Gutmann` (35 passes)
   - `Zero Overwrite` (1 pass)
4. Verify **Metadata Scrubbing** is enabled (renames file to random characters, modifies timestamps, truncates length before unlinking).
5. Click **Eradicate Selected**.

---

## 10. Cryptographic Audit Log Explorer

The Audit Log maintains an unbroken cryptographic chain of custody:
- Every action (user login, case creation, hash calculation, file carve, drive wipe) generates a SHA-256 record hash chained to the preceding event:
  $$\text{Hash}_n = \text{SHA256}(\text{Timestamp} \parallel \text{User} \parallel \text{EventType} \parallel \text{EventData} \parallel \text{Hash}_{n-1})$$
- Click **Verify Hash Chain Integrity** at any time to mathematically verify all events. If an attacker tampers with a database row, the chain breaks and the exact modified record is flagged immediately.

---

## 11. Forensic Reporting & Sanitization Certificates

The platform produces court-admissible reports in multiple formats:
- **PDF Reports:** Official typography, agency headers, cryptographic verification seals, evidence tables, and signature blocks.
- **Interactive HTML Reports:** Standalone responsive dossiers with searchable tables.
- **JSON & CSV Exports:** Machine-readable datasets for ingestion into court databases, SIEMs, or eDiscovery platforms.

### Verifying a Report File
To verify that an exported PDF or HTML document has not been altered:
1. Navigate to **Reports**.
2. Select the report in the table.
3. Click **Verify Cryptographic Seal**. The platform recalculates the document's SHA-256 checksum and compares it against the audit ledger.

---

## 12. Troubleshooting & FAQs

**Q: Why are physical drives grayed out in Drive Eraser?**  
*A:* In Simulation Mode, physical drives cannot be altered. To sanitize physical drives, configure `simulation_mode: false` in `config.yaml` and execute the platform with root permissions (`sudo`).

**Q: Can carved files be corrupted?**  
*A:* Yes. If unallocated clusters were partially overwritten prior to acquisition, carved files may be fragmented. Review the **Confidence Score** in the carving view; scores above 80% indicate fully intact structures with verified headers, footers, and checksums.

**Q: Where are case files saved?**  
*A:* Default storage is located in `~/.local/share/forensics-platform/cases/` or the path defined in your `config.yaml`.
