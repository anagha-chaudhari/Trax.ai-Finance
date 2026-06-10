from crewai import Agent, Task, Crew, Process, LLM
from tools.edgar_tool import fetch_sec_financials
from tools.yfinance_tool import fetch_market_data
from tools.news_tool import fetch_news_sentiment
from utils.config import settings
import json
import re

# One LLM instance shared across all agents.
llm = LLM(
    model=settings.llm_model,
    api_key=settings.gemini_api_key,
    temperature=0.2,  # low temperature = more consistent, factual output
    max_retries=3,    # Auto-retry on API blips
    timeout=60
)


# Agent definitions

sec_analyst = Agent(
    role="Senior SEC Filing Analyst",
    goal=(
        "Extract and interpret key financial metrics from SEC EDGAR 10-K filings. "
        "Identify revenue trends, profitability, debt levels, and any red flags "
        "in the company's official financial statements."
    ),
    backstory=(
        "You are a forensic accountant with 12 years at a Big Four firm specialising "
        "in public company audits. You have reviewed hundreds of 10-K filings and know "
        "exactly where companies hide debt, inflate revenue, or obscure losses. "
        "You trust numbers from official SEC filings above all other sources. "
        "You always calculate profit margin and debt ratio when the data is available. "
        "You are sceptical by nature — you look for what the numbers don't say as much "
        "as what they do."
    ),
    tools=[fetch_sec_financials],
    llm=llm,
    verbose=True,
    max_iter=3,
)

market_analyst = Agent(
    role="Quantitative Market Analyst",
    goal=(
        "Analyse price history, technical indicators, and market valuation metrics "
        "to determine the stock's current trend, momentum, and relative value. "
        "Provide a clear technical picture: is this stock in an uptrend or downtrend?"
    ),
    backstory=(
        "You are a quantitative analyst trained at a hedge fund where you built "
        "algorithmic trading systems. You think in terms of moving averages, "
        "momentum signals, and price-to-value gaps. You know that the 50/200-day "
        "moving average crossover is one of the most reliable trend signals in "
        "technical analysis. You interpret P/E ratios relative to sector averages "
        "and growth rates, not in isolation. Numbers without context are meaningless to you."
    ),
    tools=[fetch_market_data],
    llm=llm,
    verbose=True,
    max_iter=3,
)

risk_evaluator = Agent(
    role="Portfolio Risk Evaluator",
    goal=(
        "Score the stock's risk profile by evaluating beta, debt levels, "
        "profit margins, and valuation against S&P 500 benchmarks. "
        "Assign a final risk rating of LOW, MEDIUM, or HIGH with clear justification."
    ),
    backstory=(
        "You are a risk officer at an asset management firm. Your job is to protect "
        "capital first, generate returns second. You have seen bull markets hide "
        "weak fundamentals and bear markets punish overleveraged companies. "
        "You evaluate every stock against five dimensions: volatility risk (beta), "
        "financial leverage risk (debt ratio), earnings quality risk (profit margin), "
        "valuation risk (P/E vs growth), and liquidity risk (volume). "
        "You assign LOW risk only when at least four of five dimensions are healthy."
    ),
    tools=[fetch_market_data, fetch_sec_financials],
    llm=llm,
    verbose=True,
    max_iter=3,
)

news_analyst = Agent(
    role="Financial News and Sentiment Analyst",
    goal=(
        "Analyse recent news headlines using FinBERT sentiment scoring to determine "
        "market sentiment around the stock. Identify major catalysts — earnings beats, "
        "lawsuits, product launches, analyst upgrades — that could drive price movement."
    ),
    backstory=(
        "You are a sell-side research analyst who has tracked market-moving news for "
        "a decade. You know that sentiment precedes price movement — stocks fall before "
        "bad earnings because smart money reads the tea leaves early. "
        "You use NLP-powered sentiment scoring but you also read between the lines: "
        "a 'cautious' CEO statement in an earnings call is a warning sign even if "
        "the headline numbers look fine. You always flag the top 2-3 events that "
        "could move this stock in the next 30 days."
    ),
    tools=[fetch_news_sentiment],
    llm=llm,
    verbose=True,
    max_iter=3,
)


# Task definitions

def create_sec_task(ticker: str) -> Task:
    return Task(
        description=(
            f"Fetch and analyse the SEC EDGAR 10-K filing data for {ticker}. "
            f"Extract revenue, net income, total assets, total liabilities. "
            f"Calculate profit margin and debt ratio. "
            f"Identify whether the company is profitable, growing, and financially stable. "
            f"Flag any concerning patterns such as declining revenue, negative margins, "
            f"or debt ratio above 0.7."
        ),
        expected_output=(
            "A structured financial analysis containing: "
            "1) Key metrics table (revenue, net income, assets, liabilities, profit margin, debt ratio) "
            "2) Profitability assessment (is the company making money?) "
            "3) Balance sheet health assessment (is the debt level manageable?) "
            "4) One paragraph summary of fundamental financial health "
            "5) Any red flags found in the filing data"
        ),
        agent=sec_analyst,
    )


def create_market_task(ticker: str) -> Task:
    return Task(
        description=(
            f"Fetch current market data and 1-year price history for {ticker}. "
            f"Analyse the 50-day and 200-day moving average crossover signal. "
            f"Evaluate the P/E ratio against market averages. "
            f"Assess beta for volatility. "
            f"Determine where the stock sits in its 52-week range. "
            f"Provide a clear directional verdict: is this stock technically strong or weak?"
        ),
        expected_output=(
            "A structured market analysis containing: "
            "1) Current price and market cap "
            "2) Technical trend signal (UPTREND/DOWNTREND with MA values) "
            "3) Valuation assessment (is the P/E reasonable?) "
            "4) Volatility assessment (beta interpretation) "
            "5) 52-week price position context "
            "6) One paragraph technical summary with clear directional bias"
        ),
        agent=market_analyst,
    )


def create_risk_task(ticker: str) -> Task:
    return Task(
        description=(
            f"Evaluate the overall investment risk profile for {ticker}. "
            f"Use both market data (beta, P/E, price trend) and SEC filing data "
            f"(debt ratio, profit margin) to score risk across five dimensions: "
            f"volatility, financial leverage, earnings quality, valuation, and trend. "
            f"Assign a final risk rating of LOW, MEDIUM, or HIGH. "
            f"LOW requires at least 4 of 5 dimensions to be healthy. "
            f"HIGH if 3 or more dimensions show significant concern."
        ),
        expected_output=(
            "A structured risk assessment containing: "
            "1) Score for each of five risk dimensions with brief justification "
            "2) Overall risk rating: LOW / MEDIUM / HIGH "
            "3) The single biggest risk factor for this stock right now "
            "4) One paragraph risk summary an investor can act on"
        ),
        agent=risk_evaluator,
    )


def create_news_task(ticker: str) -> Task:
    return Task(
        description=(
            f"Fetch and score recent news headlines for {ticker} using FinBERT sentiment analysis. "
            f"Compute the confidence-weighted, recency-adjusted sentiment score. "
            f"Detect any major events: earnings beats/misses, analyst upgrades/downgrades, "
            f"acquisitions, lawsuits, product launches, or management changes. "
            f"Identify the top 2-3 events most likely to move the stock price in the next 30 days."
        ),
        expected_output=(
            "A structured sentiment report containing: "
            "1) Overall sentiment label (POSITIVE/NEGATIVE/NEUTRAL) and weighted score (-1 to +1) "
            "2) List of detected major events with brief description of likely price impact "
            "3) Top 3 most impactful headlines with their individual sentiment scores "
            "4) One paragraph market narrative: what is the street saying about this stock right now?"
        ),
        agent=news_analyst,
    )


def create_synthesis_task(ticker: str, sec_task, market_task, risk_task, news_task) -> Task:
    return Task(
        description=(
            f"You have received four specialist research reports on {ticker}: "
            f"SEC filing analysis, market/technical analysis, risk assessment, and news sentiment. "
            f"Read all four reports carefully and synthesise them into one final investment report. "
            f"Your recommendation must be grounded in specific evidence from all four reports. "
            f"Be direct. Investors need a clear answer, not hedged non-commitments. "
            f"You MUST extract the specific numerical values from the reports to populate the JSON fields."
        ),
        expected_output=(
            "A JSON object with exactly this structure:\n"
            "{\n"
            '  "company": "Full company name",\n'
            '  "ticker": "TICKER",\n'
            '  "recommendation": "BUY" or "HOLD" or "SELL",\n'
            '  "risk_rating": "LOW" or "MEDIUM" or "HIGH",\n'
            '  "sentiment": "POSITIVE" or "NEGATIVE" or "NEUTRAL",\n'
            '  "sentiment_score": float between -1.0 and 1.0,\n'
            '  "market_cap": "String (e.g., $2.5T)",\n'
            '  "beta": "String (e.g., 1.1)",\n'
            '  "roe": "String (e.g., 25%)",\n'
            '  "trend": "String (e.g., UPTREND)",\n'
            '  "revenue": "String (e.g., $100B)",\n'
            '  "net_income": "String (e.g., $20B)",\n'
            '  "total_assets": "String (e.g., $300B)",\n'
            '  "profit_margin": "String (e.g., 20%)",\n'
            '  "summary": "3-4 sentence plain English summary of the investment case",\n'
            '  "risks": ["specific risk 1", "specific risk 2", "specific risk 3"],\n'
            '  "opportunities": ["specific opportunity 1", "specific opportunity 2", "specific opportunity 3"],\n'
            '  "sec_analysis": "2-3 sentence summary of filing findings",\n'
            '  "market_analysis": "2-3 sentence summary of technical findings",\n'
            '  "risk_analysis": "2-3 sentence summary of risk assessment",\n'
            '  "news_analysis": "2-3 sentence summary of sentiment findings"\n'
            "}\n"
            "Return ONLY valid JSON. No markdown, no backticks, no explanation outside the JSON."
        ),
        agent=sec_analyst,
        context=[sec_task, market_task, risk_task, news_task],
    )


# main function - run full analysis

def run_analysis(ticker: str) -> dict:
    """
    Orchestrates all four agents and returns the final structured report.
    Called by the FastAPI background task in the analysis router.
    """
    ticker = ticker.upper().strip()

    # Create task instances for this specific ticker
    sec_task = create_sec_task(ticker)
    market_task = create_market_task(ticker)
    risk_task = create_risk_task(ticker)
    news_task = create_news_task(ticker)
    synthesis = create_synthesis_task(ticker, sec_task, market_task, risk_task, news_task)

    crew = Crew(
        agents=[sec_analyst, market_analyst, risk_evaluator, news_analyst],
        tasks=[sec_task, market_task, risk_task, news_task, synthesis],
        process=Process.sequential,
        verbose=True,
        max_rpm=10,  # Safely throttles API calls to avoid 429s on free tiers
    )

    result = crew.kickoff()

    raw_output = result.raw
    cleaned = re.sub(r"```json\s*|\s*```", "", raw_output).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback with all required UI keys so the frontend never crashes
        return {
            "company": ticker,
            "ticker": ticker,
            "recommendation": "HOLD",
            "risk_rating": "MEDIUM",
            "sentiment": "NEUTRAL",
            "sentiment_score": 0.0,
            "market_cap": "N/A",
            "beta": "N/A",
            "roe": "N/A",
            "trend": "N/A",
            "revenue": "N/A",
            "net_income": "N/A",
            "total_assets": "N/A",
            "profit_margin": "N/A",
            "summary": "Analysis completed but report formatting failed. Raw output preserved.",
            "risks": ["JSON parsing failed — see raw_output"],
            "opportunities": ["Re-run analysis for structured output"],
            "sec_analysis": "Error formatting data.",
            "market_analysis": "Error formatting data.",
            "risk_analysis": "Error formatting data.",
            "news_analysis": "Error formatting data.",
            "raw_output": raw_output,
        }