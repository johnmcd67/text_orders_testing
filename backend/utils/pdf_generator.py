"""
PDF Generator Utility

Generates PDF documents from markdown content for failure summary reports.
Uses fpdf2 library for pure Python PDF generation with no system dependencies.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
from fpdf import FPDF


class FailureSummaryPdfGenerator(FPDF):
    """PDF generator specifically for failure summary reports."""

    # Color definitions (RGB)
    COLOR_PRIMARY = (30, 58, 138)      # Dark blue
    COLOR_HEADER_BG = (243, 244, 246)  # Light gray
    COLOR_TEXT = (55, 65, 81)          # Dark gray
    COLOR_WARNING = (245, 158, 11)     # Amber
    COLOR_MUTED = (107, 114, 128)      # Medium gray

    def __init__(self, job_id: int, failure_count: int, generated_at: Optional[Union[datetime, str]] = None):
        super().__init__()
        self.job_id = job_id
        self.failure_count = failure_count

        # Handle generated_at - might be string from database
        if generated_at is None:
            self.generated_at = datetime.utcnow()
        elif isinstance(generated_at, str):
            # Parse ISO format string from database
            try:
                self.generated_at = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            except ValueError:
                self.generated_at = datetime.utcnow()
        else:
            self.generated_at = generated_at

        # Set up document
        self.set_auto_page_break(auto=True, margin=20)

        # Add Unicode font support - DejaVu fonts bundled in backend/fonts/
        fonts_dir = Path(__file__).parent.parent / 'fonts'
        self.add_font('DejaVu', '', str(fonts_dir / 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', str(fonts_dir / 'DejaVuSans-Bold.ttf'))

        self.add_page()

        # Add header
        self._add_header()

    def _add_header(self):
        """Add professional header with job metadata."""
        # Header background
        self.set_fill_color(*self.COLOR_HEADER_BG)
        self.rect(10, 10, 190, 35, 'F')

        # Title
        self.set_font('DejaVu', 'B', 18)
        self.set_text_color(*self.COLOR_PRIMARY)
        self.set_xy(15, 15)
        self.cell(0, 10, 'FAILURE SUMMARY REPORT', ln=True)

        # Metadata line
        self.set_font('DejaVu', '', 10)
        self.set_text_color(*self.COLOR_TEXT)
        self.set_xy(15, 28)

        timestamp_str = self.generated_at.strftime('%Y-%m-%d %H:%M UTC')
        metadata = f"Job ID: {self.job_id}  |  Failures: {self.failure_count}  |  Generated: {timestamp_str}"
        self.cell(0, 10, metadata, ln=True)

        # Add spacing after header
        self.ln(15)

    def render_markdown(self, markdown_content: str):
        """Parse and render markdown content to PDF."""
        if not markdown_content:
            return

        lines = markdown_content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines (add small spacing)
            if not line.strip():
                self.ln(3)
                i += 1
                continue

            # H2 header (## Header)
            if line.startswith('## '):
                self._render_h2(line[3:].strip())
                i += 1
                continue

            # H3 header (### Header)
            if line.startswith('### '):
                self._render_h3(line[4:].strip())
                i += 1
                continue

            # Bullet list item (- item or * item)
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                bullet_text = line.strip()[2:].strip()
                self._render_bullet(bullet_text)
                i += 1
                continue

            # Numbered list item (1. item)
            numbered_match = re.match(r'^(\d+)\.\s+(.+)$', line.strip())
            if numbered_match:
                number = numbered_match.group(1)
                text = numbered_match.group(2)
                self._render_numbered_item(number, text)
                i += 1
                continue

            # Regular paragraph
            self._render_paragraph(line.strip())
            i += 1

    def _render_h2(self, text: str):
        """Render H2 header with border."""
        self.ln(5)
        self.set_font('DejaVu', 'B', 14)
        self.set_text_color(*self.COLOR_PRIMARY)

        # Add text
        self.multi_cell(0, 7, text)

        # Add underline
        self.set_draw_color(*self.COLOR_HEADER_BG)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(10, y, 200, y)
        self.ln(4)

    def _render_h3(self, text: str):
        """Render H3 subheader."""
        self.ln(3)
        self.set_font('DejaVu', 'B', 12)
        self.set_text_color(*self.COLOR_TEXT)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def _render_bullet(self, text: str):
        """Render bullet list item."""
        self.set_font('DejaVu', '', 10)
        self.set_text_color(*self.COLOR_TEXT)

        # Bullet point
        x_start = self.get_x()
        self.set_x(15)
        self.cell(5, 5, '-', ln=0)  # Bullet character (using dash for compatibility)

        # Text with inline formatting
        self._render_text_with_formatting(text, indent=20)
        self.ln(2)

    def _render_numbered_item(self, number: str, text: str):
        """Render numbered list item."""
        self.set_font('DejaVu', '', 10)
        self.set_text_color(*self.COLOR_TEXT)

        self.set_x(15)
        self.cell(8, 5, f"{number}.", ln=0)

        self._render_text_with_formatting(text, indent=23)
        self.ln(2)

    def _render_paragraph(self, text: str):
        """Render regular paragraph with inline formatting."""
        self.set_font('DejaVu', '', 10)
        self.set_text_color(*self.COLOR_TEXT)
        self._render_text_with_formatting(text, indent=10)
        self.ln(2)

    def _render_text_with_formatting(self, text: str, indent: float = 10):
        """Render text with bold and code span formatting."""
        self.set_x(indent)

        # Parse inline formatting (bold **text** and code `text`)
        pattern = r'(\*\*[^*]+\*\*|`[^`]+`)'
        parts = re.split(pattern, text)

        # Calculate available width
        page_width = 210 - indent - 10  # A4 width minus margins

        current_line = ""
        current_x = indent

        for part in parts:
            if not part:
                continue

            # Check if bold
            if part.startswith('**') and part.endswith('**'):
                clean_text = part[2:-2]
                self.set_font('DejaVu', 'B', 10)
            # Check if code
            elif part.startswith('`') and part.endswith('`'):
                clean_text = part[1:-1]
                self.set_font('DejaVu', '', 9)  # Use DejaVu for code too (Unicode support)
            else:
                clean_text = part
                self.set_font('DejaVu', '', 10)

            # Simple approach: just output text, let multi_cell handle wrapping
            self.write(5, clean_text)

        self.ln()

    def generate(self) -> bytes:
        """Generate PDF and return as bytes."""
        return self.output()


def generate_failure_summary_pdf(
    job_id: int,
    failure_count: int,
    summary: str,
    generated_at: Optional[Union[datetime, str]] = None
) -> bytes:
    """
    Main entry point for generating failure summary PDF.

    Args:
        job_id: Job identifier
        failure_count: Number of failures in the report
        summary: Markdown-formatted summary content
        generated_at: Timestamp when summary was generated

    Returns:
        PDF file as bytes
    """
    pdf = FailureSummaryPdfGenerator(
        job_id=job_id,
        failure_count=failure_count,
        generated_at=generated_at
    )

    pdf.render_markdown(summary)

    return pdf.generate()
