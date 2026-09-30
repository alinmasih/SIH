# Platform Security Model & Assurance Architecture

**Version:** 1.0.0  
**Status:** Certified Architecture & Threat Model

---

## 1. Threat Model & Trust Assumptions

The Forensic Platform is designed to operate in high-integrity environments such as digital forensics laboratories, law enforcement evidence rooms, and corporate incident response centers.

### Assumed Trust Boundaries
1. **Host Environment:** The host operating system is assumed to be free of kernel-level rootkits or compromised runtime interpreters.
2. **Physical Security:** Evidence drives and local storage are within an authorized physical or logical boundary.
3. **Auditor Accountability:** Individual operators are authenticated by the local operating system or enterprise identity provider.

### Primary Threat Mitigations
- **Accidental Self-Destruction:** Accidental wiping of host OS drives, partition boot sectors, or critical system binaries.
- **Evidence Contamination:** Accidental modification of raw forensic disk images during acquisition or examination.
- **Audit Log Tampering:** Malicious alteration of investigation records, examiner names, or case timestamps by unauthorized parties.
- **Arbitrary File Traversal:** Directory traversal attacks aimed at unauthorized file deletion (`../../etc/shadow`).

---

## 2. Privilege Separation & Execution Model

The platform enforces strict privilege boundaries based on the operation:

| Component / Task | Minimum Required Privilege | Risk Profile | Defense Controls |
| :--- | :--- | :--- | :--- |
| **Case & Evidence Management** | Standard User | Low | Database foreign keys, isolated directories. |
| **File Recovery & Signature Carving** | Standard User | Zero (Read-Only) | All evidence files are opened in strict `rb` mode; no write handles are acquired. |
| **Forensic Report Generation** | Standard User | Low | Template sandboxing, strict output path validation. |
| **File Shredding (User Files)** | Standard User | Medium | Path canonicalization; system directories blocked. |
| **Physical Drive Sanitization** | Root (`CAP_SYS_RAWIO`) | High | System disk locks, mounted media checks, triple confirmation dialogs. |

---

## 3. Defense-in-Depth Mechanisms

### A. Non-Bypassable Drive Safety Interlocks
Before allowing any block-level overwrite command:
1. The platform executes `lsblk` and `/proc/mounts` inspection to detect the root filesystem mount (`/`), boot partition (`/boot`), EFI partition, and active swap spaces.
2. If the target device matches any host partition or its parent disk, execution is immediately aborted with a critical safety violation.
3. If the target media has any mounted partitions, the operation is blocked until explicitly unmounted.
4. The user must provide a confirmation counter matching the required safety threshold (3 consecutive confirmations).

### B. Path Traversal & Protected Path Defense
In the `FileEraser` module:
- All target paths are resolved to their canonical absolute paths using `Path.resolve()` to neutralize relative path traversal (`..` and symbolic links).
- Paths are checked against the protected directory registry:
  - `/`, `/etc`, `/bin`, `/sbin`, `/usr`, `/boot`, `/lib`, `/dev`, `/sys`, `/proc`, `/var`
- Target paths falling within protected trees are immediately rejected.

### C. Cryptographic Audit Hash Chain (ISO/IEC 27037 Compliance)
To satisfy legal admissibility requirements under the **Federal Rules of Evidence (Rule 901/902)**:
- Every event is linked via a mathematical SHA-256 blockchain ledger:
  $$\text{Hash}_n = \text{SHA256}(\text{Timestamp} \parallel \text{User} \parallel \text{EventType} \parallel \text{EventData} \parallel \text{Hash}_{n-1})$$
- Modifying, inserting, or deleting any audit row breaks the hash chain for all subsequent entries.
- The `AuditLogger.verify_integrity()` routine mathematically validates the entire chain and pinpoints the exact record where tampering occurred.

---

## 4. Cryptographic Standards

- **Hashing Algorithms:** NIST FIPS 180-4 SHA-256 (Primary) and MD5 (Legacy validation only).
- **Dual Baseline Verification:** Evidence images are hashed using both SHA-256 and MD5 simultaneously during acquisition to guard against algorithmic collisions and ensure interoperability with legacy forensic suites (EnCase, FTK).
- **RNG for Shredding:** Pseudo-random overwrite passes utilize cryptographically secure randomness via `secrets.token_bytes()` or OS `/dev/urandom`.

---

## 5. Vulnerability Disclosure & Reporting

If you identify a potential security vulnerability in this platform:
1. Please do not disclose vulnerabilities publicly via public GitHub issues.
2. Submit a detailed report including reproduction steps and impacted versions to the security coordinator.
3. Security patches are prioritized and verified using our automated integration test suite prior to release.
