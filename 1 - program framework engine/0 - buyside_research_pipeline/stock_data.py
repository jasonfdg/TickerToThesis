"""
Stock Data Fetcher
==================
Fetches comprehensive financial data using yfinance.
Used for initial baseline data before analyst iterations.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 0.5


@dataclass
class StockData:
    """Comprehensive stock data from yfinance."""

    ticker: str
    timestamp: datetime

    # === Price & Technical ===
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    open_price: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    fifty_day_average: Optional[float] = None
    two_hundred_day_average: Optional[float] = None

    # === Volume ===
    volume: Optional[int] = None
    average_volume: Optional[int] = None
    average_volume_10d: Optional[int] = None

    # === Valuation ===
    market_cap: Optional[int] = None
    enterprise_value: Optional[int] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    ev_to_revenue: Optional[float] = None
    ev_to_ebitda: Optional[float] = None

    # === Profitability ===
    gross_margins: Optional[float] = None
    operating_margins: Optional[float] = None
    profit_margins: Optional[float] = None
    ebitda_margins: Optional[float] = None

    # === Income ===
    revenue: Optional[int] = None
    revenue_per_share: Optional[float] = None
    revenue_growth: Optional[float] = None
    gross_profits: Optional[int] = None
    ebitda: Optional[int] = None
    net_income: Optional[int] = None
    earnings_growth: Optional[float] = None
    earnings_quarterly_growth: Optional[float] = None
    eps_trailing: Optional[float] = None
    eps_forward: Optional[float] = None

    # === Balance Sheet ===
    total_cash: Optional[int] = None
    total_cash_per_share: Optional[float] = None
    total_debt: Optional[int] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    book_value: Optional[float] = None

    # === Returns ===
    return_on_assets: Optional[float] = None
    return_on_equity: Optional[float] = None

    # === Cash Flow ===
    free_cashflow: Optional[int] = None
    operating_cashflow: Optional[int] = None

    # === Dividends ===
    dividend_rate: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None

    # === Analyst ===
    target_mean_price: Optional[float] = None
    target_high_price: Optional[float] = None
    target_low_price: Optional[float] = None
    target_median_price: Optional[float] = None
    recommendation_key: Optional[str] = None
    recommendation_mean: Optional[float] = None
    number_of_analysts: Optional[int] = None

    # === Shares & Short Interest ===
    shares_outstanding: Optional[int] = None
    float_shares: Optional[int] = None
    shares_short: Optional[int] = None
    short_ratio: Optional[float] = None
    short_percent_of_float: Optional[float] = None
    held_percent_insiders: Optional[float] = None
    held_percent_institutions: Optional[float] = None

    # === Company Info ===
    sector: Optional[str] = None
    industry: Optional[str] = None
    full_name: Optional[str] = None
    employees: Optional[int] = None

    # === Dates ===
    earnings_date: Optional[str] = None
    ex_dividend_date: Optional[str] = None

    def to_source_json(self) -> Dict[str, Any]:
        """Convert to source file JSON format with full structured data."""
        return {
            "url": f"https://finance.yahoo.com/quote/{self.ticker}",
            "title": f"Yahoo Finance: {self.ticker} Stock Data",
            "date_accessed": self.timestamp.isoformat(),
            "summary": self._build_summary(),
            "data_type": "stock_data",
            "type": "stock_data",
            "structured_data": {
                "price": {
                    "current": self.current_price,
                    "previous_close": self.previous_close,
                    "open": self.open_price,
                    "day_range": f"{self.day_low}-{self.day_high}" if self.day_low else None,
                    "52_week_range": f"{self.fifty_two_week_low}-{self.fifty_two_week_high}" if self.fifty_two_week_low else None,
                    "50_day_avg": self.fifty_day_average,
                    "200_day_avg": self.two_hundred_day_average,
                },
                "volume": {
                    "current": self.volume,
                    "average": self.average_volume,
                    "avg_10d": self.average_volume_10d,
                },
                "valuation": {
                    "market_cap": self.market_cap,
                    "enterprise_value": self.enterprise_value,
                    "pe_trailing": self.trailing_pe,
                    "pe_forward": self.forward_pe,
                    "peg": self.peg_ratio,
                    "price_to_book": self.price_to_book,
                    "price_to_sales": self.price_to_sales,
                    "ev_to_revenue": self.ev_to_revenue,
                    "ev_to_ebitda": self.ev_to_ebitda,
                },
                "profitability": {
                    "gross_margin": self.gross_margins,
                    "operating_margin": self.operating_margins,
                    "profit_margin": self.profit_margins,
                    "ebitda_margin": self.ebitda_margins,
                },
                "income": {
                    "revenue": self.revenue,
                    "revenue_per_share": self.revenue_per_share,
                    "revenue_growth": self.revenue_growth,
                    "gross_profits": self.gross_profits,
                    "ebitda": self.ebitda,
                    "net_income": self.net_income,
                    "earnings_growth": self.earnings_growth,
                    "earnings_quarterly_growth": self.earnings_quarterly_growth,
                    "eps_trailing": self.eps_trailing,
                    "eps_forward": self.eps_forward,
                },
                "balance_sheet": {
                    "total_cash": self.total_cash,
                    "cash_per_share": self.total_cash_per_share,
                    "total_debt": self.total_debt,
                    "debt_to_equity": self.debt_to_equity,
                    "current_ratio": self.current_ratio,
                    "quick_ratio": self.quick_ratio,
                    "book_value": self.book_value,
                },
                "returns": {
                    "roa": self.return_on_assets,
                    "roe": self.return_on_equity,
                },
                "cash_flow": {
                    "free_cashflow": self.free_cashflow,
                    "operating_cashflow": self.operating_cashflow,
                },
                "dividends": {
                    "rate": self.dividend_rate,
                    "yield": self.dividend_yield,
                    "payout_ratio": self.payout_ratio,
                },
                "analyst": {
                    "target_mean": self.target_mean_price,
                    "target_median": self.target_median_price,
                    "target_high": self.target_high_price,
                    "target_low": self.target_low_price,
                    "recommendation": self.recommendation_key,
                    "recommendation_score": self.recommendation_mean,
                    "num_analysts": self.number_of_analysts,
                },
                "shares": {
                    "outstanding": self.shares_outstanding,
                    "float": self.float_shares,
                    "short": self.shares_short,
                    "short_ratio": self.short_ratio,
                    "short_pct_float": self.short_percent_of_float,
                    "insider_pct": self.held_percent_insiders,
                    "institution_pct": self.held_percent_institutions,
                },
                "company": {
                    "name": self.full_name,
                    "sector": self.sector,
                    "industry": self.industry,
                    "employees": self.employees,
                },
                "dates": {
                    "earnings": self.earnings_date,
                    "ex_dividend": self.ex_dividend_date,
                },
            },
        }

    def _build_summary(self) -> str:
        """Build human-readable summary for source file."""
        parts = []

        if self.current_price:
            parts.append(f"${self.current_price:.2f}")

        if self.fifty_two_week_low and self.fifty_two_week_high:
            parts.append(f"52wk ${self.fifty_two_week_low:.2f}-${self.fifty_two_week_high:.2f}")

        if self.market_cap:
            cap = f"${self.market_cap/1e9:.1f}B" if self.market_cap >= 1e9 else f"${self.market_cap/1e6:.0f}M"
            parts.append(f"MCap {cap}")

        if self.trailing_pe:
            parts.append(f"P/E {self.trailing_pe:.1f}")

        if self.return_on_equity:
            parts.append(f"ROE {self.return_on_equity*100:.1f}%")

        if self.debt_to_equity:
            parts.append(f"D/E {self.debt_to_equity:.1f}")

        if self.revenue_growth:
            parts.append(f"Rev growth {self.revenue_growth*100:.1f}%")

        if self.target_mean_price and self.recommendation_key:
            parts.append(f"Target ${self.target_mean_price:.2f} ({self.recommendation_key})")

        return " | ".join(parts)


def _rate_limit():
    """Enforce rate limiting between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def fetch_stock_data(ticker: str) -> Optional[StockData]:
    """Fetch comprehensive stock data from yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed. Run: pip install yfinance")
        return None

    _rate_limit()

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or info.get("regularMarketPrice") is None:
            logger.warning(f"No data returned for {ticker}")
            return None

        # Parse earnings date
        earnings_date = None
        if info.get("earningsDate"):
            try:
                ed = info["earningsDate"]
                if isinstance(ed, list) and len(ed) > 0:
                    earnings_date = datetime.fromtimestamp(ed[0]).strftime("%Y-%m-%d")
                elif isinstance(ed, (int, float)):
                    earnings_date = datetime.fromtimestamp(ed).strftime("%Y-%m-%d")
            except Exception:
                pass

        return StockData(
            ticker=ticker,
            timestamp=datetime.now(),
            # Price & Technical
            current_price=info.get("currentPrice") or info.get("regularMarketPrice"),
            previous_close=info.get("previousClose"),
            open_price=info.get("open"),
            day_high=info.get("dayHigh"),
            day_low=info.get("dayLow"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            fifty_day_average=info.get("fiftyDayAverage"),
            two_hundred_day_average=info.get("twoHundredDayAverage"),
            # Volume
            volume=info.get("volume"),
            average_volume=info.get("averageVolume"),
            average_volume_10d=info.get("averageVolume10days"),
            # Valuation
            market_cap=info.get("marketCap"),
            enterprise_value=info.get("enterpriseValue"),
            trailing_pe=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            ev_to_revenue=info.get("enterpriseToRevenue"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            # Profitability
            gross_margins=info.get("grossMargins"),
            operating_margins=info.get("operatingMargins"),
            profit_margins=info.get("profitMargins"),
            ebitda_margins=info.get("ebitdaMargins"),
            # Income
            revenue=info.get("totalRevenue"),
            revenue_per_share=info.get("revenuePerShare"),
            revenue_growth=info.get("revenueGrowth"),
            gross_profits=info.get("grossProfits"),
            ebitda=info.get("ebitda"),
            net_income=info.get("netIncomeToCommon"),
            earnings_growth=info.get("earningsGrowth"),
            earnings_quarterly_growth=info.get("earningsQuarterlyGrowth"),
            eps_trailing=info.get("trailingEps"),
            eps_forward=info.get("forwardEps"),
            # Balance Sheet
            total_cash=info.get("totalCash"),
            total_cash_per_share=info.get("totalCashPerShare"),
            total_debt=info.get("totalDebt"),
            debt_to_equity=info.get("debtToEquity"),
            current_ratio=info.get("currentRatio"),
            quick_ratio=info.get("quickRatio"),
            book_value=info.get("bookValue"),
            # Returns
            return_on_assets=info.get("returnOnAssets"),
            return_on_equity=info.get("returnOnEquity"),
            # Cash Flow
            free_cashflow=info.get("freeCashflow"),
            operating_cashflow=info.get("operatingCashflow"),
            # Dividends
            dividend_rate=info.get("dividendRate"),
            dividend_yield=info.get("dividendYield"),
            payout_ratio=info.get("payoutRatio"),
            # Analyst
            target_mean_price=info.get("targetMeanPrice"),
            target_high_price=info.get("targetHighPrice"),
            target_low_price=info.get("targetLowPrice"),
            target_median_price=info.get("targetMedianPrice"),
            recommendation_key=info.get("recommendationKey"),
            recommendation_mean=info.get("recommendationMean"),
            number_of_analysts=info.get("numberOfAnalystOpinions"),
            # Shares
            shares_outstanding=info.get("sharesOutstanding"),
            float_shares=info.get("floatShares"),
            shares_short=info.get("sharesShort"),
            short_ratio=info.get("shortRatio"),
            short_percent_of_float=info.get("shortPercentOfFloat"),
            held_percent_insiders=info.get("heldPercentInsiders"),
            held_percent_institutions=info.get("heldPercentInstitutions"),
            # Company
            sector=info.get("sector"),
            industry=info.get("industry"),
            full_name=info.get("longName") or info.get("shortName"),
            employees=info.get("fullTimeEmployees"),
            # Dates
            earnings_date=earnings_date,
            ex_dividend_date=info.get("exDividendDate"),
        )

    except Exception as e:
        logger.error(f"Failed to fetch stock data for {ticker}: {e}")
        return None
