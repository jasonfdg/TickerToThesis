"""
VIC Memo Batch Processor - Process all remaining files in batches
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import statistics

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "vic" / "github_dump" / "extracted"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "memo_synthesis" / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(filepath: Path) -> dict:
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_year(date_str: str) -> int:
    if not date_str:
        return 0
    match = re.search(r'\b(20\d{2}|19\d{2})\b', date_str)
    return int(match.group(1)) if match else 0


def detect_valuation_methods(text: str) -> list:
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
    text_lower = text.lower()
    if is_short:
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
    structure["completeness_score"] = sum(structure.values()) / (len(structure) - 1)
    return structure


def calculate_decision_readiness(memo: dict, structure: dict) -> float:
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
    if memo.get("catalyst_text") and len(memo.get("catalyst_text", "")) > 50:
        score += 0.05
    return min(score, 1.0)


def analyze_batch(file_list: list) -> dict:
    """Analyze a batch of files and return structured results."""
    results = {
        "meta": {
            "total_files": len(file_list),
            "processed": 0,
            "errors": 0,
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
        "structural_elements": defaultdict(int),
        "metrics": {
            "description_lengths": [],
            "decision_readiness_scores": [],
            "completeness_scores": [],
        }
    }

    for filepath in file_list:
        try:
            memo = load_json_file(filepath)
            results["meta"]["processed"] += 1

            year = extract_year(memo.get("date", ""))
            results["distribution"]["by_year"][year] += 1

            position = memo.get("position_type", "unknown").lower()
            results["distribution"]["by_position"][position] += 1

            if memo.get("is_contest_winner"):
                results["distribution"]["winners"] += 1

            desc = memo.get("description_text", "") or ""
            catalyst = memo.get("catalyst_text", "") or ""
            full_text = desc + " " + catalyst
            is_short = position == "short"

            results["metrics"]["description_lengths"].append(len(desc))

            thesis_type = detect_thesis_type(full_text, is_short)
            results["distribution"]["by_thesis_type"][thesis_type] += 1

            for method in detect_valuation_methods(full_text):
                results["valuation_methods"][method] += 1

            for cat in detect_catalyst_types(full_text):
                results["catalyst_types"][cat] += 1

            for risk in detect_risk_factors(full_text):
                results["risk_factors"][risk] += 1

            structure = analyze_memo_structure(full_text)
            for key, val in structure.items():
                if key != "completeness_score" and val:
                    results["structural_elements"][key] += 1

            results["metrics"]["completeness_scores"].append(structure["completeness_score"])
            decision_ready = calculate_decision_readiness(memo, structure)
            results["metrics"]["decision_readiness_scores"].append(decision_ready)

        except Exception as e:
            results["meta"]["errors"] += 1

    # Calculate aggregates
    if results["metrics"]["description_lengths"]:
        results["metrics"]["avg_description_length"] = int(statistics.mean(results["metrics"]["description_lengths"]))
        results["metrics"]["median_description_length"] = int(statistics.median(results["metrics"]["description_lengths"]))
    if results["metrics"]["decision_readiness_scores"]:
        results["metrics"]["avg_decision_readiness"] = round(statistics.mean(results["metrics"]["decision_readiness_scores"]), 3)
    if results["metrics"]["completeness_scores"]:
        results["metrics"]["avg_completeness"] = round(statistics.mean(results["metrics"]["completeness_scores"]), 3)

    # Clean up for JSON
    del results["metrics"]["description_lengths"]
    del results["metrics"]["decision_readiness_scores"]
    del results["metrics"]["completeness_scores"]

    results["distribution"]["by_year"] = dict(results["distribution"]["by_year"])
    results["distribution"]["by_position"] = dict(results["distribution"]["by_position"])
    results["distribution"]["by_thesis_type"] = dict(results["distribution"]["by_thesis_type"])
    results["valuation_methods"] = dict(results["valuation_methods"])
    results["catalyst_types"] = dict(results["catalyst_types"])
    results["risk_factors"] = dict(results["risk_factors"])
    results["structural_elements"] = dict(results["structural_elements"])

    return results


def merge_results(cumulative: dict, batch: dict) -> dict:
    """Merge batch results into cumulative results."""
    if not cumulative:
        return batch

    # Merge meta
    cumulative["meta"]["total_files"] += batch["meta"]["total_files"]
    cumulative["meta"]["processed"] += batch["meta"]["processed"]
    cumulative["meta"]["errors"] += batch["meta"]["errors"]

    # Merge distributions
    for year, count in batch["distribution"]["by_year"].items():
        cumulative["distribution"]["by_year"][year] = cumulative["distribution"]["by_year"].get(year, 0) + count

    for pos, count in batch["distribution"]["by_position"].items():
        cumulative["distribution"]["by_position"][pos] = cumulative["distribution"]["by_position"].get(pos, 0) + count

    for thesis, count in batch["distribution"]["by_thesis_type"].items():
        cumulative["distribution"]["by_thesis_type"][thesis] = cumulative["distribution"]["by_thesis_type"].get(thesis, 0) + count

    cumulative["distribution"]["winners"] += batch["distribution"]["winners"]

    # Merge counters
    for method, count in batch["valuation_methods"].items():
        cumulative["valuation_methods"][method] = cumulative["valuation_methods"].get(method, 0) + count

    for cat, count in batch["catalyst_types"].items():
        cumulative["catalyst_types"][cat] = cumulative["catalyst_types"].get(cat, 0) + count

    for risk, count in batch["risk_factors"].items():
        cumulative["risk_factors"][risk] = cumulative["risk_factors"].get(risk, 0) + count

    for elem, count in batch["structural_elements"].items():
        cumulative["structural_elements"][elem] = cumulative["structural_elements"].get(elem, 0) + count

    # Running average for metrics (weighted)
    old_n = cumulative["meta"]["processed"] - batch["meta"]["processed"]
    new_n = batch["meta"]["processed"]
    total_n = cumulative["meta"]["processed"]

    if "avg_description_length" in batch["metrics"] and "avg_description_length" in cumulative["metrics"]:
        cumulative["metrics"]["avg_description_length"] = int(
            (cumulative["metrics"]["avg_description_length"] * old_n + batch["metrics"]["avg_description_length"] * new_n) / total_n
        )

    if "avg_decision_readiness" in batch["metrics"] and "avg_decision_readiness" in cumulative["metrics"]:
        cumulative["metrics"]["avg_decision_readiness"] = round(
            (cumulative["metrics"]["avg_decision_readiness"] * old_n + batch["metrics"]["avg_decision_readiness"] * new_n) / total_n, 3
        )

    if "avg_completeness" in batch["metrics"] and "avg_completeness" in cumulative["metrics"]:
        cumulative["metrics"]["avg_completeness"] = round(
            (cumulative["metrics"]["avg_completeness"] * old_n + batch["metrics"]["avg_completeness"] * new_n) / total_n, 3
        )

    return cumulative


def get_all_files_sorted():
    """Get all files sorted by date."""
    all_files = list(DATA_DIR.glob("*.json"))
    file_dates = []

    for f in all_files:
        try:
            data = load_json_file(f)
            year = extract_year(data.get("date", ""))
            is_priority = data.get("is_contest_winner") or data.get("position_type", "").lower() == "short"
            file_dates.append((f, year, is_priority))
        except:
            file_dates.append((f, 0, False))

    return file_dates


def main():
    print("=" * 60)
    print("VIC Memo Full Corpus Processor")
    print("=" * 60)

    # Get all files
    print("\nLoading file metadata...")
    file_data = get_all_files_sorted()
    print(f"Total files: {len(file_data)}")

    # Separate priority and non-priority
    priority_files = [f for f, _, is_p in file_data if is_p]
    non_priority = [(f, y) for f, y, is_p in file_data if not is_p]

    # Sort non-priority by year
    non_priority.sort(key=lambda x: x[1])
    non_priority_files = [f for f, _ in non_priority]

    print(f"Priority files (winners + shorts): {len(priority_files)}")
    print(f"Non-priority files: {len(non_priority_files)}")

    # Load existing cumulative results if available
    cumulative_file = OUTPUT_DIR / "cumulative_analysis.json"
    if cumulative_file.exists():
        with open(cumulative_file, 'r') as f:
            cumulative = json.load(f)
        print(f"\nResuming from existing analysis: {cumulative['meta']['processed']} files processed")
        start_iteration = cumulative.get("last_iteration", 1) + 1
    else:
        cumulative = None
        start_iteration = 1

    # Process priority files if not done
    if start_iteration == 1:
        print(f"\n{'='*60}")
        print("ITERATION 1: Processing priority files (winners + shorts)")
        print(f"{'='*60}")

        batch_result = analyze_batch(priority_files)
        batch_result["meta"]["iteration"] = 1
        batch_result["meta"]["batch_type"] = "priority"

        cumulative = batch_result
        cumulative["last_iteration"] = 1

        with open(cumulative_file, 'w') as f:
            json.dump(cumulative, f, indent=2)

        print(f"  Processed: {batch_result['meta']['processed']}")
        print(f"  Errors: {batch_result['meta']['errors']}")
        print(f"  Avg Decision Readiness: {batch_result['metrics'].get('avg_decision_readiness', 'N/A')}")

        start_iteration = 2

    # Process remaining files in batches of 500
    batch_size = 500
    batches = [non_priority_files[i:i + batch_size] for i in range(0, len(non_priority_files), batch_size)]

    for i, batch_files in enumerate(batches, start=2):
        if i < start_iteration:
            continue

        # Get year range for this batch
        years = set()
        for f in batch_files:
            try:
                data = load_json_file(f)
                year = extract_year(data.get("date", ""))
                if year > 0:
                    years.add(year)
            except:
                pass

        year_range = f"{min(years)}-{max(years)}" if years else "N/A"

        print(f"\n{'='*60}")
        print(f"ITERATION {i}: Processing batch ({year_range})")
        print(f"{'='*60}")

        batch_result = analyze_batch(batch_files)
        batch_result["meta"]["iteration"] = i
        batch_result["meta"]["year_range"] = year_range

        cumulative = merge_results(cumulative, batch_result)
        cumulative["last_iteration"] = i
        cumulative["meta"]["timestamp"] = datetime.now().isoformat()

        # Save checkpoint
        with open(cumulative_file, 'w') as f:
            json.dump(cumulative, f, indent=2)

        print(f"  Batch processed: {batch_result['meta']['processed']}")
        print(f"  Cumulative total: {cumulative['meta']['processed']}")
        print(f"  Avg Decision Readiness: {cumulative['metrics'].get('avg_decision_readiness', 'N/A')}")

    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Total files processed: {cumulative['meta']['processed']}")
    print(f"Total errors: {cumulative['meta']['errors']}")
    print(f"Winners: {cumulative['distribution']['winners']}")
    print(f"Shorts: {cumulative['distribution']['by_position'].get('short', 0)}")
    print(f"Longs: {cumulative['distribution']['by_position'].get('long', 0)}")
    print(f"Avg Description Length: {cumulative['metrics'].get('avg_description_length', 'N/A')}")
    print(f"Avg Decision Readiness: {cumulative['metrics'].get('avg_decision_readiness', 'N/A')}")
    print(f"\nResults saved to: {cumulative_file}")

    return cumulative


if __name__ == "__main__":
    main()
