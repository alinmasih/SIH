"""
JPEG Validator - binary structure validation for JPEG/JFIF/EXIF images.
"""

import struct
from typing import Any, Dict, List
from forensics_platform.carving.validators.base_validator import BaseValidator, ValidationResult


class JPEGValidator(BaseValidator):
    """Validates JPEG format segments, SOF dimensions, and EOI termination."""

    def validate(self, data: bytes, start_offset: int = 0) -> ValidationResult:
        errors: List[str] = []
        details: Dict[str, Any] = {}
        score = 0

        buf = data[start_offset:]
        buf_len = len(buf)

        if buf_len < 4:
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Data too small for JPEG header"],
            )

        # Check SOI marker: FF D8
        if buf[:2] != b"\xff\xd8":
            return ValidationResult(
                is_valid=False,
                estimated_size=0,
                structure_score=0,
                footer_found=False,
                errors=["Missing SOI marker (FF D8)"],
            )

        score += 5
        offset = 2
        in_scan = False
        eoi_found = False
        sof_found = False
        app_found = False
        dqt_found = False

        # Parse segments
        while offset < buf_len - 1:
            if not in_scan:
                # Expect marker 0xFF followed by non-zero
                if buf[offset] != 0xFF:
                    # Stuffed or corrupt byte before scan
                    offset += 1
                    continue

                marker = buf[offset + 1]
                offset += 2

                # Skip fill bytes FF
                while marker == 0xFF and offset < buf_len:
                    marker = buf[offset]
                    offset += 1

                # SOI or RST markers (no payload)
                if marker == 0xD8 or 0xD0 <= marker <= 0xD7:
                    continue

                # EOI marker
                if marker == 0xD9:
                    eoi_found = True
                    break

                # Segment with length
                if offset + 2 > buf_len:
                    errors.append("Truncated segment length")
                    break

                seg_len = struct.unpack(">H", buf[offset : offset + 2])[0]
                if seg_len < 2:
                    errors.append(f"Invalid segment length {seg_len}")
                    break

                seg_data = buf[offset + 2 : offset + seg_len]
                offset += seg_len

                # APP0 - APP15
                if 0xE0 <= marker <= 0xEF:
                    app_found = True
                    if marker == 0xE0 and seg_data.startswith(b"JFIF\x00"):
                        details["format"] = "JFIF"
                    elif marker == 0xE1 and seg_data.startswith(b"Exif\x00"):
                        details["format"] = "Exif"

                # DQT (Define Quantization Table)
                elif marker == 0xDB:
                    dqt_found = True

                # SOF0 / SOF2 (Start of Frame)
                elif marker in (0xC0, 0xC2):
                    sof_found = True
                    if len(seg_data) >= 6:
                        precision = seg_data[0]
                        height = struct.unpack(">H", seg_data[1:3])[0]
                        width = struct.unpack(">H", seg_data[3:5])[0]
                        components = seg_data[5]
                        details["width"] = width
                        details["height"] = height
                        details["components"] = components
                        details["precision"] = precision

                # SOS (Start of Scan) - rest of file is entropy scan data until EOI
                elif marker == 0xDA:
                    in_scan = True

            else:
                # In scan data: look for EOI (FF D9)
                # Find next 0xFF
                ff_pos = buf.find(b"\xff", offset)
                if ff_pos == -1 or ff_pos + 1 >= buf_len:
                    break

                next_byte = buf[ff_pos + 1]
                if next_byte == 0xD9:  # EOI
                    eoi_found = True
                    offset = ff_pos + 2
                    break
                elif next_byte == 0x00 or (0xD0 <= next_byte <= 0xD7):
                    # Stuffed byte 0xFF 0x00 or restart marker
                    offset = ff_pos + 2
                else:
                    offset = ff_pos + 1

        if app_found or dqt_found:
            score += 10
        if sof_found:
            score += 10
            if details.get("width", 0) > 0 and details.get("height", 0) > 0:
                pass
            else:
                errors.append("Invalid image dimensions in SOF")
        if eoi_found:
            score += 5

        estimated_size = offset
        is_valid = score >= 15 and estimated_size > 4

        return ValidationResult(
            is_valid=is_valid,
            estimated_size=estimated_size,
            structure_score=min(score, 30),
            footer_found=eoi_found,
            details=details,
            errors=errors,
        )
