"""
PDF Generator
=============
Converts investment memos from Markdown to professional PDF using WeasyPrint.
Supports both English and Chinese with appropriate typography.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class PDFResult:
    """Result of a PDF generation operation."""
    source_path: Path
    output_path: Path
    lang: str
    page_count: int
    file_size_bytes: int
    timestamp: datetime

    @property
    def file_size_kb(self) -> float:
        return self.file_size_bytes / 1024

    @property
    def is_success(self) -> bool:
        return self.output_path.exists() and self.file_size_bytes > 0


class MemoPDFGenerator:
    """Generates professional PDFs from investment memo markdown files."""

    # Language to CSS file mapping
    LANG_CSS = {
        "en": "memo_en.css",
        "zh": "memo_zh.css",
        "zh-CN": "memo_zh.css",
        "zh-TW": "memo_zh.css",  # Traditional Chinese uses same base
    }

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the PDF generator.

        Args:
            templates_dir: Directory containing HTML/CSS templates.
                          If None, uses default templates directory.
        """
        self.templates_dir = templates_dir or TEMPLATES_DIR
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"Templates directory not found: {self.templates_dir}")

        # Load base HTML template
        self.html_template = self._load_template("memo_base.html")

        # Font configuration for WeasyPrint (enables @font-face with external URLs)
        self.font_config = FontConfiguration()

        # Markdown processor with extensions
        # Note: Removed 'sane_lists' as it requires blank lines before lists
        # which breaks formatting when lists follow bold headers directly
        self.md = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "toc",
            ]
        )

    def _load_template(self, filename: str) -> str:
        """Load a template file."""
        template_path = self.templates_dir / filename
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def _load_css(self, lang: str) -> str:
        """Load the appropriate CSS for a language."""
        css_filename = self.LANG_CSS.get(lang, "memo_en.css")
        return self._load_template(css_filename)

    def _extract_title(self, markdown_content: str) -> str:
        """Extract title from markdown (first H1)."""
        lines = markdown_content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "Investment Memo"

    def _detect_language(self, content: str) -> str:
        """Detect if content is primarily Chinese or English."""
        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        total_chars = len(content)

        if total_chars == 0:
            return "en"

        # If more than 10% Chinese characters, assume Chinese
        if chinese_chars / total_chars > 0.1:
            return "zh-CN"
        return "en"

    def _convert_sources_table_to_bullets(self, content: str) -> str:
        """Convert Sources section from table format to bullet points.

        The synthesis MD now includes Sources in table format. This converts
        them to smaller bullet points for better PDF readability.
        """
        # Find the Sources section (English or Chinese)
        # Pattern accounts for optional section numbering like "## 10. Sources"
        # Final \n? handles last row without trailing newline
        sources_pattern = r'(##\s*(?:\d+\.\s*)?(?:Sources|资料来源|信息来源|来源)\s*\n+)((?:\|[^\n]*\n?)+)'

        def convert_table(match):
            header = match.group(1)
            table_content = match.group(2)

            # Parse table rows (skip header row and separator)
            lines = table_content.strip().split('\n')
            bullets = []

            for line in lines:
                # Skip separator lines (|---|---|...)
                if re.match(r'\|[-:\s|]+\|', line):
                    continue
                # Skip header row (first row with | # | Source | etc.)
                if '| # |' in line or '| Source |' in line or '| 来源 |' in line:
                    continue

                # Parse table cells
                cells = [c.strip() for c in line.split('|')[1:-1]]  # Remove empty first/last

                if len(cells) >= 4:
                    # Format: | # | Source Title | URL | Type | Summary |
                    # We want: - [Title](URL) — Type — Summary
                    idx = cells[0].strip()
                    title = cells[1].strip()
                    url = cells[2].strip()
                    src_type = cells[3].strip() if len(cells) > 3 else ''
                    summary = cells[4].strip() if len(cells) > 4 else ''

                    # Build bullet point
                    if url and url.startswith('http'):
                        bullet = f"- [{title}]({url})"
                    else:
                        bullet = f"- {title}"

                    if src_type:
                        bullet += f" — {src_type}"
                    if summary:
                        bullet += f" — {summary}"

                    bullets.append(bullet)

            # Return header + bullet list wrapped in a div for styling
            if bullets:
                return header + '\n'.join(bullets) + '\n'
            return match.group(0)  # Return original if no bullets generated

        return re.sub(sources_pattern, convert_table, content)

    def _preprocess_markdown(self, content: str) -> str:
        """Preprocess markdown to fix common formatting issues.

        - Ensures blank lines before list items that follow paragraphs
        - Converts Sources table to bullet points for smaller text
        - Normalizes line endings
        """
        # Convert Sources table to bullet point format
        content = self._convert_sources_table_to_bullets(content)

        lines = content.split('\n')
        processed = []

        for i, line in enumerate(lines):
            # Check if this line starts a list (- or * or numbered)
            is_list_start = bool(re.match(r'^[\-\*]\s+', line) or re.match(r'^\d+\.\s+', line))

            # If previous line exists and is not empty and not a list item
            if is_list_start and i > 0 and processed:
                prev_line = processed[-1]
                prev_is_list = bool(re.match(r'^[\-\*]\s+', prev_line) or re.match(r'^\d+\.\s+', prev_line))
                prev_is_empty = prev_line.strip() == ''

                # Add blank line if previous line is content (not empty, not list)
                if not prev_is_empty and not prev_is_list:
                    processed.append('')

            processed.append(line)

        return '\n'.join(processed)

    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML."""
        # Preprocess to fix formatting issues
        content = self._preprocess_markdown(markdown_content)
        # Reset the markdown processor for clean conversion
        self.md.reset()
        return self.md.convert(content)

    def _build_html(
        self,
        markdown_content: str,
        lang: str,
        title: Optional[str] = None,
    ) -> tuple[str, str]:
        """Build complete HTML document from markdown.

        Args:
            markdown_content: Markdown content to convert.
            lang: Language code.
            title: Optional document title.

        Returns:
            Tuple of (html_content, css_content) - CSS is returned separately
            so it can be loaded with FontConfiguration for proper font handling.
        """
        # Convert markdown to HTML (Sources table converted to bullets during preprocessing)
        body_html = self._markdown_to_html(markdown_content)

        # Load CSS for language
        css_content = self._load_css(lang)

        # Extract or use provided title
        if title is None:
            title = self._extract_title(markdown_content)

        # Build full HTML using template (CSS placeholder left empty - applied via stylesheet)
        html = self.html_template
        html = html.replace("{{ lang }}", lang)
        html = html.replace("{{ title }}", title)
        html = html.replace("{{ css }}", "/* CSS applied via external stylesheet */")
        html = html.replace("{{ content }}", body_html)
        html = html.replace("{{ date }}", datetime.now().strftime("%Y-%m-%d %H:%M"))

        return html, css_content

    def generate_pdf(
        self,
        markdown_path: Path,
        output_path: Optional[Path] = None,
        lang: Optional[str] = None,
    ) -> PDFResult:
        """Generate PDF from a markdown file.

        Args:
            markdown_path: Path to the markdown file.
            output_path: Path to save the PDF. If None, auto-generates.
            lang: Language code ("en", "zh-CN"). If None, auto-detects.

        Returns:
            PDFResult with generation details.
        """
        markdown_path = Path(markdown_path)
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        # Read markdown content
        markdown_content = markdown_path.read_text(encoding="utf-8")
        logger.info(f"Generating PDF: {markdown_path.name}")

        # Auto-detect language if not specified
        if lang is None:
            lang = self._detect_language(markdown_content)
            logger.info(f"Auto-detected language: {lang}")

        # Build HTML and get CSS separately (Sources from MD converted to bullets)
        html_content, css_content = self._build_html(markdown_content, lang)

        # Determine output path
        if output_path is None:
            output_path = markdown_path.with_suffix(".pdf")

        # Create CSS object with font configuration (enables @font-face with external URLs)
        css = CSS(string=css_content, font_config=self.font_config)

        # Generate PDF using WeasyPrint with font configuration
        html_doc = HTML(string=html_content, base_url=str(self.templates_dir))
        pdf_doc = html_doc.render(stylesheets=[css], font_config=self.font_config)

        # Write PDF
        pdf_doc.write_pdf(output_path)

        # Get file stats
        file_size = output_path.stat().st_size
        page_count = len(pdf_doc.pages)

        logger.info(
            f"PDF generated: {output_path.name} "
            f"({page_count} pages, {file_size/1024:.1f} KB)"
        )

        return PDFResult(
            source_path=markdown_path,
            output_path=output_path,
            lang=lang,
            page_count=page_count,
            file_size_bytes=file_size,
            timestamp=datetime.now(),
        )

    def generate_pdf_from_string(
        self,
        markdown_content: str,
        output_path: Path,
        lang: Optional[str] = None,
        title: Optional[str] = None,
    ) -> PDFResult:
        """Generate PDF from markdown string.

        Args:
            markdown_content: Markdown content as string.
            output_path: Path to save the PDF.
            lang: Language code ("en", "zh-CN"). If None, auto-detects.
            title: Document title. If None, extracts from content.

        Returns:
            PDFResult with generation details.
        """
        # Auto-detect language if not specified
        if lang is None:
            lang = self._detect_language(markdown_content)
            logger.info(f"Auto-detected language: {lang}")

        # Build HTML and get CSS separately
        html_content, css_content = self._build_html(markdown_content, lang, title)

        # Create CSS object with font configuration (enables @font-face with external URLs)
        css = CSS(string=css_content, font_config=self.font_config)

        # Generate PDF using WeasyPrint with font configuration
        html_doc = HTML(string=html_content, base_url=str(self.templates_dir))
        pdf_doc = html_doc.render(stylesheets=[css], font_config=self.font_config)

        # Write PDF
        output_path = Path(output_path)
        pdf_doc.write_pdf(output_path)

        # Get file stats
        file_size = output_path.stat().st_size
        page_count = len(pdf_doc.pages)

        logger.info(
            f"PDF generated: {output_path.name} "
            f"({page_count} pages, {file_size/1024:.1f} KB)"
        )

        return PDFResult(
            source_path=Path("(string input)"),
            output_path=output_path,
            lang=lang,
            page_count=page_count,
            file_size_bytes=file_size,
            timestamp=datetime.now(),
        )


def generate_pdf(
    markdown_path: Path,
    output_path: Optional[Path] = None,
    lang: Optional[str] = None,
) -> PDFResult:
    """Convenience function to generate PDF from a markdown file.

    Args:
        markdown_path: Path to the markdown file.
        output_path: Path to save the PDF. If None, auto-generates.
        lang: Language code ("en", "zh-CN"). If None, auto-detects.

    Returns:
        PDFResult with generation details.
    """
    generator = MemoPDFGenerator()
    return generator.generate_pdf(markdown_path, output_path, lang)


# CLI support for standalone testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if len(sys.argv) < 2:
        print("Usage: python pdf_generator.py <markdown_path> [output_path] [lang]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    lang = sys.argv[3] if len(sys.argv) > 3 else None

    result = generate_pdf(md_path, out_path, lang)

    print(f"\n{'='*60}")
    print(f"PDF Generation Complete")
    print(f"{'='*60}")
    print(f"Source: {result.source_path}")
    print(f"Output: {result.output_path}")
    print(f"Language: {result.lang}")
    print(f"Pages: {result.page_count}")
    print(f"Size: {result.file_size_kb:.1f} KB")
