"""
Memo Translator
===============
Translates investment memos to Chinese using Claude with finance-aware prompting.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

# Load environment variables
_env_locations = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
    Path.home() / ".anthropic" / ".env",
]
for _env_path in _env_locations:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result of a translation operation."""
    source_path: Path
    target_path: Path
    source_lang: str
    target_lang: str
    source_content: str
    translated_content: str
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: datetime

    @property
    def is_success(self) -> bool:
        return bool(self.translated_content)


# Translation system prompt for financial documents
TRANSLATION_SYSTEM_PROMPT = """You are a professional financial translator specializing in investment research.

Your task is to translate English investment memos to Simplified Chinese (简体中文) with institutional-quality precision.

## Core Requirements

1. **Financial Terminology Standards**
   Use standard Chinese finance terms consistently:
   - IRR → 内部收益率 (IRR)
   - WACC → 加权平均资本成本 (WACC)
   - ROIC → 投入资本回报率 (ROIC)
   - ROE → 净资产收益率 (ROE)
   - EV/EBITDA → 企业价值/息税折旧摊销前利润 (EV/EBITDA)
   - P/E → 市盈率 (P/E)
   - P/B → 市净率 (P/B)
   - FCF → 自由现金流 (FCF)
   - DCF → 现金流折现 (DCF)
   - Moat → 护城河
   - Compounder → 复利增长型企业
   - Margin of Safety → 安全边际
   - Intrinsic Value → 内在价值
   - Bull case → 乐观情景
   - Bear case → 悲观情景
   - Base case → 基准情景
   - Upside → 上行空间
   - Downside → 下行风险
   - Catalyst → 催化剂
   - Kill condition → 终止条件
   - Risk/reward → 风险收益比
   - TAM (Total Addressable Market) → 潜在市场规模 (TAM)
   - ARR (Annual Recurring Revenue) → 年度经常性收入 (ARR)
   - NRR (Net Revenue Retention) → 净收入留存率 (NRR)
   - Churn → 客户流失率
   - LTV/CAC → 客户终身价值/获客成本 (LTV/CAC)

2. **Preserve Structure Exactly**
   - Keep all markdown formatting (headers, lists, tables, bold, italics)
   - Maintain the exact document structure
   - Do not add or remove sections

3. **Number and Symbol Handling**
   - Keep all numbers in original format (e.g., $1.2B, 15.3%, 2.5x)
   - Keep currency symbols ($, €, ¥)
   - Keep percentage signs (%)
   - Keep ticker symbols in English (e.g., AAPL, MSFT, GTLB)

4. **Tone and Style**
   - Professional and analytical
   - Suitable for institutional investors
   - Avoid colloquialisms
   - Match the authority of the original

5. **Special Elements**
   - Keep URLs and links unchanged
   - Keep code blocks unchanged
   - Translate table headers but keep data values as-is

Output ONLY the translated document. Do not include any explanation or commentary."""


class MemoTranslator:
    """Translates investment memos using Claude API."""

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 16000,
        timeout: float = 300.0,
    ):
        """Initialize the translator.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Claude model to use for translation.
            max_tokens: Maximum output tokens.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout

    async def translate(
        self,
        content: str,
        source_lang: str = "en",
        target_lang: str = "zh-CN",
    ) -> tuple[str, int, int]:
        """Translate content from source to target language.

        Args:
            content: The text content to translate.
            source_lang: Source language code (default: "en").
            target_lang: Target language code (default: "zh-CN").

        Returns:
            Tuple of (translated_content, input_tokens, output_tokens).
        """
        user_prompt = f"""Translate the following investment memo from English to Simplified Chinese (简体中文).

## Source Document

{content}"""

        try:
            response = await asyncio.wait_for(
                self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0.3,  # Lower temperature for consistency
                    system=[{
                        "type": "text",
                        "text": TRANSLATION_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"}
                    }],
                    messages=[{"role": "user", "content": user_prompt}],
                ),
                timeout=self.timeout,
            )

            # Extract content
            translated = ""
            for block in response.content:
                if hasattr(block, "text"):
                    translated += block.text

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            # Log cache metrics
            cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
            cache_write = getattr(response.usage, "cache_creation_input_tokens", 0)
            if cache_read > 0:
                logger.info(f"Translation cache HIT: {cache_read:,} tokens")
            if cache_write > 0:
                logger.debug(f"Translation cache WRITE: {cache_write:,} tokens")

            logger.info(
                f"Translation complete: {input_tokens:,} in / {output_tokens:,} out"
            )

            return translated, input_tokens, output_tokens

        except anthropic.RateLimitError as e:
            logger.error(f"Rate limit hit during translation: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error(f"Translation timed out after {self.timeout}s")
            raise
        except anthropic.APIError as e:
            logger.error(f"API error during translation: {e}")
            raise

    async def translate_memo(
        self,
        memo_path: Path,
        output_path: Optional[Path] = None,
        target_lang: str = "zh-CN",
    ) -> TranslationResult:
        """Translate a memo file and save the result.

        Args:
            memo_path: Path to the source memo markdown file.
            output_path: Path to save translated memo. If None, auto-generates.
            target_lang: Target language code (default: "zh-CN").

        Returns:
            TranslationResult with translation details.
        """
        memo_path = Path(memo_path)
        if not memo_path.exists():
            raise FileNotFoundError(f"Memo not found: {memo_path}")

        # Read source content
        source_content = memo_path.read_text(encoding="utf-8")
        logger.info(f"Translating: {memo_path.name} ({len(source_content):,} chars)")

        # Perform translation
        translated_content, input_tokens, output_tokens = await self.translate(
            source_content,
            source_lang="en",
            target_lang=target_lang,
        )

        # Determine output path
        if output_path is None:
            # {TICKER}_memo_vF_{date}.md -> {TICKER}_memo_vF_{date}_zh.md
            stem = memo_path.stem
            output_path = memo_path.parent / f"{stem}_zh.md"

        # Save translated memo
        output_path.write_text(translated_content, encoding="utf-8")
        logger.info(f"Saved translation: {output_path.name}")

        return TranslationResult(
            source_path=memo_path,
            target_path=output_path,
            source_lang="en",
            target_lang=target_lang,
            source_content=source_content,
            translated_content=translated_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            timestamp=datetime.now(),
        )


async def translate_memo(
    memo_path: Path,
    output_path: Optional[Path] = None,
    target_lang: str = "zh-CN",
    model: str = MemoTranslator.DEFAULT_MODEL,
) -> TranslationResult:
    """Convenience function to translate a memo file.

    Args:
        memo_path: Path to the source memo markdown file.
        output_path: Path to save translated memo. If None, auto-generates.
        target_lang: Target language code (default: "zh-CN").
        model: Claude model to use (default: claude-sonnet-4).

    Returns:
        TranslationResult with translation details.
    """
    translator = MemoTranslator(model=model)
    return await translator.translate_memo(memo_path, output_path, target_lang)


# CLI support for standalone testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if len(sys.argv) < 2:
        print("Usage: python translator.py <memo_path>")
        sys.exit(1)

    memo_path = Path(sys.argv[1])
    result = asyncio.run(translate_memo(memo_path))

    print(f"\n{'='*60}")
    print(f"Translation Complete")
    print(f"{'='*60}")
    print(f"Source: {result.source_path}")
    print(f"Output: {result.target_path}")
    print(f"Tokens: {result.input_tokens:,} in / {result.output_tokens:,} out")
    print(f"Model: {result.model}")
