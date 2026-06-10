import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import ClassVar
from utils.config import settings


class NewsInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol e.g. AAPL")


class FetchNewsSentimentTool(BaseTool):
    name: str = "fetch_news_sentiment"
    description: str = (
        "Fetches recent news headlines for a stock ticker and returns a sentiment summary. "
        "Use this tool to identify market-moving events and overall sentiment direction."
    )
    args_schema: type[BaseModel] = NewsInput
    POSITIVE_WORDS: ClassVar[set[str]] = {
        "upgrade", "beat", "outperform", "strong", "gain", "record", "growth",
        "raises", "surge", "expands", "wins", "positive", "bullish", "profit",
        "higher", "improved", "acquisition", "partnership", "launch",
        "optimistic", "outlook", "recovery",
    }

    NEGATIVE_WORDS: ClassVar[set[str]] = {
        "downgrade", "miss", "weak", "decline", "loss", "cut", "drop", "slump",
        "lawsuit", "investigation", "recall", "warn", "negative", "bearish", "risk",
        "debt", "layoff", "slowdown", "shortfall", "fraud",
    }

    def _normalize_text(self, text: str) -> str:
        return (text or "").lower()

    def _score_text(self, text: str) -> int:
        normalized = self._normalize_text(text)
        score = 0
        for word in self.POSITIVE_WORDS:
            if word in normalized:
                score += 1
        for word in self.NEGATIVE_WORDS:
            if word in normalized:
                score -= 1
        return score

    def _run(self, ticker: str) -> str:
        api_key = getattr(settings, "news_api_key", None)
        if not api_key:
            return "News sentiment tool unavailable: NEWS_API_KEY is not configured."

        endpoint = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 8,
            "apiKey": api_key,
        }

        try:
            response = requests.get(endpoint, params=params, timeout=15)
            data = response.json()
        except Exception as e:
            return f"Error fetching news for {ticker}: {str(e)}"

        if response.status_code != 200 or data.get("status") != "ok":
            message = data.get("message") or response.text
            return f"News API error for {ticker}: {message}"

        articles = data.get("articles", [])
        if not articles:
            return f"No recent news articles found for {ticker}."

        scored_articles = []
        for article in articles:
            title = article.get("title") or ""
            description = article.get("description") or ""
            content = f"{title}. {description}"
            score = self._score_text(content)
            scored_articles.append({
                "title": title,
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", ""),
                "score": score,
                "url": article.get("url", ""),
            })

        total_score = sum(item["score"] for item in scored_articles)
        average_score = total_score / max(len(scored_articles), 1)
        overall = "POSITIVE" if average_score >= 1 else "NEGATIVE" if average_score <= -1 else "NEUTRAL"

        headlines = []
        for item in scored_articles[:5]:
            label = "Positive" if item["score"] > 0 else "Negative" if item["score"] < 0 else "Neutral"
            headlines.append(f"- [{label}] {item['title']} ({item['source']})")

        events = []
        for item in scored_articles[:5]:
            if item["score"] >= 1:
                events.append(f"Positive signal from {item['source']}: {item['title']}")
            elif item["score"] <= -1:
                events.append(f"Negative signal from {item['source']}: {item['title']}")

        if not events:
            events.append("No strong positive or negative events were detected in the top headlines.")

        return (
            f"News Sentiment — {ticker.upper()}\n"
            f"Overall Sentiment: {overall} (average score {average_score:.1f})\n"
            f"Articles Reviewed: {len(scored_articles)}\n\n"
            f"Top Headlines:\n"
            f"{chr(10).join(headlines)}\n\n"
            f"Key Events:\n"
            f"{chr(10).join(events)}"
        )


fetch_news_sentiment = FetchNewsSentimentTool()
