"""
Newsletter Publisher
====================
Ghost integration for the TickerToThesis pipeline.

Ghost provides full API access on all plans, including:
  - Create/update/delete posts
  - Publish immediately or schedule
  - Send newsletters to subscribers
  - Manage members/subscribers
  - Paid subscription support (Publisher plan+)

This module provides:
  - GhostClient: Full async client for Ghost Admin API
  - format_memo_for_ghost(): Converts markdown memo to Ghost-compatible HTML
  - publish_memo(): High-level function to publish TTT memos
"""

import hashlib
import hmac
import json
import logging
import os
import re
import textwrap
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from .config import get_final_memo_path, get_output_dir, get_latest_output_dir, REPORT_OUTPUT
except ImportError:
    from config import get_final_memo_path, get_output_dir, get_latest_output_dir, REPORT_OUTPUT

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

def _load_env_file() -> Dict[str, str]:
    """Load credentials from .env file."""
    env_path = Path(__file__).parent.parent / "5 - credentials" / ".env"
    env_vars = {}

    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def get_ghost_credentials() -> tuple[str, str]:
    """Get Ghost URL and Admin API key from environment or .env file."""
    ghost_url = os.environ.get("GHOST_URL")
    admin_key = os.environ.get("GHOST_ADMIN_API_KEY")

    if not ghost_url or not admin_key:
        env_vars = _load_env_file()
        ghost_url = ghost_url or env_vars.get("GHOST_URL")
        admin_key = admin_key or env_vars.get("GHOST_ADMIN_API_KEY")

    if not ghost_url:
        raise ValueError(
            "GHOST_URL not found. Set it in environment or in "
            "'5 - credentials/.env'"
        )
    if not admin_key:
        raise ValueError(
            "GHOST_ADMIN_API_KEY not found. Set it in environment or in "
            "'5 - credentials/.env'"
        )

    # Ensure URL doesn't have trailing slash
    ghost_url = ghost_url.rstrip("/")

    return ghost_url, admin_key


# =============================================================================
# OG Image Generation
# =============================================================================

# Path to TTT logo (downloaded from Ghost)
ASSETS_DIR = Path(__file__).parent / "assets"
TTT_LOGO_PATH = ASSETS_DIR / "ttt_logo.png"


def generate_og_image(ticker: str, title: str, output_path: Optional[Path] = None) -> Path:
    """
    Generate a branded Open Graph image for social media sharing.

    Creates a 1200x630 image matching TTT website aesthetic:
    - Clean white background
    - Prominent ticker symbol
    - Title text
    - TTT branding

    Args:
        ticker: Stock ticker (e.g., "SE")
        title: Article title
        output_path: Where to save the image (default: temp file)

    Returns:
        Path to the generated image
    """
    if not HAS_PIL:
        raise ImportError("Pillow is required for OG image generation: pip install Pillow")

    width, height = 1200, 630

    # Clean white background (matching TTT site)
    img = Image.new('RGB', (width, height), color='#ffffff')
    draw = ImageDraw.Draw(img)

    # Black accent bar at top
    draw.rectangle([(0, 0), (width, 8)], fill='#000000')

    # Load fonts (with fallbacks)
    try:
        ticker_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia Bold.ttf', 96)
        title_font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia.ttf', 48)
        subtitle_font = ImageFont.truetype('/System/Library/Fonts/HelveticaNeue.ttc', 24)
    except OSError:
        try:
            # Linux fallbacks
            ticker_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 96)
            title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', 48)
            subtitle_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
        except OSError:
            # Ultimate fallback
            ticker_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

    # Ticker symbol - large and prominent
    ticker_text = f'${ticker}'
    draw.text((80, 100), ticker_text, font=ticker_font, fill='#000000')

    # Title - wrapped elegantly
    wrapped_lines = textwrap.wrap(title, width=38)
    y_pos = 230
    for line in wrapped_lines[:3]:  # Max 3 lines
        draw.text((80, y_pos), line, font=title_font, fill='#1a1a1a')
        y_pos += 60

    # Thin separator line
    draw.rectangle([(80, height - 100), (width - 80, height - 98)], fill='#e0e0e0')

    # Bottom branding
    draw.text((80, height - 70), 'tickertothesis.com', font=subtitle_font, fill='#666666')

    # Logo at bottom right
    if TTT_LOGO_PATH.exists():
        try:
            logo = Image.open(TTT_LOGO_PATH).convert('RGBA')
            logo = logo.resize((60, 60), Image.LANCZOS)
            img.paste(logo, (width - 140, height - 90), logo)
        except Exception as e:
            logger.warning(f"Could not add logo: {e}")

    # Determine output path
    if output_path is None:
        output_path = Path(f"/tmp/og_{ticker}_{int(time.time())}.png")

    img.save(output_path, quality=95)
    logger.info(f"Generated OG image: {output_path}")
    return output_path


@dataclass
class GhostConfig:
    """Configuration for Ghost API."""
    url: str
    admin_api_key: str

    @classmethod
    def from_env(cls) -> "GhostConfig":
        """Create config from environment."""
        url, key = get_ghost_credentials()
        return cls(url=url, admin_api_key=key)

    @property
    def api_key_id(self) -> str:
        """Extract the key ID from the admin API key."""
        return self.admin_api_key.split(":")[0]

    @property
    def api_key_secret(self) -> bytes:
        """Extract and decode the secret from the admin API key."""
        secret_hex = self.admin_api_key.split(":")[1]
        return bytes.fromhex(secret_hex)


# =============================================================================
# JWT Token Generation for Ghost Admin API
# =============================================================================

def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    import base64
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_ghost_jwt(config: GhostConfig) -> str:
    """
    Generate a JWT token for Ghost Admin API authentication.

    Ghost uses HS256 signed JWTs with:
    - Header: {"alg": "HS256", "typ": "JWT", "kid": "{key_id}"}
    - Payload: {"iat": now, "exp": now+300, "aud": "/admin/"}
    """
    # Header
    header = {
        "alg": "HS256",
        "typ": "JWT",
        "kid": config.api_key_id
    }

    # Payload - token valid for 5 minutes
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + 300,
        "aud": "/admin/"
    }

    # Encode header and payload
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    # Create signature
    message = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(config.api_key_secret, message, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


# =============================================================================
# Markdown to HTML Conversion
# =============================================================================

def markdown_to_html(markdown: str) -> str:
    """
    Convert markdown to HTML suitable for Ghost.

    Handles:
    - Headers (h1-h6) with horizontal rules below section headers
    - Bold/italic (including across word boundaries)
    - Lists (ordered/unordered)
    - Links
    - Code blocks
    - Tables (with special styling for Sources section)
    - Blockquotes
    - Horizontal rules
    - TL;DR highlighting
    """
    html = markdown

    # Strip YAML frontmatter if present
    if html.startswith("---"):
        parts = html.split("---", 2)
        if len(parts) >= 3:
            html = parts[2].strip()

    # Strip the first H1 (title) since Ghost displays it from the title field
    html = re.sub(r"^# .+\n+", "", html, count=1)

    # Code blocks (must be done before other processing)
    def replace_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        return f'<pre><code class="language-{lang}">{code}</code></pre>'

    html = re.sub(r"```(\w*)\n(.*?)```", replace_code_block, html, flags=re.DOTALL)

    # Inline code
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)

    # Headers with horizontal rules below h2 (section headers)
    # Process from h6 to h1 to avoid conflicts
    html = re.sub(r"^###### (.+)$", r"<h6>\1</h6>", html, flags=re.MULTILINE)
    html = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
    html = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    # h2 gets a horizontal rule below it
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>\n<hr>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic - process in correct order
    # Use [\s\S] or explicit flags to handle edge cases
    # Triple markers first
    html = re.sub(r"\*\*\*([^\*]+)\*\*\*", r"<strong><em>\1</em></strong>", html)
    html = re.sub(r"___([^_]+)___", r"<strong><em>\1</em></strong>", html)
    # Double markers (bold) - handle multi-word and spanning cases
    html = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", html)
    # Single markers (italic) - be careful not to match list items
    html = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", html)
    html = re.sub(r"(?<!_)_([^_\n]+)_(?!_)", r"<em>\1</em>", html)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Blockquotes
    def replace_blockquote(match):
        content = match.group(0)
        lines = content.split("\n")
        quote_lines = [line.lstrip("> ").lstrip(">") for line in lines]
        return f"<blockquote>{'<br>'.join(quote_lines)}</blockquote>"

    html = re.sub(r"^(?:> .+\n?)+", replace_blockquote, html, flags=re.MULTILINE)

    # Horizontal rules (standalone, not the ones we added after h2)
    html = re.sub(r"^[-*_]{3,}$", r"<hr>", html, flags=re.MULTILINE)

    # Tables - with special handling for Sources section
    # Styling matches existing tickertothesis.com posts
    def replace_table(match):
        table_text = match.group(0)
        lines = table_text.strip().split("\n")

        if len(lines) < 2:
            return table_text

        # Check if this is the Sources table
        header_row = lines[0].lower()
        is_sources = "source" in header_row and ("url" in header_row or "type" in header_row)

        if is_sources:
            # Render Sources as compact list - matches existing tickertothesis.com format
            sources_html = ['<div style="font-size:0.75em; color:#6b7280; line-height:1.6;">']
            sources_html.append('<ul style="margin:0; padding-left:1.5em;">')

            for line in lines[2:]:  # Skip header and separator
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if len(cells) >= 3:
                    # Extract: #, Title, URL, Type, Summary
                    title = cells[1] if len(cells) > 1 else ""
                    url = cells[2] if len(cells) > 2 else ""
                    source_type = cells[3] if len(cells) > 3 else ""

                    # Build source entry
                    if url and url.startswith("http"):
                        source_entry = f'{title} - <a href="{url}" style="color:#3b82f6;">{url[:60]}{"..." if len(url) > 60 else ""}</a>'
                    else:
                        source_entry = title

                    if source_type and source_type not in ["Unknown", ""]:
                        source_entry += f' [{source_type}]'

                    sources_html.append(f'<li style="margin-bottom:4px;">{source_entry}</li>')

            sources_html.append('</ul></div>')
            return '\n'.join(sources_html)
        else:
            # Regular table with dark header styling - matches existing tickertothesis.com
            html_table = ['<table style="width:100%; border-collapse:collapse; margin:1em 0; font-size:0.8em;">']

            # Header row with dark background
            header_cells = [cell.strip() for cell in lines[0].strip("|").split("|")]
            html_table.append('<thead><tr style="background-color:#1f2937;">')
            for cell in header_cells:
                html_table.append(f'<th style="border:1px solid #374151; padding:8px 10px; color:white; text-align:left; font-weight:600;">{cell}</th>')
            html_table.append("</tr></thead>")

            # Body rows
            html_table.append("<tbody>")
            for i, line in enumerate(lines[2:]):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                bg = '#f9fafb' if i % 2 == 1 else 'white'
                html_table.append(f'<tr style="background-color:{bg};">')
                for cell in cells:
                    html_table.append(f'<td style="border:1px solid #e5e7eb; padding:8px 10px;">{cell}</td>')
                html_table.append("</tr>")
            html_table.append("</tbody></table>")

            return "\n".join(html_table)

    # Match tables: header | separator | rows
    html = re.sub(
        r"^\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)+",
        replace_table,
        html,
        flags=re.MULTILINE,
    )

    # Unordered lists
    def replace_ul(match):
        items = match.group(0).strip().split("\n")
        html_items = []
        for item in items:
            content = re.sub(r"^[-*+]\s+", "", item.strip())
            html_items.append(f"<li>{content}</li>")
        return f"<ul>{''.join(html_items)}</ul>"

    html = re.sub(r"(?:^[-*+]\s+.+\n?)+", replace_ul, html, flags=re.MULTILINE)

    # Ordered lists
    def replace_ol(match):
        items = match.group(0).strip().split("\n")
        html_items = []
        for item in items:
            content = re.sub(r"^\d+\.\s+", "", item.strip())
            html_items.append(f"<li>{content}</li>")
        return f"<ol>{''.join(html_items)}</ol>"

    html = re.sub(r"(?:^\d+\.\s+.+\n?)+", replace_ol, html, flags=re.MULTILINE)

    # Paragraphs (wrap remaining text blocks)
    paragraphs = []
    current_para = []

    for line in html.split("\n"):
        stripped = line.strip()

        # Check if this line is already an HTML element
        if stripped.startswith("<") and not stripped.startswith("<a ") and not stripped.startswith("<strong>") and not stripped.startswith("<em>"):
            if current_para:
                para_text = " ".join(current_para)
                if para_text.strip():
                    paragraphs.append(f"<p>{para_text}</p>")
                current_para = []
            paragraphs.append(line)
        elif stripped == "":
            if current_para:
                para_text = " ".join(current_para)
                if para_text.strip():
                    paragraphs.append(f"<p>{para_text}</p>")
                current_para = []
        else:
            current_para.append(stripped)

    if current_para:
        para_text = " ".join(current_para)
        if para_text.strip():
            paragraphs.append(f"<p>{para_text}</p>")

    html = "\n".join(paragraphs)

    # TL;DR section highlighting - must happen AFTER paragraph wrapping
    # Matches existing tickertothesis.com styling
    def replace_tldr(match):
        # Extract list items and format with the exact styling from existing posts
        list_content = match.group(1)
        # Re-style the list items
        styled_items = re.sub(
            r'<li>',
            '<li style="margin-bottom:8px; line-height:1.5;">',
            list_content
        )
        return f'<div style="background-color:#f0f9ff; border-left:4px solid #0369a1; padding:16px 20px; margin:1em 0; border-radius:0 8px 8px 0;"><div style="font-weight:700; color:#0c4a6e; margin-bottom:12px; font-size:1.1em;">TL;DR</div><ul style="margin:0; padding-left:1.2em; color:#1e3a5f;">{styled_items}</ul></div>'

    # Match TL;DR section: paragraph with TL;DR followed by a list
    html = re.sub(
        r'<p><strong>TL;DR:</strong></p>\s*<ul>(.*?)</ul>',
        replace_tldr,
        html,
        flags=re.DOTALL
    )

    return html


def html_to_lexical(html: str) -> str:
    """
    Convert HTML content to Ghost lexical format.

    Uses HTML cards for styled content (TL;DR boxes, styled tables, sources)
    to preserve inline styling. Simple elements become native Lexical nodes
    via Ghost's HTML conversion, but styled sections are wrapped as HTML cards.

    For styled content that needs preservation, we wrap in <!--kg-card-begin-->
    and <!--kg-card-end--> markers which Ghost preserves as HTML cards.
    """
    # Wrap styled sections in Ghost HTML card markers
    # These markers tell Ghost to preserve the HTML as-is

    # TL;DR boxes - match from opening div to the final </ul></div>
    # Pattern: <div style="background-color:#f0f9ff...>...<ul...>...</ul></div>
    html = re.sub(
        r'(<div style="background-color:#f0f9ff[^>]*>.*?</ul></div>)',
        r'<!--kg-card-begin: html-->\1<!--kg-card-end: html-->',
        html,
        flags=re.DOTALL
    )

    # Styled tables (with dark headers) - match entire table
    html = re.sub(
        r'(<table style="width:100%; border-collapse:collapse[^>]*>.*?</table>)',
        r'<!--kg-card-begin: html-->\1<!--kg-card-end: html-->',
        html,
        flags=re.DOTALL
    )

    # Sources section - match from opening div to final </ul></div>
    html = re.sub(
        r'(<div style="font-size:0\.75em[^>]*>.*?</ul></div>)',
        r'<!--kg-card-begin: html-->\1<!--kg-card-end: html-->',
        html,
        flags=re.DOTALL
    )

    return html


def find_latest_memo(ticker: str, lang: str = "EN") -> Optional[Path]:
    """
    Find the most recent memo file for a ticker.

    Searches through all versioned output directories to find the latest memo.

    Args:
        ticker: Stock ticker symbol
        lang: Language code ("EN" or "CN")

    Returns:
        Path to the memo file, or None if not found
    """
    ticker = ticker.upper()
    if not REPORT_OUTPUT.exists():
        return None

    # Find all directories for this ticker, sorted by version (descending)
    pattern = re.compile(rf"^{ticker}_V(\d+)_")
    dirs_with_version = []

    for folder in REPORT_OUTPUT.iterdir():
        if folder.is_dir():
            match = pattern.match(folder.name)
            if match:
                dirs_with_version.append((int(match.group(1)), folder))

    # Sort by version descending (newest first)
    dirs_with_version.sort(key=lambda x: x[0], reverse=True)

    # Search for memo in each directory
    for _, folder in dirs_with_version:
        memo_path = folder / f"{ticker}_memo_{lang}.md"
        if memo_path.exists():
            return memo_path

    return None


def format_memo_for_ghost(
    ticker: str,
    lang: str = "EN",
    memo_path: Optional[Path] = None,
) -> Dict[str, str]:
    """
    Load and format a TTT memo for Ghost.

    Args:
        ticker: Stock ticker symbol
        lang: Language code ("EN" or "CN")
        memo_path: Explicit path to memo file (optional)

    Returns:
        Dict with 'title', 'html', 'plain_text', 'slug', 'ticker', 'lang', 'memo_path'
    """
    if memo_path is None:
        memo_path = find_latest_memo(ticker, lang)

    if memo_path is None or not memo_path.exists():
        raise FileNotFoundError(
            f"Memo not found for {ticker}_{lang}. "
            f"Run the TTT pipeline first or provide explicit memo_path."
        )

    markdown = memo_path.read_text(encoding="utf-8")

    # Extract title from first H1
    title_match = re.search(r"^# (.+)$", markdown, re.MULTILINE)
    title = title_match.group(1) if title_match else f"${ticker}: Investment Memo"

    # Ensure title starts with $TICKER: format
    if not title.startswith("$"):
        # Check if it starts with the ticker without $
        ticker_upper = ticker.upper()
        if title.upper().startswith(f"{ticker_upper}:"):
            title = f"${title}"
        elif title.upper().startswith(ticker_upper):
            # Handle "TICKER - ..." or "TICKER ..." formats
            title = f"${title}"

    # Generate slug from ticker and date
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = f"{ticker.lower()}-investment-memo-{date_str}"

    # Convert to HTML and wrap styled sections for Ghost preservation
    html = markdown_to_html(markdown)
    html = html_to_lexical(html)

    return {
        "title": title,
        "html": html,
        "plain_text": markdown,
        "slug": slug,
        "ticker": ticker,
        "lang": lang,
        "memo_path": str(memo_path),
    }


def save_formatted_memo(ticker: str, lang: str = "EN", memo_path: Optional[Path] = None) -> Path:
    """
    Save formatted memo as HTML file for preview.

    Args:
        ticker: Stock ticker symbol
        lang: Language code
        memo_path: Explicit path to memo file (optional)

    Returns:
        Path to the saved HTML file
    """
    formatted = format_memo_for_ghost(ticker, lang, memo_path)

    # Save HTML file in same directory as the memo
    source_memo = Path(formatted["memo_path"])
    output_dir = source_memo.parent
    html_path = output_dir / f"{ticker}_newsletter_{lang}.html"

    # Save as complete HTML document with Ghost-compatible styling
    full_html = f"""<!DOCTYPE html>
<html lang="{'en' if lang == 'EN' else 'zh'}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{formatted['title']}</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            max-width: 680px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.7;
            color: #1a1a1a;
        }}
        h1 {{ font-size: 2.2em; margin-bottom: 0.5em; }}
        h2 {{ font-size: 1.6em; margin-top: 1.5em; margin-bottom: 0.5em; border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.3em; margin-top: 1.2em; margin-bottom: 0.4em; }}
        p {{ margin-bottom: 1em; }}
        ul, ol {{ margin-bottom: 1em; padding-left: 1.5em; }}
        li {{ margin-bottom: 0.5em; }}
        blockquote {{ border-left: 3px solid #ccc; padding-left: 1em; margin: 1em 0; color: #555; font-style: italic; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5em 0.75em; text-align: left; }}
        th {{ background-color: #f5f5f5; font-weight: bold; }}
        code {{ background-color: #f5f5f5; padding: 0.15em 0.4em; border-radius: 3px; font-family: monospace; font-size: 0.9em; }}
        pre {{ background-color: #f5f5f5; padding: 1em; border-radius: 4px; overflow-x: auto; }}
        hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 2em 0; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
{formatted['html']}
</body>
</html>
"""

    html_path.write_text(full_html, encoding="utf-8")
    logger.info(f"Saved newsletter HTML: {html_path}")

    return html_path


# =============================================================================
# Ghost Admin API Client
# =============================================================================

class GhostClient:
    """
    Async client for Ghost Admin API.

    Provides full programmatic access to Ghost:
    - Posts: create, update, delete, publish, schedule
    - Members: list, create (requires higher plans)
    - Site: get configuration
    """

    def __init__(self, config: Optional[GhostConfig] = None):
        self.config = config or GhostConfig.from_env()
        self._session: Optional[aiohttp.ClientSession] = None
        self._token: Optional[str] = None
        self._token_expires: float = 0

    @property
    def _jwt_token(self) -> str:
        """Get a valid JWT token, regenerating if expired."""
        now = time.time()
        if self._token is None or now >= self._token_expires:
            self._token = generate_ghost_jwt(self.config)
            self._token_expires = now + 240  # Refresh 1 min before expiry
        return self._token

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Ghost {self._jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Version": "v5.0",  # Ghost API version
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an API request to Ghost Admin API."""
        session = await self._get_session()
        url = f"{self.config.url}/ghost/api/admin{endpoint}"

        async with session.request(
            method,
            url,
            json=data,
            params=params,
            headers=self.headers,
        ) as response:
            response_text = await response.text()

            if response.status >= 400:
                logger.error(f"Ghost API error: {response.status} - {response_text}")
                raise Exception(f"Ghost API error: {response.status} - {response_text}")

            if response_text:
                return json.loads(response_text)
            return {}

    # -------------------------------------------------------------------------
    # File Uploads
    # -------------------------------------------------------------------------

    async def upload_file(self, file_path: Path) -> str:
        """
        Upload a file (PDF, etc.) to Ghost.

        Args:
            file_path: Path to the file to upload

        Returns:
            URL of the uploaded file
        """
        session = await self._get_session()
        url = f"{self.config.url}/ghost/api/admin/files/upload/"

        # Read file
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine content type
        suffix = file_path.suffix.lower()
        content_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".zip": "application/zip",
        }
        content_type = content_types.get(suffix, "application/octet-stream")

        # Create form data
        with open(file_path, "rb") as f:
            file_data = f.read()

        form = aiohttp.FormData()
        form.add_field(
            "file",
            file_data,
            filename=file_path.name,
            content_type=content_type,
        )

        # Upload with JWT auth (but no Content-Type header - aiohttp sets it for multipart)
        headers = {
            "Authorization": f"Ghost {self._jwt_token}",
            "Accept": "application/json",
            "Accept-Version": "v5.0",
        }

        async with session.post(url, data=form, headers=headers) as response:
            response_text = await response.text()

            if response.status >= 400:
                logger.error(f"Ghost file upload error: {response.status} - {response_text}")
                raise Exception(f"Ghost file upload error: {response.status} - {response_text}")

            result = json.loads(response_text)
            # Response format: {"files": [{"url": "...", "ref": "..."}]}
            files = result.get("files", [])
            if files:
                return files[0].get("url", "")
            raise Exception("No file URL returned from Ghost")

    async def upload_image(self, image_path: Path) -> str:
        """
        Upload an image to Ghost.

        Args:
            image_path: Path to the image file (PNG, JPG, etc.)

        Returns:
            URL of the uploaded image
        """
        session = await self._get_session()
        url = f"{self.config.url}/ghost/api/admin/images/upload/"

        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Determine content type
        suffix = image_path.suffix.lower()
        content_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
        }
        content_type = content_types.get(suffix, "image/png")

        # Create form data
        with open(image_path, "rb") as f:
            file_data = f.read()

        form = aiohttp.FormData()
        form.add_field(
            "file",
            file_data,
            filename=image_path.name,
            content_type=content_type,
        )
        # Ghost requires 'purpose' field for images
        form.add_field("purpose", "image")

        headers = {
            "Authorization": f"Ghost {self._jwt_token}",
            "Accept": "application/json",
            "Accept-Version": "v5.0",
        }

        async with session.post(url, data=form, headers=headers) as response:
            response_text = await response.text()

            if response.status >= 400:
                logger.error(f"Ghost image upload error: {response.status} - {response_text}")
                raise Exception(f"Ghost image upload error: {response.status} - {response_text}")

            result = json.loads(response_text)
            # Response format: {"images": [{"url": "...", "ref": "..."}]}
            images = result.get("images", [])
            if images:
                return images[0].get("url", "")
            raise Exception("No image URL returned from Ghost")

    # -------------------------------------------------------------------------
    # Posts
    # -------------------------------------------------------------------------

    async def create_post(
        self,
        title: str,
        html: str,
        status: str = "draft",
        visibility: str = "public",
        slug: Optional[str] = None,
        custom_excerpt: Optional[str] = None,
        tags: Optional[List[str]] = None,
        feature_image: Optional[str] = None,
        send_email_when_published: bool = False,
        email_segment: str = "all",
    ) -> Dict:
        """
        Create a new post in Ghost.

        Args:
            title: Post title
            html: Post content as HTML
            status: 'draft', 'published', or 'scheduled'
            visibility: 'public', 'members', or 'paid'
            slug: URL slug (auto-generated if not provided)
            custom_excerpt: Short description for previews
            tags: List of tag names
            feature_image: URL of the feature image (for social sharing)
            send_email_when_published: Trigger newsletter send
            email_segment: 'all', 'status:free', or 'status:-free' (paid only)

        Returns:
            Created post data
        """
        post_data = {
            "title": title,
            "html": html,
            "status": status,
            "visibility": visibility,
        }

        if slug:
            post_data["slug"] = slug
        if custom_excerpt:
            post_data["custom_excerpt"] = custom_excerpt
        if tags:
            post_data["tags"] = [{"name": tag} for tag in tags]
        if feature_image:
            post_data["feature_image"] = feature_image

        # Newsletter settings (only apply when publishing)
        if status == "published" and send_email_when_published:
            post_data["email_segment"] = email_segment

        # Ghost 6.x requires source=html as query parameter for HTML→Lexical conversion
        response = await self._request(
            "POST",
            "/posts/?source=html",
            data={"posts": [post_data]},
        )

        return response.get("posts", [{}])[0]

    async def publish_post(
        self,
        title: str,
        html: str,
        visibility: str = "public",
        slug: Optional[str] = None,
        custom_excerpt: Optional[str] = None,
        tags: Optional[List[str]] = None,
        feature_image: Optional[str] = None,
        send_email: bool = True,
        email_segment: str = "all",
        newsletter_slug: str = "default-newsletter",
    ) -> Dict:
        """
        Create and immediately publish a post, optionally sending newsletter email.

        Uses two-step approach required by Ghost API:
        1. Create post as draft
        2. Publish with newsletter query parameters

        Args:
            title: Post title
            html: Post content as HTML
            visibility: 'public', 'members', or 'paid'
            slug: URL slug
            custom_excerpt: Short description
            tags: List of tag names
            feature_image: URL of the feature image (for social sharing)
            send_email: Send newsletter to subscribers
            email_segment: Target audience ('all', 'status:free', 'status:-free')
            newsletter_slug: Newsletter slug (default: 'default-newsletter')

        Returns:
            Published post data including URL and email status
        """
        # Step 1: Create as draft
        draft = await self.create_post(
            title=title,
            html=html,
            status="draft",
            visibility=visibility,
            slug=slug,
            custom_excerpt=custom_excerpt,
            tags=tags,
            feature_image=feature_image,
        )

        post_id = draft.get("id")
        updated_at = draft.get("updated_at")

        # Step 2: Publish with newsletter query params (if send_email)
        if send_email:
            # Use query parameters for newsletter - this is required by Ghost API
            session = await self._get_session()
            url = f"{self.config.url}/ghost/api/admin/posts/{post_id}/?newsletter={newsletter_slug}&email_segment={email_segment}"

            async with session.put(
                url,
                json={"posts": [{"updated_at": updated_at, "status": "published"}]},
                headers=self.headers,
            ) as response:
                response_text = await response.text()
                if response.status >= 400:
                    logger.error(f"Ghost API error: {response.status} - {response_text}")
                    raise Exception(f"Ghost API error: {response.status} - {response_text}")
                result = json.loads(response_text)
                return result.get("posts", [{}])[0]
        else:
            # Publish without email
            return await self.update_post(
                post_id=post_id,
                updated_at=updated_at,
                status="published",
            )

    async def create_draft(
        self,
        title: str,
        html: str,
        visibility: str = "public",
        slug: Optional[str] = None,
        custom_excerpt: Optional[str] = None,
        tags: Optional[List[str]] = None,
        feature_image: Optional[str] = None,
    ) -> Dict:
        """
        Create a draft post for later review.

        Args:
            title: Post title
            html: Post content as HTML
            visibility: 'public', 'members', or 'paid'
            slug: URL slug
            custom_excerpt: Short description
            tags: List of tag names
            feature_image: URL of the feature image (for social sharing)

        Returns:
            Draft post data
        """
        return await self.create_post(
            title=title,
            html=html,
            status="draft",
            visibility=visibility,
            slug=slug,
            custom_excerpt=custom_excerpt,
            tags=tags,
            feature_image=feature_image,
        )

    async def update_post(
        self,
        post_id: str,
        updated_at: str,
        **updates,
    ) -> Dict:
        """
        Update an existing post.

        Args:
            post_id: The post's ID
            updated_at: The post's current updated_at timestamp (for conflict detection)
            **updates: Fields to update (title, html, status, etc.)

        Returns:
            Updated post data
        """
        post_data = {"updated_at": updated_at, **updates}

        # Use source=html query param when updating HTML content
        endpoint = f"/posts/{post_id}/"
        if "html" in updates:
            endpoint = f"/posts/{post_id}/?source=html"

        response = await self._request(
            "PUT",
            endpoint,
            data={"posts": [post_data]},
        )

        return response.get("posts", [{}])[0]

    async def delete_post(self, post_id: str) -> bool:
        """
        Delete a post.

        Args:
            post_id: The post's ID

        Returns:
            True if deleted successfully
        """
        await self._request("DELETE", f"/posts/{post_id}/")
        return True

    async def send_email_for_post(
        self,
        post_id: str,
        email_segment: str = "all",
        newsletter_slug: str = "default-newsletter",
    ) -> Dict:
        """
        Send newsletter email for an existing published post.

        This uses the two-step approach required by Ghost API:
        1. Unpublish to draft
        2. Republish with newsletter query parameters

        Args:
            post_id: The post's ID
            email_segment: Target audience ('all', 'status:free', 'status:-free')
            newsletter_slug: Newsletter slug (default: 'default-newsletter')

        Returns:
            Updated post data with email status
        """
        # Get current post state
        post = await self.get_post(post_id=post_id)
        updated_at = post.get("updated_at")

        # Step 1: Unpublish to draft
        draft_result = await self.update_post(
            post_id=post_id,
            updated_at=updated_at,
            status="draft",
        )
        updated_at = draft_result.get("updated_at")

        # Step 2: Republish with newsletter query params
        session = await self._get_session()
        url = f"{self.config.url}/ghost/api/admin/posts/{post_id}/?newsletter={newsletter_slug}&email_segment={email_segment}"

        async with session.put(
            url,
            json={"posts": [{"updated_at": updated_at, "status": "published"}]},
            headers=self.headers,
        ) as response:
            response_text = await response.text()
            if response.status >= 400:
                logger.error(f"Ghost API error: {response.status} - {response_text}")
                raise Exception(f"Ghost API error: {response.status} - {response_text}")
            result = json.loads(response_text)
            return result.get("posts", [{}])[0]

    async def list_posts(
        self,
        status: str = "all",
        limit: int = 15,
        page: int = 1,
        include: Optional[List[str]] = None,
    ) -> Dict:
        """
        List posts.

        Args:
            status: 'all', 'draft', 'published', 'scheduled'
            limit: Number of posts per page (max 100)
            page: Page number
            include: Additional data to include ('tags', 'authors')

        Returns:
            Dict with 'posts' list and 'meta' pagination info
        """
        params = {
            "limit": min(limit, 100),
            "page": page,
        }

        if status != "all":
            params["filter"] = f"status:{status}"
        if include:
            params["include"] = ",".join(include)

        return await self._request("GET", "/posts/", params=params)

    async def get_post(
        self,
        post_id: Optional[str] = None,
        slug: Optional[str] = None,
        include: Optional[List[str]] = None,
        formats: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get a specific post by ID or slug.

        Args:
            post_id: The post's ID
            slug: The post's URL slug (alternative to ID)
            include: Additional data to include
            formats: Content formats to return ('html', 'mobiledoc', 'lexical')

        Returns:
            Post data
        """
        if not post_id and not slug:
            raise ValueError("Either post_id or slug must be provided")

        endpoint = f"/posts/{post_id}/" if post_id else f"/posts/slug/{slug}/"
        params = {}
        if include:
            params["include"] = ",".join(include)
        if formats:
            params["formats"] = ",".join(formats)

        response = await self._request("GET", endpoint, params=params)
        return response.get("posts", [{}])[0]

    # -------------------------------------------------------------------------
    # Members
    # -------------------------------------------------------------------------

    async def list_members(
        self,
        limit: int = 15,
        page: int = 1,
        filter_str: Optional[str] = None,
    ) -> Dict:
        """
        List members/subscribers.

        Args:
            limit: Number of members per page (max 100)
            page: Page number
            filter_str: Filter expression (e.g., 'status:free', 'status:paid')

        Returns:
            Dict with 'members' list and 'meta' pagination info
        """
        params = {
            "limit": min(limit, 100),
            "page": page,
        }

        if filter_str:
            params["filter"] = filter_str

        return await self._request("GET", "/members/", params=params)

    async def get_member_stats(self) -> Dict:
        """
        Get member statistics.

        Returns:
            Dict with total, free, and paid member counts
        """
        # Get counts for different member types
        all_members = await self.list_members(limit=1)
        free_members = await self.list_members(limit=1, filter_str="status:free")
        paid_members = await self.list_members(limit=1, filter_str="status:paid")

        return {
            "total": all_members.get("meta", {}).get("pagination", {}).get("total", 0),
            "free": free_members.get("meta", {}).get("pagination", {}).get("total", 0),
            "paid": paid_members.get("meta", {}).get("pagination", {}).get("total", 0),
        }

    # -------------------------------------------------------------------------
    # Site
    # -------------------------------------------------------------------------

    async def get_site(self) -> Dict:
        """
        Get site configuration and metadata.

        Returns:
            Site configuration including title, description, URL
        """
        response = await self._request("GET", "/site/")
        return response.get("site", {})


# =============================================================================
# High-Level Publishing Functions
# =============================================================================

async def publish_memo(
    ticker: str,
    lang: str = "EN",
    draft: bool = True,
    visibility: str = "public",
    send_email: bool = False,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Publish a TTT memo to Ghost.

    Args:
        ticker: Stock ticker symbol
        lang: Language code ("EN" or "CN")
        draft: If True, create as draft; if False, publish immediately
        visibility: 'public', 'members', or 'paid'
        send_email: Send newsletter when publishing (ignored if draft=True)
        tags: Optional list of tags (defaults to none - keeps title area clean)

    Returns:
        Dict with post data and status
    """
    logger.info(f"Publishing {ticker} memo to Ghost (draft={draft})...")

    # Format the memo
    formatted = format_memo_for_ghost(ticker, lang)

    # No tags by default - Ghost themes show primary tag above title which looks cluttered
    if tags is None:
        tags = []

    async with GhostClient() as client:
        if draft:
            post = await client.create_draft(
                title=formatted["title"],
                html=formatted["html"],
                visibility=visibility,
                slug=formatted["slug"],
                tags=tags,
            )
            status = "draft"
        else:
            post = await client.publish_post(
                title=formatted["title"],
                html=formatted["html"],
                visibility=visibility,
                slug=formatted["slug"],
                tags=tags,
                send_email=send_email,
            )
            status = "published"

    # Also save local HTML copy
    html_path = save_formatted_memo(ticker, lang)

    result = {
        "ticker": ticker,
        "lang": lang,
        "status": status,
        "post_id": post.get("id"),
        "post_url": post.get("url"),
        "slug": post.get("slug"),
        "title": formatted["title"],
        "visibility": visibility,
        "html_file": str(html_path),
        "memo_path": formatted["memo_path"],
    }

    if status == "published":
        email_data = post.get("email")
        if email_data:
            result["email_sent"] = True
            result["email_status"] = email_data.get("status")
            result["email_recipients"] = email_data.get("email_count")
        else:
            result["email_sent"] = False

    logger.info(f"Memo {'saved as draft' if draft else 'published'}: {result.get('post_url', post.get('id'))}")
    return result


async def get_newsletter_stats() -> Dict[str, Any]:
    """Get current newsletter statistics from Ghost."""
    async with GhostClient() as client:
        site = await client.get_site()
        members = await client.get_member_stats()
        posts = await client.list_posts(status="published", limit=5)

        return {
            "site": {
                "title": site.get("title"),
                "url": site.get("url"),
            },
            "members": members,
            "recent_posts": [
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "slug": p.get("slug"),
                    "url": p.get("url"),
                    "published_at": p.get("published_at"),
                    "visibility": p.get("visibility"),
                }
                for p in posts.get("posts", [])
            ],
        }


async def test_connection() -> Dict[str, Any]:
    """Test Ghost API connection and return site info."""
    async with GhostClient() as client:
        site = await client.get_site()
        return {
            "status": "connected",
            "site_title": site.get("title"),
            "site_url": site.get("url"),
            "ghost_version": site.get("version"),
        }


# =============================================================================
# Delayed Content Unlock (Paid → Free after X days)
# =============================================================================

async def unlock_aged_posts(
    days_delay: int = 60,
    from_visibility: str = "paid",
    to_visibility: str = "public",
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Automatically change visibility of posts older than X days.

    Use case: Make paid content available to free users after 60 days.

    Args:
        days_delay: Number of days before unlocking (default 60)
        from_visibility: Current visibility to match ('paid', 'members')
        to_visibility: New visibility to set ('public', 'members', 'paid')
        dry_run: If True, only report what would change without making changes

    Returns:
        Dict with 'unlocked' list of posts and 'count'
    """
    from datetime import datetime, timedelta, timezone

    cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_delay)

    async with GhostClient() as client:
        # Get all published posts with the target visibility
        all_posts = []
        page = 1
        while True:
            response = await client.list_posts(
                status="published",
                limit=100,
                page=page,
                include=["tags"],
            )
            posts = response.get("posts", [])
            if not posts:
                break
            all_posts.extend(posts)
            page += 1

        # Filter posts that match criteria
        posts_to_unlock = []
        for post in all_posts:
            if post.get("visibility") != from_visibility:
                continue

            published_at = post.get("published_at")
            if not published_at:
                continue

            # Parse ISO date
            pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            pub_date = pub_date.replace(tzinfo=None)  # Make naive for comparison

            if pub_date < cutoff_date:
                posts_to_unlock.append(post)

        results = {
            "total_checked": len(all_posts),
            "matching_visibility": len([p for p in all_posts if p.get("visibility") == from_visibility]),
            "older_than_cutoff": len(posts_to_unlock),
            "cutoff_date": cutoff_date.isoformat(),
            "dry_run": dry_run,
            "unlocked": [],
        }

        if dry_run:
            results["would_unlock"] = [
                {"id": p["id"], "title": p["title"], "published_at": p["published_at"]}
                for p in posts_to_unlock
            ]
            logger.info(f"DRY RUN: Would unlock {len(posts_to_unlock)} posts")
        else:
            # Actually update the posts
            for post in posts_to_unlock:
                try:
                    await client.update_post(
                        post_id=post["id"],
                        updated_at=post["updated_at"],
                        visibility=to_visibility,
                    )
                    results["unlocked"].append({
                        "id": post["id"],
                        "title": post["title"],
                        "old_visibility": from_visibility,
                        "new_visibility": to_visibility,
                    })
                    logger.info(f"Unlocked: {post['title']}")
                except Exception as e:
                    logger.error(f"Failed to unlock {post['title']}: {e}")

        results["count"] = len(results.get("unlocked", results.get("would_unlock", [])))
        return results


# =============================================================================
# PDF Attachments
# =============================================================================

def find_pdfs_for_ticker(ticker: str) -> Dict[str, Path]:
    """
    Find PDF files for a ticker in the report output directory.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with 'EN' and/or 'CN' keys mapping to PDF paths
    """
    ticker = ticker.upper()
    if not REPORT_OUTPUT.exists():
        return {}

    # Find all directories for this ticker, sorted by version (descending)
    pattern = re.compile(rf"^{re.escape(ticker)}_V(\d+)_")
    dirs_with_version = []

    for folder in REPORT_OUTPUT.iterdir():
        if folder.is_dir():
            match = pattern.match(folder.name)
            if match:
                dirs_with_version.append((int(match.group(1)), folder))

    # Sort by version descending (newest first)
    dirs_with_version.sort(key=lambda x: x[0], reverse=True)

    pdfs = {}
    for _, folder in dirs_with_version:
        # Check for EN PDF
        for en_pattern in [f"{ticker}_memo_EN.pdf", f"{ticker}_memo_vF_*.pdf"]:
            for pdf_path in folder.glob(en_pattern.replace("*", "*")):
                if "EN" not in pdfs and "_zh" not in pdf_path.name and "_CN" not in pdf_path.name:
                    pdfs["EN"] = pdf_path
                    break

        # Check for CN PDF
        for cn_pattern in [f"{ticker}_memo_CN.pdf", f"{ticker}_memo_vF_*_zh.pdf"]:
            for pdf_path in folder.glob(cn_pattern.replace("*", "*")):
                if "CN" not in pdfs:
                    pdfs["CN"] = pdf_path
                    break

        # Stop if we found both
        if "EN" in pdfs and "CN" in pdfs:
            break

    return pdfs


def create_pdf_download_section(pdf_urls: Dict[str, str], ticker: str) -> str:
    """
    Create HTML for PDF download section.

    Args:
        pdf_urls: Dict with 'EN' and/or 'CN' keys mapping to URLs
        ticker: Stock ticker symbol

    Returns:
        HTML string for the download section
    """
    if not pdf_urls:
        return ""

    html_parts = [
        '<hr>',
        '<div class="pdf-downloads" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">',
        f'<h3 style="margin-top: 0;">📥 Download {ticker} Investment Memo</h3>',
        '<p>Get the full research memo in PDF format:</p>',
        '<ul style="list-style: none; padding: 0;">',
    ]

    if "EN" in pdf_urls:
        html_parts.append(
            f'<li style="margin: 10px 0;">'
            f'<a href="{pdf_urls["EN"]}" style="display: inline-block; background: #1a1a1a; color: white; '
            f'padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold;">'
            f'📄 English PDF</a></li>'
        )

    if "CN" in pdf_urls:
        html_parts.append(
            f'<li style="margin: 10px 0;">'
            f'<a href="{pdf_urls["CN"]}" style="display: inline-block; background: #1a1a1a; color: white; '
            f'padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold;">'
            f'📄 中文 PDF</a></li>'
        )

    html_parts.extend([
        '</ul>',
        '</div>',
    ])

    return '\n'.join(html_parts)


async def add_pdfs_to_post(
    post_id: str,
    ticker: str,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Upload PDFs and add download links to an existing post.

    Args:
        post_id: Ghost post ID
        ticker: Stock ticker symbol
        dry_run: If True, only report what would happen

    Returns:
        Dict with results
    """
    pdfs = find_pdfs_for_ticker(ticker)
    if not pdfs:
        return {
            "status": "no_pdfs",
            "ticker": ticker,
            "message": f"No PDFs found for {ticker}",
        }

    async with GhostClient() as client:
        # Get current post with HTML format explicitly requested
        post = await client.get_post(post_id=post_id, formats=["html"])
        current_html = post.get("html", "")
        updated_at = post.get("updated_at")

        # Safety check: don't proceed if current HTML is empty or suspiciously short
        if not current_html or len(current_html) < 500:
            logger.error(f"Current HTML is empty or too short ({len(current_html)} chars). Aborting to prevent content loss.")
            return {
                "status": "error",
                "ticker": ticker,
                "post_id": post_id,
                "post_title": post.get("title"),
                "message": f"Cannot add PDFs: post HTML content is empty or too short ({len(current_html)} chars). This may indicate an API issue.",
            }

        if dry_run:
            return {
                "status": "dry_run",
                "ticker": ticker,
                "post_id": post_id,
                "post_title": post.get("title"),
                "pdfs_found": {lang: str(path) for lang, path in pdfs.items()},
                "would_upload": list(pdfs.keys()),
            }

        # Upload PDFs
        pdf_urls = {}
        for lang, pdf_path in pdfs.items():
            try:
                url = await client.upload_file(pdf_path)
                pdf_urls[lang] = url
                logger.info(f"Uploaded {lang} PDF: {url}")
            except Exception as e:
                logger.error(f"Failed to upload {lang} PDF: {e}")

        if not pdf_urls:
            return {
                "status": "upload_failed",
                "ticker": ticker,
                "post_id": post_id,
                "message": "Failed to upload any PDFs",
            }

        # Create download section
        download_section = create_pdf_download_section(pdf_urls, ticker)

        # Check if download section already exists
        if "pdf-downloads" in current_html:
            # Replace existing section
            import re as regex
            new_html = regex.sub(
                r'<hr>\s*<div class="pdf-downloads".*?</div>',
                download_section,
                current_html,
                flags=regex.DOTALL,
            )
        else:
            # Append to end
            new_html = current_html + "\n" + download_section

        # Update post (source=html handled via query param in update_post)
        await client.update_post(
            post_id=post_id,
            updated_at=updated_at,
            html=new_html,
        )

        return {
            "status": "success",
            "ticker": ticker,
            "post_id": post_id,
            "post_title": post.get("title"),
            "pdfs_uploaded": pdf_urls,
        }


async def add_pdfs_to_all_drafts(dry_run: bool = True, force: bool = False) -> Dict[str, Any]:
    """
    Find all draft posts and add PDF download links to them.

    Args:
        dry_run: If True, only report what would happen
        force: If True, re-upload PDFs even if post already has them

    Returns:
        Dict with results for each post
    """
    async with GhostClient() as client:
        # Get all drafts
        all_drafts = []
        page = 1
        while True:
            response = await client.list_posts(status="draft", limit=100, page=page)
            posts = response.get("posts", [])
            if not posts:
                break
            all_drafts.extend(posts)
            page += 1

        results = {
            "total_drafts": len(all_drafts),
            "processed": [],
            "skipped": [],
            "dry_run": dry_run,
        }

        for post in all_drafts:
            title = post.get("title", "")
            post_id = post.get("id")

            # Extract ticker from title (assuming format like "COIN Investment Memo" or "$COIN: ...")
            ticker_match = re.search(r'\$?([A-Z]{2,5})\b', title)
            if not ticker_match:
                results["skipped"].append({
                    "post_id": post_id,
                    "title": title,
                    "reason": "Could not extract ticker from title",
                })
                continue

            ticker = ticker_match.group(1)

            # Check if PDFs exist
            pdfs = find_pdfs_for_ticker(ticker)
            if not pdfs:
                results["skipped"].append({
                    "post_id": post_id,
                    "title": title,
                    "ticker": ticker,
                    "reason": "No PDFs found",
                })
                continue

            # Check if already has PDF section
            current_html = post.get("html", "")
            if "pdf-downloads" in current_html and not force:
                results["skipped"].append({
                    "post_id": post_id,
                    "title": title,
                    "ticker": ticker,
                    "reason": "Already has PDF downloads section (use --force to update)",
                })
                continue

            if dry_run:
                results["processed"].append({
                    "post_id": post_id,
                    "title": title,
                    "ticker": ticker,
                    "pdfs": list(pdfs.keys()),
                    "action": "would_add_pdfs",
                })
            else:
                # Actually add PDFs
                result = await add_pdfs_to_post(post_id, ticker, dry_run=False)
                results["processed"].append(result)

        return results


# =============================================================================
# CLI Interface
# =============================================================================

async def main():
    """CLI entry point for Ghost newsletter publisher."""
    import argparse

    parser = argparse.ArgumentParser(
        description="TTT Newsletter Publisher (Ghost)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test API connection
  python newsletter_publisher.py test

  # Create draft post from COIN memo
  python newsletter_publisher.py publish --ticker COIN --draft

  # Publish and send newsletter
  python newsletter_publisher.py publish --ticker COIN --send-email

  # Get newsletter stats
  python newsletter_publisher.py stats

  # List recent posts
  python newsletter_publisher.py list-posts

  # Preview which paid posts would become free after 60 days
  python newsletter_publisher.py unlock --days 60 --dry-run

  # Actually unlock paid posts older than 60 days
  python newsletter_publisher.py unlock --days 60 --execute

  # Preview adding PDFs to all drafts
  python newsletter_publisher.py add-pdfs --all --dry-run

  # Actually add PDFs to all drafts
  python newsletter_publisher.py add-pdfs --all --execute

  # Send email for a specific post
  python newsletter_publisher.py send-email --post-id abc123

  # Send email for all published posts that haven't been emailed
  python newsletter_publisher.py send-email --all
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Test command
    subparsers.add_parser("test", help="Test Ghost API connection")

    # Publish command
    publish_parser = subparsers.add_parser("publish", help="Publish a memo to Ghost")
    publish_parser.add_argument("--ticker", required=True, help="Stock ticker symbol")
    publish_parser.add_argument("--lang", default="EN", choices=["EN", "CN"], help="Language")
    publish_parser.add_argument("--draft", action="store_true", help="Save as draft (default)")
    publish_parser.add_argument("--publish", action="store_true", help="Publish immediately")
    publish_parser.add_argument("--send-email", action="store_true", help="Send newsletter email")
    publish_parser.add_argument("--visibility", default="public",
                               choices=["public", "members", "paid"],
                               help="Post visibility")

    # Stats command
    subparsers.add_parser("stats", help="Get newsletter statistics")

    # List posts command
    list_parser = subparsers.add_parser("list-posts", help="List recent posts")
    list_parser.add_argument("--limit", type=int, default=10, help="Number of posts")
    list_parser.add_argument("--status", default="all",
                            choices=["all", "draft", "published", "scheduled"],
                            help="Filter by status")

    # Format command (local only, no API)
    format_parser = subparsers.add_parser("format", help="Format memo as HTML (no API)")
    format_parser.add_argument("--ticker", required=True, help="Stock ticker symbol")
    format_parser.add_argument("--lang", default="EN", choices=["EN", "CN"], help="Language")

    # Unlock command (delayed content unlock)
    unlock_parser = subparsers.add_parser("unlock", help="Unlock aged paid posts (make free after X days)")
    unlock_parser.add_argument("--days", type=int, default=60, help="Days before unlocking (default: 60)")
    unlock_parser.add_argument("--from-visibility", default="paid",
                               choices=["paid", "members"],
                               help="Current visibility to match (default: paid)")
    unlock_parser.add_argument("--to-visibility", default="public",
                               choices=["public", "members"],
                               help="New visibility to set (default: public)")
    unlock_parser.add_argument("--dry-run", action="store_true", default=True,
                               help="Preview changes without applying (default: True)")
    unlock_parser.add_argument("--execute", action="store_true",
                               help="Actually apply changes (overrides --dry-run)")

    # Add PDFs command
    addpdfs_parser = subparsers.add_parser("add-pdfs", help="Add PDF downloads to posts")
    addpdfs_parser.add_argument("--all", action="store_true",
                                help="Add PDFs to all drafts that don't have them")
    addpdfs_parser.add_argument("--post-id", help="Specific post ID to update")
    addpdfs_parser.add_argument("--ticker", help="Ticker symbol (required with --post-id)")
    addpdfs_parser.add_argument("--dry-run", action="store_true", default=True,
                                help="Preview changes without applying (default: True)")
    addpdfs_parser.add_argument("--execute", action="store_true",
                                help="Actually apply changes (overrides --dry-run)")
    addpdfs_parser.add_argument("--force", action="store_true",
                                help="Re-upload PDFs even if post already has them")

    # Send email command (for existing published posts)
    sendemail_parser = subparsers.add_parser("send-email", help="Send newsletter email for existing posts")
    sendemail_parser.add_argument("--post-id", help="Specific post ID to send email for")
    sendemail_parser.add_argument("--all", action="store_true",
                                  help="Send email for all published posts that haven't been emailed")
    sendemail_parser.add_argument("--email-segment", default="all",
                                  choices=["all", "status:free", "status:-free"],
                                  help="Target audience (default: all)")

    args = parser.parse_args()

    if args.command == "test":
        result = await test_connection()
        print(json.dumps(result, indent=2))

    elif args.command == "publish":
        # --draft is default, --publish overrides it
        draft = not args.publish
        result = await publish_memo(
            ticker=args.ticker,
            lang=args.lang,
            draft=draft,
            visibility=args.visibility,
            send_email=args.send_email,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "stats":
        stats = await get_newsletter_stats()
        print(json.dumps(stats, indent=2, default=str))

    elif args.command == "list-posts":
        async with GhostClient() as client:
            posts = await client.list_posts(status=args.status, limit=args.limit)
            print(json.dumps(posts, indent=2, default=str))

    elif args.command == "format":
        html_path = save_formatted_memo(args.ticker, args.lang)
        print(f"Formatted memo saved to: {html_path}")

    elif args.command == "unlock":
        # --execute overrides --dry-run
        dry_run = not args.execute
        result = await unlock_aged_posts(
            days_delay=args.days,
            from_visibility=args.from_visibility,
            to_visibility=args.to_visibility,
            dry_run=dry_run,
        )
        print(json.dumps(result, indent=2, default=str))
        if dry_run:
            print(f"\n[DRY RUN] Would unlock {result['count']} posts. Use --execute to apply.")
        else:
            print(f"\nUnlocked {result['count']} posts.")

    elif args.command == "add-pdfs":
        dry_run = not args.execute
        force = getattr(args, 'force', False)

        if args.all:
            # Add PDFs to all drafts
            result = await add_pdfs_to_all_drafts(dry_run=dry_run, force=force)
            print(json.dumps(result, indent=2, default=str))
            processed_count = len(result.get("processed", []))
            skipped_count = len(result.get("skipped", []))
            if dry_run:
                print(f"\n[DRY RUN] Would add PDFs to {processed_count} posts. Skipped: {skipped_count}. Use --execute to apply.")
            else:
                print(f"\nAdded PDFs to {processed_count} posts. Skipped: {skipped_count}.")

        elif args.post_id:
            if not args.ticker:
                print("Error: --ticker is required when using --post-id")
                return
            result = await add_pdfs_to_post(args.post_id, args.ticker, dry_run=dry_run)
            print(json.dumps(result, indent=2, default=str))

        else:
            print("Error: Use --all to update all drafts, or --post-id with --ticker for a specific post")

    elif args.command == "send-email":
        if args.post_id:
            # Send email for specific post
            async with GhostClient() as client:
                result = await client.send_email_for_post(
                    post_id=args.post_id,
                    email_segment=args.email_segment,
                )
                email = result.get("email", {})
                if email:
                    print(f"✓ Email sent for: {result.get('title')}")
                    print(f"  Status: {email.get('status')}")
                    print(f"  Recipients: {email.get('email_count')}")
                else:
                    print(f"✗ Failed to send email for: {result.get('title')}")

        elif args.all:
            # Send email for all published posts without email
            async with GhostClient() as client:
                response = await client.list_posts(status="published", limit=100, include=["email"])
                posts = response.get("posts", [])

                # Filter posts without email
                posts_without_email = [p for p in posts if not p.get("email")]
                print(f"Found {len(posts_without_email)} posts without email sent\n")

                for i, post in enumerate(posts_without_email, 1):
                    title = post.get("title", "")[:45]
                    print(f"[{i}/{len(posts_without_email)}] {title}...")

                    result = await client.send_email_for_post(
                        post_id=post.get("id"),
                        email_segment=args.email_segment,
                    )
                    email = result.get("email", {})
                    if email:
                        print(f"  ✓ Email queued ({email.get('email_count')} recipients)")
                    else:
                        print(f"  ✗ Failed")

                print(f"\nDone!")

        else:
            print("Error: Use --post-id for a specific post or --all for all posts without email")

    else:
        parser.print_help()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
