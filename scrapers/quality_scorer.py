"""
Quality Scorer for Buyside Research Memos
Based on buyside_memo_engine_v0.2.0.md criteria

Top 25% quartile = Score 6+ on 7-point scale
"""

import re
from typing import Dict, Optional

# Uncertainty phrases that indicate low conviction (auto-penalize)
UNCERTAINTY_PHRASES = [
    r"tell me what i'?m missing",
    r"hard to know",
    r"i'?m not sure",
    r"could be wrong",
    r"not certain",
    r"difficult to say",
    r"unclear",
    r"time will tell",
    r"we'?ll see",
    r"maybe i'?m wrong",
]

# Evidence quality indicators
PRIMARY_RESEARCH_INDICATORS = [
    r"channel check",
    r"spoke with",
    r"according to .{1,50} (ceo|cfo|cto|management|executive|analyst|expert)",
    r"industry expert",
    r"former employee",
    r"supplier",
    r"customer",
    r"competitor",
    r"site visit",
    r"store check",
]

# Quote detection pattern
QUOTE_PATTERN = r'["\u201c].{10,200}["\u201d]\s*[-\u2014\u2013]\s*\w+'

# Valuation method indicators
VALUATION_METHODS = [
    r"ev/ebitda",
    r"p/e\s*(ratio|multiple)?",
    r"dcf",
    r"discounted cash flow",
    r"sum[- ]of[- ](the[- ])?parts",
    r"liquidation value",
    r"book value",
    r"nav",
    r"net asset value",
    r"replacement cost",
    r"fcf yield",
    r"free cash flow",
]

# Scenario indicators
SCENARIO_INDICATORS = [
    r"bull case",
    r"bear case",
    r"base case",
    r"upside",
    r"downside",
    r"best case",
    r"worst case",
    r"sensitivity",
    r"scenario",
]

# Risk quality indicators
KILL_CONDITION_PATTERNS = [
    r"if .{5,100} (exit|sell|wrong|fails)",
    r"thesis breaks if",
    r"key risk",
    r"kill the thesis",
    r"stop[- ]?loss",
    r"would exit",
]

# Catalyst timing indicators
CATALYST_TIMING_PATTERNS = [
    r"q[1-4]\s*20\d{2}",
    r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*20\d{2}",
    r"by (year[- ]?end|end of year)",
    r"within \d+ (months?|quarters?|weeks?)",
    r"expected (in|by|around)",
]


def count_pattern_matches(text: str, patterns: list) -> int:
    """Count how many patterns match in the text."""
    text_lower = text.lower()
    count = 0
    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        count += len(matches)
    return count


def score_thesis_conviction(text: str) -> float:
    """
    Score thesis conviction (0-10).
    Penalize uncertainty language heavily.
    """
    text_lower = text.lower()
    uncertainty_count = count_pattern_matches(text, UNCERTAINTY_PHRASES)

    # Start at 7, penalize 2 points per uncertainty phrase
    score = 7.0 - (uncertainty_count * 2.0)

    # Check for strong conviction language
    conviction_phrases = [
        r"we believe",
        r"conviction",
        r"high confidence",
        r"compelling",
        r"significant upside",
        r"asymmetric",
    ]
    conviction_count = count_pattern_matches(text, conviction_phrases)
    score += min(conviction_count * 0.5, 2.0)

    return max(0.0, min(10.0, score))


def score_evidence_quality(text: str) -> float:
    """
    Score evidence quality (0-10).
    Primary research with quotes scores highest.
    """
    # Count primary research indicators
    primary_count = count_pattern_matches(text, PRIMARY_RESEARCH_INDICATORS)

    # Count attributed quotes
    quotes = re.findall(QUOTE_PATTERN, text)
    quote_count = len(quotes)

    # Base score from primary research
    score = min(primary_count * 1.5, 5.0)

    # Bonus for attributed quotes (elite memos avg 2.3 quotes)
    score += min(quote_count * 1.5, 4.0)

    # Penalty if no evidence indicators at all
    if primary_count == 0 and quote_count == 0:
        # Check for at least SEC filing references
        sec_refs = len(re.findall(r"10-?k|10-?q|8-?k|proxy|annual report", text.lower()))
        score = min(sec_refs * 0.5, 2.0)

    return max(0.0, min(10.0, score))


def score_valuation_rigor(text: str) -> float:
    """
    Score valuation rigor (0-10).
    Multiple methods + scenarios = high score.
    """
    # Count valuation methods used
    methods_count = count_pattern_matches(text, VALUATION_METHODS)

    # Check for scenario analysis
    scenarios_count = count_pattern_matches(text, SCENARIO_INDICATORS)

    # Base score from methods
    score = min(methods_count * 1.5, 5.0)

    # Bonus for scenarios (elite memos have 83% scenarios)
    if scenarios_count >= 2:
        score += 4.0
    elif scenarios_count == 1:
        score += 2.0

    # Check for specific price targets
    price_targets = re.findall(r"\$\d+(?:\.\d+)?(?:\s*(?:target|price|upside|worth))?", text)
    if len(price_targets) >= 2:
        score += 1.0

    return max(0.0, min(10.0, score))


def score_risk_honesty(text: str) -> float:
    """
    Score risk honesty (0-10).
    Specific risks with kill conditions score highest.
    """
    text_lower = text.lower()

    # Check for risk section
    has_risk_section = bool(re.search(r"risk|downside|bear case|what could go wrong", text_lower))

    # Count kill conditions
    kill_conditions = count_pattern_matches(text, KILL_CONDITION_PATTERNS)

    # Count specific risk mentions
    specific_risks = len(re.findall(r"risk[s]?\s*(?:include|are|:)", text_lower))

    score = 0.0
    if has_risk_section:
        score += 3.0

    # Kill conditions are gold
    score += min(kill_conditions * 2.0, 5.0)

    # Specific enumerated risks
    score += min(specific_risks * 1.0, 2.0)

    return max(0.0, min(10.0, score))


def score_decision_readiness(text: str) -> float:
    """
    Score decision readiness (0-10).
    Actionable: target, timing, downside floor.
    """
    score = 0.0
    text_lower = text.lower()

    # Check for price target
    has_target = bool(re.search(r"target|worth|fair value|intrinsic value", text_lower))
    if has_target:
        score += 3.0

    # Check for catalyst timing
    timing_count = count_pattern_matches(text, CATALYST_TIMING_PATTERNS)
    score += min(timing_count * 1.5, 3.0)

    # Check for downside floor (elite trait)
    downside_patterns = [
        r"downside.{1,30}\$\d+",
        r"\$\d+.{1,30}downside",
        r"floor",
        r"limited downside",
        r"protected",
        r"margin of safety",
    ]
    downside_count = count_pattern_matches(text, downside_patterns)
    score += min(downside_count * 1.5, 3.0)

    # Check for position sizing guidance
    sizing_patterns = [r"position size", r"% of portfolio", r"full position", r"starter position"]
    if count_pattern_matches(text, sizing_patterns) > 0:
        score += 1.0

    return max(0.0, min(10.0, score))


def score_memo(content: str, min_word_count: int = 500, quality_threshold: float = 5.0) -> Dict:
    """
    Score a buyside memo against quality criteria.

    Returns dict with:
    - Individual dimension scores (0-10)
    - Weighted total (0-10)
    - passes_quality_bar (bool) - True if >= quality_threshold (default 5.0)

    Note: Threshold lowered from 6.0 to 5.0 to accommodate different report formats
    (short-seller reports, hedge fund letters) that are inherently high quality
    but structured differently from traditional VIC memos.
    """
    # Check minimum length
    word_count = len(content.split())
    if word_count < min_word_count:
        return {
            "variant_view_clarity": 0,
            "evidence_quality": 0,
            "valuation_rigor": 0,
            "risk_honesty": 0,
            "decision_readiness": 0,
            "weighted_total": 0,
            "passes_quality_bar": False,
            "word_count": word_count,
            "rejection_reason": f"Too short: {word_count} words (min {min_word_count})"
        }

    # Score each dimension
    variant_view = score_thesis_conviction(content)
    evidence = score_evidence_quality(content)
    valuation = score_valuation_rigor(content)
    risk = score_risk_honesty(content)
    decision = score_decision_readiness(content)

    # Weighted total (from memo engine v0.2.0)
    weighted = (
        variant_view * 0.25 +
        evidence * 0.25 +
        valuation * 0.20 +
        risk * 0.15 +
        decision * 0.15
    )

    return {
        "variant_view_clarity": round(variant_view, 1),
        "evidence_quality": round(evidence, 1),
        "valuation_rigor": round(valuation, 1),
        "risk_honesty": round(risk, 1),
        "decision_readiness": round(decision, 1),
        "weighted_total": round(weighted, 1),
        "passes_quality_bar": weighted >= quality_threshold,
        "word_count": word_count,
        "rejection_reason": None if weighted >= quality_threshold else f"Score {weighted:.1f} below {quality_threshold} threshold"
    }


def quick_quality_check(content: str) -> bool:
    """
    Quick check if content is likely to pass quality bar.
    Use for filtering before full extraction.
    More lenient to accommodate different report formats.
    """
    word_count = len(content.split())
    if word_count < 400:  # Lowered from 500
        return False

    text_lower = content.lower()

    # Check for valuation or financial analysis content
    has_valuation = bool(re.search(r"ev/ebitda|p/e|dcf|valuation|worth|target|revenue|earnings|margin", text_lower))

    # Check for thesis/investment/research content
    has_thesis = bool(re.search(r"thesis|investment|opportunity|undervalued|upside|overvalued|short|fraud|accounting|manipulation", text_lower))

    # Check for excessive uncertainty (auto-reject) - but more lenient
    uncertainty_count = count_pattern_matches(content, UNCERTAINTY_PHRASES)
    if uncertainty_count > 4:  # Raised from 2
        return False

    # Pass if has either valuation OR thesis content (more lenient)
    return has_valuation or has_thesis


if __name__ == "__main__":
    # Test with sample text
    test_text = """
    Investment Thesis: We believe XYZ Corp is significantly undervalued at current prices.

    Our channel checks with industry experts suggest the company's new product line will
    drive 20% revenue growth. "The demand is unprecedented" - Former VP of Sales.

    Valuation: At current prices, the stock trades at 8x EV/EBITDA vs peers at 12x.
    Bull case: $50 (15x EBITDA)
    Base case: $40 (12x EBITDA)
    Bear case: $25 (8x EBITDA)

    Risks:
    - If customer churn exceeds 15%, thesis breaks - would exit below $20
    - Competition from larger players

    Catalyst: Q2 2024 earnings should show inflection in margins.

    Downside floor at $22 based on liquidation value.
    """

    result = score_memo(test_text)
    print("Quality Score Results:")
    for k, v in result.items():
        print(f"  {k}: {v}")
