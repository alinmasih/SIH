"""
PDF generation and formatting module for forensic and sanitization reports.

Utilizes PySide6 (QPdfWriter, QTextDocument) for high-fidelity HTML-to-PDF
rendering, combined with pypdf for cryptographic metadata and watermark overlays.
"""

from datetime import datetime, timezone
from pathlib import Path
import os
import tempfile
from typing import Any, Dict, Optional, Union
import pypdf

from PySide6.QtCore import QMarginsF
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument


class PDFGenerator:
    """
    Converts HTML reports to professional, court-admissible PDFs with watermarking
    and forensic metadata tagging.
    """

    def __init__(self):
        self._ensure_app()

    @staticmethod
    def _ensure_app():
        """Ensure a QApplication instance exists for font and page layout metrics."""
        app = QApplication.instance()
        if app is None:
            args = ["forensics_reporter"]
            if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                args.extend(["-platform", "offscreen"])
            app = QApplication(args)
        return app

    def html_to_pdf(
        self,
        html_content: str,
        output_path: Union[str, Path],
        watermark: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Convert HTML content to a PDF file.

        Args:
            html_content: Complete HTML string with styles
            output_path: Path where output PDF should be saved
            watermark: Optional watermark text (e.g. 'CONFIDENTIAL')
            metadata: Optional PDF metadata dictionary (Title, Author, etc.)

        Returns:
            Path to the generated PDF file
        """
        self._ensure_app()
        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Temporary path if post-processing (watermark/metadata) is needed
        needs_postprocess = bool(watermark or metadata)
        if needs_postprocess:
            fd, temp_pdf = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            render_target = temp_pdf
        else:
            render_target = str(out_path)

        try:
            # 1. Setup QTextDocument
            doc = QTextDocument()
            doc.setHtml(html_content)

            # 2. Setup QPdfWriter with A4 and 15mm margins
            writer = QPdfWriter(render_target)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QMarginsF(12, 14, 12, 14),
            )
            writer.setPageLayout(layout)

            # 3. Print document to PDF writer
            doc.print_(writer)

            # 4. Post-process with pypdf if requested
            if needs_postprocess:
                self._apply_watermark_and_metadata(
                    source_pdf=render_target,
                    destination_pdf=str(out_path),
                    watermark=watermark,
                    metadata=metadata,
                )
        finally:
            if needs_postprocess and os.path.exists(render_target):
                try:
                    os.unlink(render_target)
                except OSError:
                    pass

        return out_path

    def _create_watermark_pdf(self, watermark_text: str) -> str:
        """Generate a single-page transparent watermark PDF."""
        fd, temp_wm = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        wm_html = f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }}
                .watermark-banner {{
                    margin-top: 380px;
                    text-align: center;
                    font-size: 52px;
                    font-family: Arial, sans-serif;
                    font-weight: 900;
                    color: rgba(220, 38, 38, 0.18);
                    letter-spacing: 12px;
                    transform: rotate(-30deg);
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div class="watermark-banner">{watermark_text}</div>
        </body>
        </html>
        """
        doc = QTextDocument()
        doc.setHtml(wm_html)

        writer = QPdfWriter(temp_wm)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QMarginsF(0, 0, 0, 0),
        )
        writer.setPageLayout(layout)
        doc.print_(writer)

        return temp_wm

    def _apply_watermark_and_metadata(
        self,
        source_pdf: str,
        destination_pdf: str,
        watermark: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Apply watermark overlay and document metadata using pypdf."""
        reader = pypdf.PdfReader(source_pdf)
        pdf_writer = pypdf.PdfWriter()

        wm_pdf = None
        wm_page = None
        if watermark:
            wm_pdf = self._create_watermark_pdf(watermark)
            wm_reader = pypdf.PdfReader(wm_pdf)
            if len(wm_reader.pages) > 0:
                wm_page = wm_reader.pages[0]

        try:
            for page in reader.pages:
                if wm_page:
                    page.merge_page(wm_page)
                pdf_writer.add_page(page)

            # Metadata
            pdf_meta = {
                "/Producer": "Digital Forensics Platform v1.0.0",
                "/CreationDate": datetime.now(timezone.utc).strftime("D:%Y%m%d%H%M%SZ"),
            }
            if metadata:
                if "title" in metadata:
                    pdf_meta["/Title"] = str(metadata["title"])
                if "author" in metadata:
                    pdf_meta["/Author"] = str(metadata["author"])
                if "subject" in metadata:
                    pdf_meta["/Subject"] = str(metadata["subject"])
                if "keywords" in metadata:
                    pdf_meta["/Keywords"] = str(metadata["keywords"])

            pdf_writer.add_metadata(pdf_meta)

            with open(destination_pdf, "wb") as f:
                pdf_writer.write(f)

        finally:
            if wm_pdf and os.path.exists(wm_pdf):
                try:
                    os.unlink(wm_pdf)
                except OSError:
                    pass

    def add_watermark(self, pdf_path: Union[str, Path], watermark_text: str) -> Path:
        """Add watermark to an existing PDF file."""
        path = Path(pdf_path).resolve()
        fd, temp_dest = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)

        self._apply_watermark_and_metadata(
            source_pdf=str(path),
            destination_pdf=temp_dest,
            watermark=watermark_text,
        )

        # Replace original
        os.replace(temp_dest, str(path))
        return path
