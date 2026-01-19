import os
import sys
import logging
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
from html import unescape
import re

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class RSSFeedService:
    """Service for fetching, parsing, and summarizing business RSS feeds."""

    # Tiered approach: Primary sources are most reliable
    PRIMARY_FEEDS = [
        "https://www.federalreserve.gov/feeds/press_all.xml",
        "https://www.bls.gov/feed/bls_latest.rss",
        "https://fredblog.stlouisfed.org/feed/",
    ]

    SECONDARY_FEEDS = [
        "https://www.bea.gov/rss/news.xml",
        "http://feeds.marketwatch.com/marketwatch/economicreport/",
        "https://www.cnbc.com/id/20910258/device/rss/rss.html"
    ]

    ALL_FEEDS = PRIMARY_FEEDS + SECONDARY_FEEDS

    @staticmethod
    async def fetch_feed(url: str) -> List[Dict[str, str]]:
        logger.info(f"Fetching RSS feed: {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(
                    url,
                    timeout=15.0,
                    headers={'User-Agent': 'Mozilla/5.0 (Economic Analysis Bot)'}
                )
                logger.debug(f"HTTP status for {url}: {response.status_code}")
                response.raise_for_status()
                return RSSFeedService._parse_feed(response.text, url)
            except Exception as e:
                logger.error(f"Error fetching/parsing feed {url}: {e}")
                return []

    @staticmethod
    def _parse_feed(feed_xml: str, source_url: str) -> List[Dict[str, str]]:
        items = []
        try:
            root = ET.fromstring(feed_xml)

            # Determine feed type (RSS vs Atom)
            is_atom = root.tag.endswith('feed')

            if is_atom:
                # Parse Atom feeds
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                for entry in root.findall('.//atom:entry', ns):
                    link_elem = entry.find('atom:link[@rel="alternate"]', ns)
                    if link_elem is None:
                        link_elem = entry.find('atom:link', ns)

                    items.append({
                        "title": entry.findtext('atom:title', namespaces=ns),
                        "link": link_elem.get('href') if link_elem is not None else None,
                        "pub_date": entry.findtext('atom:updated', namespaces=ns) or entry.findtext('atom:published',
                                                                                                    namespaces=ns),
                        "description": entry.findtext('atom:summary', namespaces=ns) or entry.findtext('atom:content',
                                                                                                       namespaces=ns),
                        "content": entry.findtext('atom:content', namespaces=ns),
                        "source": source_url,
                        "is_primary": source_url in RSSFeedService.PRIMARY_FEEDS
                    })
            else:
                # Parse RSS feeds
                for item in root.findall(".//item"):
                    content_encoded = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                    content = item.findtext("content")
                    description = item.findtext("description")

                    items.append({
                        "title": item.findtext("title"),
                        "link": item.findtext("link"),
                        "pub_date": item.findtext("pubDate"),
                        "description": description,
                        "content": content_encoded or content or description,
                        "source": source_url,
                        "is_primary": source_url in RSSFeedService.PRIMARY_FEEDS
                    })

            logger.info(f"Parsed {len(items)} items from feed: {source_url}")
        except Exception as e:
            logger.error(f"Error parsing feed XML from {source_url}: {e}")

        return items

    @staticmethod
    def _clean_html(html_text: str) -> str:
        """Remove HTML tags and clean up text for better readability."""
        if not html_text:
            return ""

        # Unescape HTML entities
        text = unescape(html_text)

        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags but keep the content
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    @staticmethod
    async def fetch_article_content(url: str) -> Optional[str]:
        """Fetch full article content from a URL."""
        if not url:
            return None

        logger.info(f"Fetching article content from: {url}")
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(
                    url,
                    timeout=20.0,
                    headers={'User-Agent': 'Mozilla/5.0 (Economic Analysis Bot)'}
                )
                response.raise_for_status()

                # Basic content extraction (you might want to use a library like newspaper3k or readability)
                html = response.text

                # Try to extract main content (very basic approach)
                # Look for common article content tags
                content_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL | re.IGNORECASE)
                if not content_match:
                    content_match = re.search(r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>', html,
                                              re.DOTALL | re.IGNORECASE)

                if content_match:
                    return RSSFeedService._clean_html(content_match.group(1))
                else:
                    # Fallback: return cleaned HTML (limited)
                    return RSSFeedService._clean_html(html)[:5000]

            except Exception as e:
                logger.error(f"Error fetching article content from {url}: {e}")
                return None

    async def get_latest_business_news(self, max_items: int = 10) -> str:
        """Get latest headlines from all feeds."""
        logger.info("Aggregating latest business news from RSS feeds.")
        all_items = []

        for url in self.ALL_FEEDS:
            all_items.extend(await self.fetch_feed(url))

        # Sort by date (most recent first) and primary sources first
        all_items = sorted(
            all_items,
            key=lambda x: (not x.get("is_primary", False), x.get("pub_date", "")),
            reverse=True
        )

        formatted = []
        for item in all_items[:max_items]:
            source_type = "[PRIMARY]" if item.get("is_primary") else "[SECONDARY]"
            formatted.append(
                f"{source_type} {item['title']}\n"
                f"Published: {item['pub_date']}\n"
                f"Link: {item['link']}"
            )

        if not formatted:
            logger.warning("No business news found.")
            return "No business news found."

        return "\n\n".join(formatted)

    async def get_articles_for_llm(self, max_items: int = 5, include_full_content: bool = True) -> List[Dict[str, str]]:
        """
        Get articles formatted for LLM consumption.
        Returns structured data that the LLM can easily process.
        """
        logger.info("Fetching articles for LLM analysis.")
        all_items = []

        # Fetch from all feeds
        for url in self.ALL_FEEDS:
            all_items.extend(await self.fetch_feed(url))

        # Prioritize primary sources and sort by date
        all_items = sorted(
            all_items,
            key=lambda x: (not x.get("is_primary", False), x.get("pub_date", "")),
            reverse=True
        )[:max_items]

        articles = []
        for item in all_items:
            # Get the best available content
            content = item.get("content") or item.get("description") or ""
            content = self._clean_html(content)

            # If we want full content and the RSS content is short, try fetching the article
            if include_full_content and len(content) < 500 and item.get("link"):
                full_content = await self.fetch_article_content(item["link"])
                if full_content and len(full_content) > len(content):
                    content = full_content

            article_data = {
                "title": item.get("title", "No title"),
                "link": item.get("link", ""),
                "pub_date": item.get("pub_date", "Unknown date"),
                "content": content[:3000],  # Limit to 3000 chars to avoid token overload
                "source_type": "PRIMARY" if item.get("is_primary") else "SECONDARY",
                "source_url": item.get("source", "Unknown")
            }
            articles.append(article_data)

        return articles

    async def get_formatted_articles_for_llm(self, max_items: int = 5) -> str:
        """
        Get articles in a formatted string ready for LLM analysis.
        This is what you'd pass directly to the LLM for summarization.
        """
        articles = await self.get_articles_for_llm(max_items, include_full_content=True)

        if not articles:
            return "No articles found to analyze."

        formatted_output = "ECONOMIC NEWS ARTICLES FOR ANALYSIS:\n\n"
        formatted_output += "=" * 80 + "\n\n"

        for i, article in enumerate(articles, 1):
            formatted_output += f"ARTICLE {i} [{article['source_type']}]\n"
            formatted_output += f"Title: {article['title']}\n"
            formatted_output += f"Published: {article['pub_date']}\n"
            formatted_output += f"Source: {article['source_url']}\n"
            formatted_output += f"Link: {article['link']}\n\n"
            formatted_output += f"Content:\n{article['content']}\n\n"
            formatted_output += "-" * 80 + "\n\n"

        return formatted_output