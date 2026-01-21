"""
Report Saver
============
File I/O for interim and final reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .config import (
        INVESTING_TYPES,
        get_final_memo_path,
        get_final_pdf_path,
        get_interim_dir,
        get_output_dir,
        get_pipeline_state_path,
        get_initial_scout_path,
        get_source_scout_path,
    )
    from .models import AgentReport, AgentRole, PipelineState
except ImportError:
    from config import (
        INVESTING_TYPES,
        get_final_memo_path,
        get_final_pdf_path,
        get_interim_dir,
        get_output_dir,
        get_pipeline_state_path,
        get_initial_scout_path,
        get_source_scout_path,
    )
    from models import AgentReport, AgentRole, PipelineState

logger = logging.getLogger(__name__)


class ReportSaver:
    """
    Handles saving and loading of all report artifacts.

    Directory structure:
    2 - report output/TICKER_V#_YYYY-MM-DD/
    ├── interim/
    │   ├── initial_scout.md                    (genesis phase)
    │   ├── analyst_*_v1.md ... analyst_*_v5.md (30 files)
    │   ├── rd_review_*_v1.md ... rd_review_*_v5.md (30 files)
    │   ├── source_scout_v1.md ... v4.md        (4 files)
    │   ├── ${TICKER}_webSource.json
    │   └── ${TICKER}_pipeline_state.json
    ├── ${TICKER}_memo_EN.md
    ├── ${TICKER}_memo_EN.pdf
    ├── ${TICKER}_memo_CN.md
    └── ${TICKER}_memo_CN.pdf
    """

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.output_dir = get_output_dir(self.ticker)
        self.interim_dir = get_interim_dir(self.ticker)

    def _get_analyst_filename(self, type_id: int, iteration: int) -> str:
        """Get filename for an analyst report."""
        short_name = INVESTING_TYPES[type_id]["short_name"]
        return f"analyst_{short_name}_v{iteration}.md"

    def _get_rd_review_filename(self, type_id: int, iteration: int) -> str:
        """Get filename for an RD review."""
        short_name = INVESTING_TYPES[type_id]["short_name"]
        return f"rd_review_{short_name}_v{iteration}.md"

    def save_analyst_report(self, report: AgentReport) -> Path:
        """
        Save an analyst report to the interim directory.

        Args:
            report: The AgentReport to save

        Returns:
            Path to the saved file
        """
        if report.investing_type_id is None:
            raise ValueError("Analyst report must have investing_type_id")

        filename = self._get_analyst_filename(report.investing_type_id, report.iteration)
        filepath = self.interim_dir / filename

        # Add header with metadata
        type_name = INVESTING_TYPES[report.investing_type_id]["name"]
        header = f"""---
ticker: {self.ticker}
analyst_type: {type_name}
iteration: {report.iteration}
timestamp: {report.timestamp.isoformat()}
tokens_in: {report.token_usage.input_tokens}
tokens_out: {report.token_usage.output_tokens}
---

"""
        content = header + report.content

        filepath.write_text(content, encoding="utf-8")
        logger.debug(f"Saved analyst report: {filepath}")
        return filepath

    def save_rd_review(self, report: AgentReport) -> Path:
        """
        Save an RD review to the interim directory.

        Args:
            report: The AgentReport to save

        Returns:
            Path to the saved file
        """
        if report.investing_type_id is None:
            raise ValueError("RD review must have investing_type_id")

        filename = self._get_rd_review_filename(report.investing_type_id, report.iteration)
        filepath = self.interim_dir / filename

        # Add header with metadata
        type_name = INVESTING_TYPES[report.investing_type_id]["name"]
        header = f"""---
ticker: {self.ticker}
review_for: {type_name}
iteration: {report.iteration}
timestamp: {report.timestamp.isoformat()}
tokens_in: {report.token_usage.input_tokens}
tokens_out: {report.token_usage.output_tokens}
---

"""
        content = header + report.content

        filepath.write_text(content, encoding="utf-8")
        logger.debug(f"Saved RD review: {filepath}")
        return filepath

    def save_initial_scout(self, report: AgentReport) -> Path:
        """
        Save the genesis/initial source scout report.

        Args:
            report: The initial source scout AgentReport

        Returns:
            Path to the saved file
        """
        filepath = get_initial_scout_path(self.ticker)

        header = f"""---
ticker: {self.ticker}
stage: initial_scout
timestamp: {report.timestamp.isoformat()}
tokens_in: {report.token_usage.input_tokens}
tokens_out: {report.token_usage.output_tokens}
---

"""
        content = header + report.content

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved initial scout: {filepath}")
        return filepath

    def save_final(self, report: AgentReport, lang: str = "EN") -> Path:
        """
        Save the final polished memo.

        Args:
            report: The final AgentReport
            lang: Language code ("EN" or "CN")

        Returns:
            Path to the saved file
        """
        filepath = get_final_memo_path(self.ticker, lang)

        # Final memo gets minimal header - it's the deliverable
        header = f"""---
ticker: {self.ticker}
lang: {lang}
generated: {report.timestamp.strftime('%Y-%m-%d')}
---

"""
        content = header + report.content

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved final memo ({lang}): {filepath}")
        return filepath

    def save_source_scout(self, report: AgentReport, iteration: int) -> Path:
        """
        Save the web research report for an iteration.

        Args:
            report: The web research AgentReport
            iteration: The iteration number

        Returns:
            Path to the saved file
        """
        filepath = get_source_scout_path(self.ticker, iteration)

        header = f"""---
ticker: {self.ticker}
stage: source_scout
iteration: {iteration}
timestamp: {report.timestamp.isoformat()}
tokens_in: {report.token_usage.input_tokens}
tokens_out: {report.token_usage.output_tokens}
---

"""
        content = header + report.content

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved web research (iteration {iteration}): {filepath}")
        return filepath

    def load_source_scout(self, iteration: int) -> Optional[str]:
        """
        Load web research report for an iteration.

        Args:
            iteration: The iteration number

        Returns:
            The web research content (without metadata header), or None if not found
        """
        filepath = get_source_scout_path(self.ticker, iteration)

        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")

        # Strip YAML header if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def save_iteration(
        self,
        iteration: int,
        analyst_reports: Dict[int, AgentReport],
        rd_reviews: Dict[int, AgentReport],
    ) -> Dict[str, List[Path]]:
        """
        Save all reports from an iteration.

        Args:
            iteration: The iteration number
            analyst_reports: Dict of type_id -> analyst report
            rd_reviews: Dict of type_id -> RD review

        Returns:
            Dict with 'analyst' and 'rd_review' keys containing lists of saved paths
        """
        saved = {"analyst": [], "rd_review": []}

        for type_id, report in analyst_reports.items():
            if report.is_success:
                path = self.save_analyst_report(report)
                saved["analyst"].append(path)

        for type_id, report in rd_reviews.items():
            if report.is_success:
                path = self.save_rd_review(report)
                saved["rd_review"].append(path)

        logger.info(
            f"Iteration {iteration}: saved {len(saved['analyst'])} analyst reports, "
            f"{len(saved['rd_review'])} RD reviews"
        )
        return saved

    def load_analyst_report(self, type_id: int, iteration: int) -> Optional[str]:
        """
        Load an analyst report from the interim directory.

        Args:
            type_id: The investing type ID (1-6)
            iteration: The iteration number

        Returns:
            The report content (without metadata header), or None if not found
        """
        filename = self._get_analyst_filename(type_id, iteration)
        filepath = self.interim_dir / filename

        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")

        # Strip YAML header if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def load_rd_review(self, type_id: int, iteration: int) -> Optional[str]:
        """
        Load an RD review from the interim directory.

        Args:
            type_id: The investing type ID (1-6)
            iteration: The iteration number

        Returns:
            The review content (without metadata header), or None if not found
        """
        filename = self._get_rd_review_filename(type_id, iteration)
        filepath = self.interim_dir / filename

        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")

        # Strip YAML header if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2].strip()

        return content

    def load_previous_analyst_report(self, type_id: int, current_iteration: int) -> Optional[str]:
        """
        Load the most recent analyst report for a type before current iteration.

        Args:
            type_id: The investing type ID (1-6)
            current_iteration: The current iteration number

        Returns:
            The most recent report content, or None if none found
        """
        for i in range(current_iteration - 1, 0, -1):
            content = self.load_analyst_report(type_id, i)
            if content:
                return content
        return None

    def load_previous_rd_review(self, type_id: int, current_iteration: int) -> Optional[str]:
        """
        Load the most recent RD review for a type before current iteration.

        Args:
            type_id: The investing type ID (1-6)
            current_iteration: The current iteration number

        Returns:
            The most recent review content, or None if none found
        """
        for i in range(current_iteration - 1, 0, -1):
            content = self.load_rd_review(type_id, i)
            if content:
                return content
        return None

    def load_all_final_reports(self, iteration: int = 5) -> Dict[int, str]:
        """
        Load all final analyst reports for a given iteration.

        Args:
            iteration: The iteration number to load (default 5 for backwards compatibility)

        Returns:
            Dict of type_id -> report content
        """
        reports = {}
        for type_id in range(1, 7):
            content = self.load_analyst_report(type_id, iteration)
            if content:
                reports[type_id] = content
        return reports

    def save_pipeline_state(self, state: PipelineState) -> Path:
        """
        Save the complete pipeline state as JSON.

        Now saved in interim/ folder.

        Args:
            state: The PipelineState to save

        Returns:
            Path to the saved file
        """
        filepath = get_pipeline_state_path(self.ticker)
        filepath.write_text(
            json.dumps(state.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.debug(f"Saved pipeline state: {filepath}")
        return filepath

    def get_report_summary(self) -> Dict[str, int]:
        """
        Get a summary of saved reports.

        Returns:
            Dict with counts of different report types
        """
        summary = {
            "analyst_reports": 0,
            "rd_reviews": 0,
            "source_scout_reports": 0,
            "has_initial_scout": False,
            "has_final_en": False,
            "has_final_cn": False,
        }

        # Count interim files
        if self.interim_dir.exists():
            for f in self.interim_dir.iterdir():
                if f.name.startswith("analyst_"):
                    summary["analyst_reports"] += 1
                elif f.name.startswith("rd_review_"):
                    summary["rd_reviews"] += 1
                elif f.name.startswith("source_scout_"):
                    summary["source_scout_reports"] += 1

        # Check for initial scout and final memos
        summary["has_initial_scout"] = get_initial_scout_path(self.ticker).exists()
        summary["has_final_en"] = get_final_memo_path(self.ticker, "EN").exists()
        summary["has_final_cn"] = get_final_memo_path(self.ticker, "CN").exists()

        return summary
