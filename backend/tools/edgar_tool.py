import os
os.environ["HF_HOME"] = "D:/hf_cache"

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

SEC_HEADERS = {"User-Agent": "FinancePlatform contact@example.com"}

REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet",
    "RevenuesNetOfInterestExpense", "InterestAndDividendIncomeOperating",
    "PremiumsEarnedNet", "HealthCareOrganizationRevenue", "RealEstateRevenueNet",
]
NET_INCOME_CONCEPTS = [
    "NetIncomeLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "ProfitLoss", "IncomeLossFromContinuingOperations",
]


def get_cik_for_ticker(ticker):
    response = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=SEC_HEADERS, timeout=10
    )
    for entry in response.json().values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def extract_latest_value(facts, concept):
    try:
        units = facts["facts"]["us-gaap"][concept]["units"]
        entries = units.get("USD", units.get("shares", []))
        annual = [e for e in entries if e.get("form") == "10-K" and e.get("end")]
        if not annual:
            return None
        return sorted(annual, key=lambda x: x["end"])[-1]["val"]
    except (KeyError, IndexError, TypeError):
        return None


def find_first_available(facts, concepts):
    for concept in concepts:
        value = extract_latest_value(facts, concept)
        if value is not None:
            return value, concept
    return None, None

# CrewAI base tool format

class SECInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol e.g. AAPL")

class FetchSECFinancialsTool(BaseTool):
    name: str = "fetch_sec_financials"
    description: str = (
        "Fetches real financial data from SEC EDGAR for a stock ticker. "
        "Returns annual revenue, net income, total assets, liabilities, "
        "profit margin and debt ratio from the most recent 10-K filing. "
        "Works across tech, banking, insurance, pharma and retail sectors. "
        "Use this to get official audited financial figures."
    )
    args_schema: type[BaseModel] = SECInput

    def _run(self, ticker: str) -> str:
        try:
            cik = get_cik_for_ticker(ticker)
            if not cik:
                return f"Could not find SEC EDGAR listing for {ticker}. May be a non-US company."

            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            response = requests.get(url, headers=SEC_HEADERS, timeout=20)
            if response.status_code != 200:
                return f"SEC EDGAR returned status {response.status_code} for {ticker}"

            facts = response.json()
            company_name = facts.get("entityName", ticker)

            revenue, revenue_concept = find_first_available(facts, REVENUE_CONCEPTS)
            net_income, _ = find_first_available(facts, NET_INCOME_CONCEPTS)
            total_assets, _ = find_first_available(facts, ["Assets"])
            total_liabilities, _ = find_first_available(facts, ["Liabilities"])

            def fmt(val):
                if val is None: return "N/A"
                if abs(val) >= 1_000_000_000: return f"${val/1e9:.2f}B"
                return f"${val/1e6:.2f}M"

            profit_margin = "N/A"
            debt_ratio    = "N/A"
            if revenue and net_income and revenue != 0:
                profit_margin = f"{(net_income/revenue)*100:.1f}%"
            if total_assets and total_liabilities and total_assets != 0:
                debt_ratio = f"{(total_liabilities/total_assets):.2f}"

            return f"""
            SEC EDGAR 10-K Filing — {company_name} ({ticker.upper()})
            Revenue: {fmt(revenue)}
            Net Income: {fmt(net_income)}
            Total Assets: {fmt(total_assets)}
            Total Liabilities: {fmt(total_liabilities)}
            Profit Margin: {profit_margin}
            Debt Ratio:{debt_ratio}
            Revenue Field:{revenue_concept or 'N/A'}
                        """.strip()

        except Exception as e:
            return f"Error fetching SEC data for {ticker}: {str(e)}"


fetch_sec_financials = FetchSECFinancialsTool()