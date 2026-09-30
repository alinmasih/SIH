# Open-Source Dependencies & Integration Analysis

**Project:** Integrated Secure Data Sanitization & Digital Forensics Platform  
**Version:** 1.0  
**Date:** 2026-09-08  
**Purpose:** License compatibility, integration strategy, and capability analysis

---

## 1. EXECUTIVE SUMMARY

This document analyzes open-source projects that will be studied, integrated, or used as reference for our platform. All integrations must respect licensing requirements and clearly distinguish between our implementation and external capabilities.

### Integration Approaches

1. **Study & Learn:** Review architecture and algorithms without copying code
2. **CLI Wrapper:** Execute external tools via subprocess with proper attribution
3. **Library Binding:** Use Python bindings to external libraries
4. **Reference Implementation:** Implement our own version inspired by documented algorithms

---

## 2. THE SLEUTH KIT (TSK)

### Overview

**Website:** https://www.sleuthkit.org/  
**GitHub:** https://github.com/sleuthkit/sleuthkit  
**Current Version:** 4.12.1 (as of reference)  
**Language:** C/C++  
**License:** Common Public License 1.0 & IBM Public License 1.0

### License Analysis

**CPL 1.0 Key Terms:**
- ✓ Commercial use permitted
- ✓ Modification permitted
- ✓ Distribution permitted
- ✓ Patent grant included
- ⚠ Copyleft: modifications to TSK code must be released under CPL
- ✓ Can be used as external tool without affecting our code license

**Compatibility:** Compatible for CLI wrapper integration

### Capabilities

1. **Filesystem Analysis:**
   - NTFS, FAT, exFAT, Ext2/3/4, HFS+, ISO9660, UFS
   - Partition analysis (MBR, GPT, Apple, BSD)
   - Filesystem metadata extraction

2. **Deleted File Recovery:**
   - Unallocated space identification
   - Deleted inode recovery
   - File metadata reconstruction

3. **Timeline Analysis:**
   - File activity timelines
   - MAC (Modified, Accessed, Changed) timestamps

4. **File Extraction:**
   - Extract files by inode
   - Bulk file recovery
   - Content extraction

### Integration Strategy

**Method:** CLI Wrapper

```python
class SleuthKitWrapper:
    """
    Wrapper for The Sleuth Kit command-line tools.
    
    The Sleuth Kit is licensed under CPL 1.0.
    This wrapper executes TSK tools via subprocess.
    No TSK code is copied or modified.
    """
    
    REQUIRED_COMMANDS = ['mmls', 'fsstat', 'fls', 'icat', 'tsk_recover']
    
    def check_availability(self) -> bool:
        """Check if TSK is installed"""
        
    def get_version(self) -> str:
        """Get TSK version"""
        
    def analyze_partitions(self, image_path: str) -> List[Partition]:
        """Execute: mmls image_path"""
        
    def analyze_filesystem(self, image_path: str, offset: int) -> FilesystemInfo:
        """Execute: fsstat -o offset image_path"""
        
    def list_files(self, image_path: str, offset: int, recursive: bool = True) -> List[FileEntry]:
        """Execute: fls -o offset -r image_path"""
        
    def extract_file(self, image_path: str, offset: int, inode: int, output_path: str):
        """Execute: icat -o offset image_path inode > output_path"""
        
    def recover_deleted(self, image_path: str, offset: int, output_dir: str):
        """Execute: tsk_recover -o offset -e image_path output_dir"""
```

### Attribution Requirements

**In Reports:**
```
Filesystem analysis performed using The Sleuth Kit v4.12.1
Licensed under Common Public License 1.0
Website: https://www.sleuthkit.org/
```

**In Code:**
```python
# The Sleuth Kit integration
# The Sleuth Kit is Copyright (c) Brian Carrier
# Licensed under Common Public License 1.0
# https://www.sleuthkit.org/
```

**In Documentation:**
- Credit in THIRD_PARTY.md
- Version tracking
- Clear separation of TSK functionality from our implementation

---

## 3. AUTOPSY

### Overview

**Website:** https://www.autopsy.com/  
**GitHub:** https://github.com/sleuthkit/autopsy  
**Current Version:** 4.21.0 (as of reference)  
**Language:** Java  
**License:** Apache License 2.0

### License Analysis

**Apache 2.0 Key Terms:**
- ✓ Commercial use permitted
- ✓ Modification permitted
- ✓ Distribution permitted
- ✓ Patent grant included
- ✓ Permissive license
- ✓ No copyleft requirement
- ⚠ Must include Apache license text for any used code
- ⚠ Must state changes if code is modified

**Compatibility:** Compatible, but we won't copy code directly

### Usage Strategy

**Method:** Study Only - No Code Integration

**What We Study:**
1. Case management architecture
2. Evidence workflow design
3. UI/UX patterns for forensics
4. Report structure and content
5. Module organization

**What We Don't Do:**
- Copy Java code
- Copy UI designs verbatim
- Copy report templates verbatim
- Claim Autopsy compatibility

### Learning Points

1. **Case Management:**
   - Multi-evidence case structure
   - Tag system for file marking
   - Keyword search integration
   - Timeline view concepts

2. **UI Organization:**
   - Tree view for evidence hierarchy
   - Content viewer panel design
   - Result table organization
   - Context-aware actions

3. **Analysis Modules:**
   - Modular analysis architecture
   - Ingest module pattern
   - Progress reporting
   - Result aggregation

### Attribution

**In Documentation:**
```
Case management architecture inspired by Autopsy forensic platform
https://www.autopsy.com/
```

---

## 4. PHOTOREC / TESTDISK

### Overview

**Website:** https://www.cgsecurity.org/  
**Documentation:** https://www.cgsecurity.org/wiki/PhotoRec  
**GitHub:** https://github.com/cgsecurity/testdisk  
**Current Version:** 7.2  
**Language:** C  
**License:** GNU General Public License v2+

### License Analysis

**GPLv2+ Key Terms:**
- ✓ Commercial use permitted
- ✓ Modification permitted
- ✓ Distribution permitted
- ⚠ Strong copyleft: derived works must be GPL
- ⚠ Static linking creates derived work
- ✓ CLI execution does NOT create derived work

**Compatibility:** 
- ✗ Cannot copy/modify GPL code into our codebase (if using permissive license)
- ✓ Can execute as external tool
- ✓ Can study algorithms and reimplement independently

### Capabilities

**PhotoRec:**
1. **File Carving:**
   - 480+ file formats
   - Signature-based recovery
   - Works with damaged filesystems
   - Recovers from unallocated space

2. **Recovery Methods:**
   - Header/footer matching
   - File size validation
   - Multiple signature support per format

**TestDisk:**
1. **Partition Recovery:**
   - Partition table reconstruction
   - Boot sector repair
   - MBR/GPT recovery

### Integration Strategy

**Method:** Study + Optional CLI Wrapper + Independent Implementation

**Our Approach:**
1. **Study PhotoRec's signature database:**
   - File format signatures (publicly documented)
   - Header/footer patterns
   - Validation strategies

2. **Implement our own carving engine:**
   - Use public file format specifications
   - Implement signature matching independently
   - Create our own signature database

3. **Optional benchmark tool:**
   - Run PhotoRec separately for comparison
   - Validate our results against PhotoRec
   - Report differences

```python
class PhotoRecBenchmark:
    """
    Optional benchmark wrapper for PhotoRec.
    Used for comparison and validation only.
    
    PhotoRec is Copyright (C) Christophe GRENIER
    Licensed under GNU GPL v2+
    https://www.cgsecurity.org/wiki/PhotoRec
    """
    
    def run_photorec(self, image_path: str, output_dir: str) -> RecoveryResult:
        """Execute PhotoRec for benchmark comparison"""
        # Execute: photorec /d output_dir /cmd image_path options
```

### File Format Research

**Public Sources for Signatures:**
- File format specifications (e.g., ISO/IEC standards)
- Official format documentation (e.g., PNG specification)
- Wikipedia file format articles
- Library of Congress Digital Formats documentation
- Gary Kessler's File Signatures Table

**Our Signature Database:**
- Created from public specifications
- Independently implemented
- Not copied from PhotoRec source code

### Attribution

**In Documentation:**
```
File carving algorithms inspired by PhotoRec methodology
PhotoRec signatures used as reference for validation
PhotoRec is Copyright (C) Christophe GRENIER, licensed under GPL v2+
https://www.cgsecurity.org/wiki/PhotoRec
```

---

## 5. SCALPEL

### Overview

**GitHub:** https://github.com/sleuthkit/scalpel  
**Original Author:** Golden G. Richard III  
**Current Maintainer:** Basis Technology (part of TSK project)  
**Language:** C  
**License:** Apache License 2.0

### License Analysis

**Apache 2.0:** Permissive, see Autopsy section

### Capabilities

1. **Configurable Carving:**
   - Text-based configuration file
   - Header/footer/max size per format
   - Case-sensitive/insensitive matching

2. **Performance:**
   - Efficient pattern matching
   - Multi-threaded processing
   - Large image handling

### Integration Strategy

**Method:** Study + Optional CLI Wrapper

**Configuration File Format Study:**
```
# Scalpel configuration format (for reference)
# format  case  size  header  footer
jpg  y  10000000  \xff\xd8\xff\xe0  \xff\xd9
png  y  10000000  \x89\x50\x4e\x47  \x49\x45\x4e\x44
```

**Our Implementation:**
- JSON-based configuration (more flexible)
- Similar conceptual structure
- Extended validation rules

### Attribution

**In Documentation:**
```
Signature configuration format inspired by Scalpel
https://github.com/sleuthkit/scalpel
```

---

## 6. BULK_EXTRACTOR

### Overview

**GitHub:** https://github.com/simsong/bulk_extractor  
**Author:** Simson Garfinkel  
**Language:** C++  
**License:** MIT License

### License Analysis

**MIT License:**
- ✓ Highly permissive
- ✓ Commercial use permitted
- ✓ Modification permitted
- ✓ No copyleft
- ✓ Only requires copyright notice preservation

**Compatibility:** Fully compatible

### Capabilities

1. **Feature Extraction:**
   - Email addresses
   - URLs
   - Credit card numbers
   - Cryptocurrency addresses
   - EXIF data

2. **Scanning Methods:**
   - No filesystem required
   - Forensic path annotation
   - Multi-threaded processing

### Integration Strategy

**Method:** Optional CLI Wrapper (Future Enhancement)

**Potential Use Cases:**
- Extract metadata from carved files
- Find embedded text in images
- Identify embedded resources

```python
class BulkExtractorWrapper:
    """
    Optional wrapper for bulk_extractor.
    
    bulk_extractor is Copyright (c) Simson Garfinkel
    Licensed under MIT License
    https://github.com/simsong/bulk_extractor
    """
    pass
```

**Priority:** Low (future enhancement)

---

## 7. GUYMAGER

### Overview

**Website:** https://guymager.sourceforge.io/  
**Language:** C++/Qt  
**License:** GNU General Public License v2+

### License Analysis

**GPLv2+:** Same as PhotoRec - copyleft

### Capabilities

1. **Forensic Imaging:**
   - Raw (dd) format
   - E01 (Expert Witness) format
   - AFF (Advanced Forensic Format)
   - Hash calculation during acquisition
   - Verification

2. **Features:**
   - Multi-threaded imaging
   - Device information display
   - Progress monitoring

### Usage Strategy

**Method:** Study Only - No Integration

**What We Learn:**
1. Evidence acquisition workflow
2. Hash verification during imaging
3. Device information display
4. Progress reporting for long operations

**Our Scope:**
- We analyze existing images (not acquisition)
- Users can use Guymager separately for acquisition
- We focus on analysis, not imaging hardware

### Attribution

**In Documentation:**
```
For evidence acquisition, we recommend tools like:
- Guymager (https://guymager.sourceforge.io/)
- dc3dd
- FTK Imager

Our platform analyzes existing forensic images.
```

---

## 8. NWIPE

### Overview

**GitHub:** https://github.com/martijnvanbrummelen/nwipe  
**Language:** C  
**License:** GNU General Public License v2

### License Analysis

**GPLv2:** Copyleft

### Capabilities

1. **Sanitization Methods:**
   - DoD 5220.22-M
   - RCMP TSSIT OPS-II
   - Gutmann method
   - Random data
   - Zero fill

2. **Features:**
   - Multiple device sanitization
   - Real-time verification
   - Detailed logging
   - Device information display

### Usage Strategy

**Method:** Study + Independent Implementation

**What We Study:**
1. Device detection methods
2. Sanitization workflow
3. Verification strategies
4. Safety checks
5. Progress reporting

**Our Implementation:**
- Independent Python implementation
- Similar safety checks
- Our own verification logic
- Modern sanitization methods

### Attribution

**In Documentation:**
```
Sanitization workflow inspired by nwipe architecture
https://github.com/martijnvanbrummelen/nwipe

Our implementation is independent and includes modern
sanitization methods appropriate for different storage types.
```

---

## 9. PYTHON LIBRARIES

### 9.1 python-magic

**Purpose:** File type identification  
**PyPI:** python-magic  
**Upstream:** libmagic (file command)  
**License:** MIT License (wrapper), BSD-like (libmagic)

**Integration:**
```python
import magic

mime = magic.Magic(mime=True)
file_type = mime.from_file(filepath)
```

**Attribution:**
```
File type identification using python-magic
Wrapper: https://github.com/ahupp/python-magic
libmagic: https://www.darwinsys.com/file/
```

### 9.2 PySide6

**Purpose:** Qt GUI framework  
**License:** LGPL v3 / Commercial  
**Integration:** Direct dependency

**License Compliance:**
- ✓ Dynamic linking permitted under LGPL
- ✓ Can distribute with proprietary code
- ⚠ Must allow users to replace Qt libraries
- ✓ PyPI package satisfies LGPL requirements

### 9.3 pytsk3

**Purpose:** Python bindings for The Sleuth Kit  
**License:** Apache License 2.0  
**Integration:** Optional (alternative to CLI wrapper)

**Comparison:**

| Approach | Pros | Cons |
|----------|------|------|
| CLI Wrapper | Simple, version independent | Subprocess overhead |
| pytsk3 | Better performance | Version dependency |

**Decision:** Start with CLI wrapper, consider pytsk3 for optimization

### 9.4 Pillow (PIL)

**Purpose:** Image validation  
**License:** HPND License (permissive)  
**Integration:** Direct dependency

**Use Cases:**
- Validate recovered JPEG/PNG
- Extract EXIF data
- Verify image dimensions

### 9.5 PyPDF2 / pypdf

**Purpose:** PDF validation  
**License:** BSD-3-Clause  
**Integration:** Direct dependency

**Use Cases:**
- Validate recovered PDFs
- Extract PDF metadata
- Verify PDF structure

### 9.6 SQLAlchemy

**Purpose:** Database ORM  
**License:** MIT License  
**Integration:** Direct dependency

### 9.7 pytest

**Purpose:** Testing framework  
**License:** MIT License  
**Integration:** Development dependency

---

## 10. STANDARDS & SPECIFICATIONS

### 10.1 File Format Specifications

**Public Sources:**

1. **JPEG:**
   - ITU-T T.81 (ISO/IEC 10918-1)
   - JFIF specification
   - Public domain documentation

2. **PNG:**
   - ISO/IEC 15948:2004
   - W3C PNG Specification
   - Freely available

3. **PDF:**
   - ISO 32000-2:2020 (PDF 2.0)
   - Adobe PDF Reference
   - Public specifications

4. **ZIP:**
   - PKWARE ZIP specification
   - ISO/IEC 21320-1
   - Public documentation

5. **MP3:**
   - ISO/IEC 11172-3 (MPEG-1 Audio Layer III)
   - Public documentation

**Usage:**
- Implement validators based on public specifications
- No proprietary format reverse engineering
- Clear specification attribution

### 10.2 Sanitization Standards

**NIST SP 800-88 Rev. 1:**
- Public domain (U.S. government work)
- Guidelines for Media Sanitization
- Methods: Clear, Purge, Destroy
- Device-type specific recommendations

**Integration:**
- Follow NIST guidance
- Cite standard in documentation
- Implement recommended verification

---

## 11. INTEGRATION SUMMARY TABLE

| Component | License | Method | Attribution | Priority |
|-----------|---------|--------|-------------|----------|
| The Sleuth Kit | CPL 1.0 | CLI Wrapper | Required | High |
| Autopsy | Apache 2.0 | Study Only | Recommended | N/A |
| PhotoRec | GPL v2+ | Study + Independent | Required | Medium |
| Scalpel | Apache 2.0 | Study + Optional CLI | Recommended | Low |
| bulk_extractor | MIT | Optional CLI | Required if used | Low |
| Guymager | GPL v2+ | Study Only | Recommended | N/A |
| nwipe | GPL v2 | Study + Independent | Recommended | N/A |
| python-magic | MIT | Direct | Required | High |
| PySide6 | LGPL v3 | Direct | Required | High |
| pytsk3 | Apache 2.0 | Optional | Required if used | Medium |
| Pillow | HPND | Direct | Required | High |
| PyPDF2 | BSD-3 | Direct | Required | High |
| SQLAlchemy | MIT | Direct | Required | High |

---

## 12. LICENSE COMPATIBILITY ANALYSIS

### Our Project License Options

**Option A: MIT License**
- ✓ Compatible with all direct dependencies
- ✓ Allows commercial use
- ✓ Minimal restrictions
- ✓ Academic-friendly

**Option B: Apache 2.0**
- ✓ Compatible with all direct dependencies
- ✓ Includes patent grant
- ✓ Academic-friendly

**Option C: GPL v3**
- ✓ Compatible with GPL components
- ⚠ Would allow direct GPL code integration
- ⚠ Copyleft affects users

**Recommendation: MIT or Apache 2.0**

Rationale:
- Academic/research project
- No GPL code directly integrated
- Permissive licenses encourage adoption
- Clear separation from GPL tools

---

## 13. THIRD-PARTY ATTRIBUTION REQUIREMENTS

### Code Attribution

```python
"""
Integrated Secure Data Sanitization & Digital Forensics Platform
Copyright (c) 2026 [Your Institution/Name]
Licensed under [MIT/Apache 2.0]

This software integrates with and references the following projects:
- The Sleuth Kit (CPL 1.0): https://www.sleuthkit.org/
- PhotoRec (GPL v2+): https://www.cgsecurity.org/
- [Additional tools as used]

See THIRD_PARTY.md for complete attribution.
"""
```

### Documentation Attribution

**THIRD_PARTY.md structure:**
```markdown
# Third-Party Components

## Direct Dependencies

### PySide6
- Version: 6.x
- License: LGPL v3
- URL: https://www.qt.io/qt-for-python
- Purpose: GUI framework
- Integration: Direct dependency via PyPI

[... continue for each dependency ...]

## External Tools

### The Sleuth Kit
- Version: 4.12.1
- License: Common Public License 1.0
- URL: https://www.sleuthkit.org/
- Purpose: Filesystem analysis
- Integration: CLI wrapper (subprocess execution)
- Modifications: None (external tool)

[... continue for each tool ...]

## Algorithms & Methodologies

### File Carving Methodology
- Inspired by: PhotoRec
- Reference: https://www.cgsecurity.org/wiki/PhotoRec
- Implementation: Independent implementation based on public specifications

[... continue for each methodology ...]
```

### Report Attribution

**Forensic reports should include:**
```
Tools Used:
- Platform Version: 1.0.0
- The Sleuth Kit: 4.12.1 (filesystem analysis)
- python-magic: 0.4.27 (file type identification)
- Pillow: 10.0.0 (image validation)
```

---

## 14. COMPLIANCE CHECKLIST

### Pre-Release Checklist

- [ ] THIRD_PARTY.md created and complete
- [ ] All license texts included in licenses/ directory
- [ ] Attribution in source files
- [ ] Attribution in documentation
- [ ] Attribution in GUI About dialog
- [ ] Attribution in generated reports
- [ ] External tool version detection implemented
- [ ] Graceful degradation when external tools unavailable
- [ ] No GPL code directly copied
- [ ] No proprietary code reverse-engineered
- [ ] All file format specifications documented
- [ ] All algorithm sources documented
- [ ] License compatibility verified
- [ ] Legal review completed (if required)

---

## 15. VERSION TRACKING

### External Tool Versions

Our platform must detect and log versions of external tools:

```python
class ToolVersionManager:
    """Track versions of all external dependencies"""
    
    def detect_versions(self) -> Dict[str, str]:
        versions = {}
        
        # The Sleuth Kit
        try:
            result = subprocess.run(['mmls', '-V'], capture_output=True)
            versions['sleuthkit'] = self.parse_tsk_version(result.stdout)
        except FileNotFoundError:
            versions['sleuthkit'] = 'Not installed'
        
        # Python packages
        import PySide6
        versions['pyside6'] = PySide6.__version__
        
        # ... continue for all dependencies
        
        return versions
    
    def log_versions(self, operation_id: int):
        """Log versions to database for audit trail"""
```

**Database Storage:**
```sql
ALTER TABLE operations ADD COLUMN tool_versions TEXT;  -- JSON
```

---

## 16. FUTURE CONSIDERATIONS

### Potential Additional Integrations

1. **libbde (BitLocker Drive Encryption):**
   - License: LGPL v3+
   - Purpose: BitLocker volume access
   - Priority: Low

2. **libewf (E01 format support):**
   - License: LGPL v3+
   - Purpose: Read E01 forensic images
   - Priority: Medium

3. **afflib (AFF format support):**
   - License: BSD-like
   - Purpose: Read AFF forensic images
   - Priority: Medium

4. **hashdeep/md5deep:**
   - License: Public domain
   - Purpose: Hash calculation and verification
   - Priority: Low (Python hashlib sufficient)

### Evaluation Criteria

For any new integration:
1. License compatibility
2. Active maintenance status
3. Platform availability
4. Integration complexity
5. Performance benefits
6. Feature necessity

---

## 17. CONCLUSION

Our integration strategy balances:
- **Legal compliance:** Respecting all licenses
- **Attribution:** Giving proper credit
- **Independence:** Maintaining our own implementation
- **Interoperability:** Working with established tools
- **Transparency:** Clear documentation of dependencies

All integrations will be clearly documented, properly attributed, and legally compliant.

---

**END OF OPEN SOURCE ANALYSIS**
