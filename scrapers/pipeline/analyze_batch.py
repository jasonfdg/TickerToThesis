"""
VIC Memo Batch Analyzer
Processes a batch of memo JSON files and extracts structured patterns.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import statistics

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "vic" / "github_dump" / "extracted"


def load_json_file(filepath: Path) -> dict:
    """Load a single JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_year(date_str: str) -> int:
    """Extract year from date string."""
    if not date_str:
        return 0
    match = re.search(r'\b(20\d{2}|19\d{2})\b', date_str)
    return int(match.group(1)) if match else 0


def detect_valuation_methods(text: str) -> list:
    """Detect valuation methods mentioned in the text."""
    text_lower = text.lower()
    methods = []

    patterns = {
        "DCF": r'\b(dcf|discounted cash flow|npv|net present value)\b',
        "P/E Multiple": r'\b(p/e|pe ratio|earnings multiple|price.to.earnings)\b',
        "EV/EBITDA": r'\b(ev/ebitda|enterprise value.*ebitda|ebitda multiple)\b',
        "EV/Revenue": r'\b(ev/revenue|ev/sales|price.to.sales|p/s)\b',
        "Sum-of-Parts": r'\b(sum.of.parts|sotp|break.?up value|hidden asset)\b',
        "NAV/Book Value": r'\b(nav|net asset value|book value|tangible book)\b',
        "FCF Yield": r'\b(fcf yield|free cash flow yield|cash flow multiple)\b',
        "Dividend Yield": r'\b(dividend yield|dividend discount|ddm)\b',
        "Replacement Cost": r'\b(replacement cost|reproduction value)\b',
        "Comp Analysis": r'\b(compar|peer|trading at.*vs|discount to peers)\b',
        "LBO/Takeout": r'\b(lbo|leveraged buyout|take.?out|acquisition target)\b',
    }

    for method, pattern in patterns.items():
        if re.search(pattern, text_lower):
            methods.append(method)

    return methods


def detect_catalyst_types(text: str) -> list:
    """Detect catalyst types mentioned in the text."""
    text_lower = text.lower()
    catalysts = []

    patterns = {
        "Earnings Release": r'\b(earnings|quarterly report|guidance|beat estimates)\b',
        "M&A/Buyout": r'\b(acquisition|merger|buyout|take.?over|strategic buyer)\b',
        "Spin-off/Split": r'\b(spin.?off|split.?off|separation|carve.?out)\b',
        "Management Change": r'\b(new (ceo|management|cfo)|activist|board change)\b',
        "Product Launch": r'\b(new product|launch|fda approval|patent)\b',
        "Restructuring": r'\b(restructur|turnaround|cost.?cut|margin improvement)\b',
        "Capital Return": r'\b(buyback|dividend|special dividend|return capital)\b',
        "Debt Refinancing": r'\b(refinanc|deleverag|debt pay.?down|balance sheet)\b',
        "Regulatory": r'\b(regulat|approval|license|permit|compliance)\b',
        "Macro/Cycle": r'\b(cycle|recovery|macro|commodity price|industry upturn)\b',
        "Short Squeeze": r'\b(short squeeze|short interest|covering|squeeze)\b',
        "Fraud/Accounting": r'\b(fraud|accounting|restatement|sec investigation)\b',
    }

    for catalyst, pattern in patterns.items():
        if re.search(pattern, text_lower):
            catalysts.append(catalyst)

    return catalysts


def detect_risk_factors(text: str) -> list:
    """Detect risk factors mentioned in the text."""
    text_lower = text.lower()
    risks = []

    patterns = {
        "Competition": r'\b(competit|market share|pricing pressure|new entrant)\b',
        "Leverage/Debt": r'\b(leverag|debt|covenant|refinanc|bankruptcy)\b',
        "Management Quality": r'\b(management (risk|quality)|key person|governance)\b',
        "Execution Risk": r'\b(execution|implement|turnaround fail|integration)\b',
        "Macro/Cyclical": r'\b(recession|economic|cyclical|downturn|macro)\b',
        "Regulatory": r'\b(regulatory|government|policy|litigation|legal)\b',
        "Technology/Disruption": r'\b(technolog|disruption|obsolete|secular decline)\b',
        "Customer Concentration": r'\b(customer concentration|key customer|revenue concentration)\b',
        "Capital Needs": r'\b(capital (need|raise)|dilution|funding|cash burn)\b',
        "Commodity Exposure": r'\b(commodity|input cost|raw material|oil price)\b',
        "Currency": r'\b(currency|fx|foreign exchange|translation)\b',
    }

    for risk, pattern in patterns.items():
        if re.search(pattern, text_lower):
            risks.append(risk)

    return risks


def detect_thesis_type(text: str, is_short: bool) -> str:
    """Detect the primary thesis type."""
    text_lower = text.lower()

    if is_short:
        # Short thesis types
        if re.search(r'\b(fraud|accounting|overstat|fake|scam)\b', text_lower):
            return "Fraud/Accounting Issues"
        elif re.search(r'\b(overvalue|bubble|hype|multiple compress)\b', text_lower):
            return "Overvaluation"
        elif re.search(r'\b(secular decline|disruption|obsolete|terminal)\b', text_lower):
            return "Secular Decline"
        elif re.search(r'\b(broken business|deteriorat|declining)\b', text_lower):
            return "Business Deterioration"
        elif re.search(r'\b(catalyst|near.?term|imminent)\b', text_lower):
            return "Catalyst-Driven Short"
        else:
            return "General Short"
    else:
        # Long thesis types
        if re.search(r'\b(compounder|moat|durable|quality|franchise)\b', text_lower):
            return "Long-term Compounder"
        elif re.search(r'\b(deep value|cigar butt|asset play|liquidat)\b', text_lower):
            return "Deep Value"
        elif re.search(r'\b(special situation|event|spin|merger|arbitrage)\b', text_lower):
            return "Special Situation"
        elif re.search(r'\b(turnaround|restructur|recover|cyclical)\b', text_lower):
            return "Turnaround/Cyclical"
        elif re.search(r'\b(growth|expand|scale|market share)\b', text_lower):
            return "Growth at Reasonable Price"
        elif re.search(r'\b(sum.?of.?parts|hidden|underappreciat|misunderstood)\b', text_lower):
            return "Hidden Value/Misunderstood"
        else:
            return "General Long"


def analyze_memo_structure(text: str) -> dict:
    """Analyze the structural elements of a memo."""
    text_lower = text.lower()

    structure = {
        "has_company_overview": bool(re.search(r'\b(company overview|business description|background|about)\b', text_lower)),
        "has_thesis_statement": bool(re.search(r'\b(thesis|investment case|why|opportunity|summary)\b', text_lower)),
        "has_valuation_section": bool(re.search(r'\b(valuation|worth|target|upside|price target)\b', text_lower)),
        "has_risk_section": bool(re.search(r'\b(risk|downside|bear case|what could go wrong)\b', text_lower)),
        "has_catalyst_section": bool(re.search(r'\b(catalyst|trigger|timing|when)\b', text_lower)),
        "has_mgmt_discussion": bool(re.search(r'\b(management|ceo|leadership|insider|ownership)\b', text_lower)),
        "has_financials": bool(re.search(r'\b(revenue|earnings|ebitda|margin|growth rate)\b', text_lower)),
        "has_competitive_analysis": bool(re.search(r'\b(competit|moat|advantage|market position|peers)\b', text_lower)),
        "has_variant_view": bool(re.search(r'\b(market (miss|wrong|doesn.t understand)|variant|consensus)\b', text_lower)),
    }

    structure["completeness_score"] = sum(structure.values()) / len(structure)
    return structure


def calculate_decision_readiness(memo: dict, structure: dict) -> float:
    """Calculate how decision-ready a memo is."""
    score = 0.0
    weights = {
        "has_thesis_statement": 0.20,
        "has_valuation_section": 0.20,
        "has_risk_section": 0.15,
        "has_catalyst_section": 0.15,
        "has_variant_view": 0.10,
        "has_financials": 0.10,
        "has_competitive_analysis": 0.10,
    }

    for key, weight in weights.items():
        if structure.get(key, False):
            score += weight

    # Bonus for catalyst text
    if memo.get("catalyst_text") and len(memo.get("catalyst_text", "")) > 50:
        score += 0.05

    return min(score, 1.0)


def analyze_batch(file_list: list) -> dict:
    """Analyze a batch of memo files."""
    results = {
        "meta": {
            "total_files": len(file_list),
            "processed": 0,
            "errors": 0,
            "timestamp": datetime.now().isoformat()
        },
        "distribution": {
            "by_year": defaultdict(int),
            "by_position": defaultdict(int),
            "by_thesis_type": defaultdict(int),
            "winners": 0,
        },
        "valuation_methods": Counter(),
        "catalyst_types": Counter(),
        "risk_factors": Counter(),
        "structural_elements": {
            "completeness_scores": [],
            "decision_readiness_scores": [],
            "element_frequencies": defaultdict(int),
        },
        "content_metrics": {
            "description_lengths": [],
            "catalyst_lengths": [],
            "has_catalyst_text": 0,
        },
        "sample_memos": {
            "winners": [],
            "shorts": [],
            "high_quality": [],
        }
    }

    for filepath in file_list:
        try:
            memo = load_json_file(filepath)
            results["meta"]["processed"] += 1

            # Basic distribution
            year = extract_year(memo.get("date", ""))
            results["distribution"]["by_year"][year] += 1

            position = memo.get("position_type", "unknown").lower()
            results["distribution"]["by_position"][position] += 1

            if memo.get("is_contest_winner"):
                results["distribution"]["winners"] += 1

            # Content analysis
            desc = memo.get("description_text", "") or ""
            catalyst = memo.get("catalyst_text", "") or ""

            results["content_metrics"]["description_lengths"].append(len(desc))
            results["content_metrics"]["catalyst_lengths"].append(len(catalyst))
            if len(catalyst) > 20:
                results["content_metrics"]["has_catalyst_text"] += 1

            # Detect patterns
            full_text = desc + " " + catalyst
            is_short = position == "short"

            thesis_type = detect_thesis_type(full_text, is_short)
            results["distribution"]["by_thesis_type"][thesis_type] += 1

            for method in detect_valuation_methods(full_text):
                results["valuation_methods"][method] += 1

            for catalyst_type in detect_catalyst_types(full_text):
                results["catalyst_types"][catalyst_type] += 1

            for risk in detect_risk_factors(full_text):
                results["risk_factors"][risk] += 1

            # Structure analysis
            structure = analyze_memo_structure(full_text)
            results["structural_elements"]["completeness_scores"].append(structure["completeness_score"])

            for key, val in structure.items():
                if key != "completeness_score" and val:
                    results["structural_elements"]["element_frequencies"][key] += 1

            decision_ready = calculate_decision_readiness(memo, structure)
            results["structural_elements"]["decision_readiness_scores"].append(decision_ready)

            # Collect sample memos
            memo_summary = {
                "id": memo.get("id", ""),
                "ticker": memo.get("ticker", ""),
                "company": memo.get("company_name", ""),
                "date": memo.get("date", ""),
                "position": position,
                "thesis_type": thesis_type,
                "decision_readiness": decision_ready,
                "desc_length": len(desc),
            }

            if memo.get("is_contest_winner") and len(results["sample_memos"]["winners"]) < 20:
                results["sample_memos"]["winners"].append(memo_summary)

            if is_short and len(results["sample_memos"]["shorts"]) < 20:
                results["sample_memos"]["shorts"].append(memo_summary)

            if decision_ready > 0.8 and len(results["sample_memos"]["high_quality"]) < 20:
                results["sample_memos"]["high_quality"].append(memo_summary)

        except Exception as e:
            results["meta"]["errors"] += 1
            continue

    # Calculate summary statistics
    if results["content_metrics"]["description_lengths"]:
        results["content_metrics"]["avg_description_length"] = int(
            statistics.mean(results["content_metrics"]["description_lengths"])
        )
        results["content_metrics"]["median_description_length"] = int(
            statistics.median(results["content_metrics"]["description_lengths"])
        )

    if results["structural_elements"]["completeness_scores"]:
        results["structural_elements"]["avg_completeness"] = round(
            statistics.mean(results["structural_elements"]["completeness_scores"]), 3
        )
        results["structural_elements"]["avg_decision_readiness"] = round(
            statistics.mean(results["structural_elements"]["decision_readiness_scores"]), 3
        )

    # Convert defaultdicts and Counters for JSON serialization
    results["distribution"]["by_year"] = dict(results["distribution"]["by_year"])
    results["distribution"]["by_position"] = dict(results["distribution"]["by_position"])
    results["distribution"]["by_thesis_type"] = dict(results["distribution"]["by_thesis_type"])
    results["valuation_methods"] = dict(results["valuation_methods"])
    results["catalyst_types"] = dict(results["catalyst_types"])
    results["risk_factors"] = dict(results["risk_factors"])
    results["structural_elements"]["element_frequencies"] = dict(
        results["structural_elements"]["element_frequencies"]
    )

    # Remove raw lists to save space
    del results["content_metrics"]["description_lengths"]
    del results["content_metrics"]["catalyst_lengths"]
    del results["structural_elements"]["completeness_scores"]
    del results["structural_elements"]["decision_readiness_scores"]

    return results


def get_priority_files() -> list:
    """Get winner + short files."""
    all_files = list(DATA_DIR.glob("*.json"))
    priority = []

    for f in all_files:
        try:
            data = load_json_file(f)
            if data.get("is_contest_winner") or data.get("position_type", "").lower() == "short":
                priority.append(f)
        except:
            continue

    return priority


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "priority":
        print("Analyzing priority files (winners + shorts)...")
        files = get_priority_files()
    else:
        print("Analyzing all files...")
        files = list(DATA_DIR.glob("*.json"))

    print(f"Processing {len(files)} files...")
    results = analyze_batch(files)

    # Output results
    output_file = PROJECT_ROOT / "analysis" / "memo_synthesis" / "output" / "batch_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Processed: {results['meta']['processed']}")
    print(f"  Errors: {results['meta']['errors']}")
    print(f"  Winners: {results['distribution']['winners']}")
    print(f"  Avg Description Length: {results['content_metrics'].get('avg_description_length', 'N/A')}")
    print(f"  Avg Decision Readiness: {results['structural_elements'].get('avg_decision_readiness', 'N/A')}")

    return results


if __name__ == "__main__":
    main()
