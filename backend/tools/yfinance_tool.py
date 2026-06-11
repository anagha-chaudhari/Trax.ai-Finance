import yfinance as yf
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def interpret_pe(pe):
    if pe is None: return "N/A"
    if pe < 0: return f"{pe:.1f} (negative — company losing money)"
    if pe < 15: return f"{pe:.1f} (below market — potentially undervalued)"
    if pe < 25: return f"{pe:.1f} (fair value range)"
    if pe < 35: return f"{pe:.1f} (above average — growth premium)"
    return f"{pe:.1f} (high — expensive relative to earnings)"

def interpret_beta(beta):
    if beta is None: return "N/A"
    if beta < 0.5:  return f"{beta:.2f} (low volatility — defensive)"
    if beta < 1.0:  return f"{beta:.2f} (below market volatility)"
    if beta < 1.5:  return f"{beta:.2f} (near market volatility)"
    return f"{beta:.2f} (high volatility)"

def interpret_roe(roe):
    if roe is None: return "N/A"
    pct = roe * 100
    if pct < 0: return f"{pct:.1f}% (negative — destroying value)"
    if pct < 10: return f"{pct:.1f}% (below average)"
    if pct < 20: return f"{pct:.1f}% (solid)"
    return f"{pct:.1f}% (excellent)"


class MarketInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol e.g. AAPL")

class FetchMarketDataTool(BaseTool):
    name: str = "fetch_market_data"
    description: str = (
        "Fetches current market data and 1-year price history for a stock ticker. "
        "Returns price, market cap, P/E ratio, beta, ROE, 52-week range, "
        "and moving average crossover trend signal (golden cross / death cross). "
        "Use this to understand price trends, valuation, and technical signals."
    )
    args_schema: type[BaseModel] = MarketInput

    def _run(self, ticker: str) -> str:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            pe_ratio = info.get("trailingPE")
            beta = info.get("beta")
            roe = info.get("returnOnEquity")
            market_cap = info.get("marketCap")
            volume = info.get("averageVolume")
            week_52_high = info.get("fiftyTwoWeekHigh")
            week_52_low = info.get("fiftyTwoWeekLow")
            company_name = info.get("longName", ticker)

            history = stock.history(period="1y")
            ma50 = ma200 = None
            trend = "Insufficient price history"

            if len(history) >= 50:
                ma50 = history["Close"].tail(50).mean()
            if len(history) >= 200:
                ma200 = history["Close"].tail(200).mean()

            if ma50 and ma200:
                gap_pct = ((ma50 - ma200) / ma200) * 100
                if ma50 > ma200:
                    trend = f"UPTREND — 50-day MA is {gap_pct:.1f}% above 200-day MA (golden cross)"
                else:
                    trend = f"DOWNTREND — 50-day MA is {abs(gap_pct):.1f}% below 200-day MA (death cross)"

            price_position = "N/A"
            if current_price and week_52_high and week_52_low:
                rng = week_52_high - week_52_low
                if rng > 0:
                    pos = ((current_price - week_52_low) / rng) * 100
                    price_position = f"{pos:.0f}% of 52-week range"

            price_fmt = f"${current_price:.2f}" if current_price else "N/A"
            cap_fmt = f"${market_cap/1e9:.2f}B" if market_cap else "N/A"
            ma50_fmt = f"${ma50:.2f}" if ma50 else "N/A"
            ma200_fmt = f"${ma200:.2f}" if ma200 else "N/A"
            high_fmt = f"${week_52_high:.2f}" if week_52_high else "N/A"
            low_fmt = f"${week_52_low:.2f}" if week_52_low else "N/A"
            vol_fmt = f"{volume:,}" if volume else "N/A"

            return f"""
                Market Data — {company_name} ({ticker.upper()})
                Current Price: {price_fmt}
                Market Cap: {cap_fmt}
                52-Week High: {high_fmt}
                52-Week Low: {low_fmt}
                Price Position: {price_position}
                Avg Volume: {vol_fmt}

                P/E Ratio: {interpret_pe(pe_ratio)}
                Beta: {interpret_beta(beta)}
                ROE: {interpret_roe(roe)}

                50-day MA: {ma50_fmt}
                200-day MA: {ma200_fmt}
                Trend Signal: {trend}
                            """.strip()

        except Exception as e:
            return f"Error fetching market data for {ticker}: {str(e)}"


fetch_market_data = FetchMarketDataTool()