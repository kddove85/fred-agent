from mcp.server.fastmcp import FastMCP
from services.rss_feed_service import RSSFeedService

def register_rss_feed_tools(mcp: FastMCP):
    """Register RSS feed tools for the LLM."""
    rss_feed_service = RSSFeedService()

    @mcp.tool()
    async def get_latest_business_news(max_items: int = 10) -> str:
        """Retrieve the latest business news headlines from economic data sources.

        Prioritizes official sources (Federal Reserve, BLS, BEA) over market news sources.
        Headlines are marked as [PRIMARY] or [SECONDARY] based on source reliability.

        Args:
            max_items: Maximum number of news items to retrieve (default: 10)
        """
        return await rss_feed_service.get_latest_business_news(max_items)

    @mcp.tool()
    async def get_economic_articles_for_analysis(max_items: int = 5) -> str:
        """Fetch full economic news articles with content for detailed analysis.

        This tool retrieves complete article content from economic news sources,
        cleans the HTML, and formats it for LLM analysis. Use this when you need
        to analyze trends, extract data points, or understand economic context.

        Articles are prioritized from official government sources (Fed, BLS, BEA)
        before market news sources (MarketWatch, CNBC).

        Args:
            max_items: Maximum number of articles to retrieve and format (default: 5)

        Returns:
            Formatted article content ready for analysis, including titles, dates,
            sources, and full cleaned text content.
        """
        return await rss_feed_service.get_formatted_articles_for_llm(max_items)

    @mcp.tool()
    async def get_primary_source_economic_news(max_items: int = 5) -> str:
        """Get economic news ONLY from primary official sources (Fed, BLS, BEA).

        Use this when you need the most authoritative, data-focused economic information
        without market commentary or analysis. Best for factual economic indicators
        and official policy announcements.

        Args:
            max_items: Maximum number of articles to retrieve (default: 5)
        """
        # This requires a small addition to your RSSFeedService
        all_items = []
        for url in rss_feed_service.PRIMARY_FEEDS:
            all_items.extend(await rss_feed_service.fetch_feed(url))

        all_items = sorted(all_items, key=lambda x: x.get("pub_date", ""), reverse=True)[:max_items]

        formatted = []
        for item in all_items:
            content = rss_feed_service._clean_html(item.get("content") or item.get("description") or "")
            formatted.append(
                f"Title: {item['title']}\n"
                f"Published: {item['pub_date']}\n"
                f"Link: {item['link']}\n"
                f"Content: {content[:2000]}\n"
            )

        return "\n\n" + ("-" * 80) + "\n\n".join(formatted) if formatted else "No primary source news found."