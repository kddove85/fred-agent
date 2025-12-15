from typing import Any
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

class FREDService:
    """Service for interacting with the FRED API."""

    FRED_API_BASE = "https://api.stlouisfed.org/fred"
    USER_AGENT = "fred-service/1.0"
    API_KEY = os.getenv("FRED_API_KEY")

    @staticmethod
    async def make_request(endpoint: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Make a request to the FRED API with proper error handling."""
        headers = {
            "User-Agent": FREDService.USER_AGENT,
            "Accept": "application/json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{FREDService.FRED_API_BASE}/{endpoint}", headers=headers, params=params, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError:
                return None


    async def search_series(self, search_text: str) -> str:
        """Search for FRED series by keyword."""
        endpoint = "series/search"
        params = {
            "search_text": search_text,
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "seriess" not in data:
            return "No series found for the given search text."

        results = data["seriess"]
        formatted_results = [
            f"ID: {series['id']}, Title: {series['title']}" for series in results
        ]
        return "\n".join(formatted_results)

    async def get_series_observations(self, series_id: str, limit: int = 100, sort_order: str = 'asc') -> str:
        """Get observations for a series."""
        params = {
            'series_id': series_id,
            'api_key': FREDService.API_KEY,
            'file_type': 'json',
            'sort_order': sort_order,
            'limit': limit
        }

        endpoint = "series/observations"
        data = await self.make_request(endpoint, params)

        if not data or 'observations' not in data:
            return "No observations found for the given series."

        observations = data['observations']

        # Filter out missing values
        valid_obs = [
            obs for obs in observations
            if obs['value'] != '.'
        ]

        if not valid_obs:
            return f"No valid observations found for series {series_id}"

        # Format as string
        formatted_obs = [
            f"Date: {obs['date']}, Value: {obs['value']}"
            for obs in valid_obs
        ]
        return "\n".join(formatted_obs)

    async def get_series_info(self, series_id: str) -> str:
        """Get information about a specific FRED series."""
        endpoint = "series"
        params = {
            "series_id": series_id,
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "seriess" not in data:
            return "Unable to fetch series info or no data found."

        series_info = data["seriess"][0]
        formatted_info = (
            f"Title: {series_info['title']}\n"
            f"ID: {series_info['id']}\n"
            f"Frequency: {series_info['frequency']}\n"
            f"Units: {series_info['units']}\n"
            f"Seasonal Adjustment: {series_info['seasonal_adjustment']}\n"
            f"Last Updated: {series_info['last_updated']}\n"
            f"Notes: {series_info.get('notes', 'No notes available')}"
        )
        return formatted_info

    async def get_categories(self) -> str:
        """Get a list of FRED categories."""
        endpoint = "category/children"
        params = {
            "category_id": "0",  # Root category
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "categories" not in data:
            return "Unable to fetch categories or no data found."

        categories = data["categories"]
        formatted_categories = [
            f"ID: {cat['id']}, Name: {cat['name']}" for cat in categories
        ]
        return "\n".join(formatted_categories)

    async def get_releases(self) -> str:
        """Get a list of FRED releases."""
        endpoint = "releases"
        params = {
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "releases" not in data:
            return "Unable to fetch releases or no data found."

        releases = data["releases"]
        formatted_releases = [
            f"ID: {rel['id']}, Name: {rel['name']}, Release Date: {rel['release_date']}" for rel in releases
        ]
        return "\n".join(formatted_releases)

    async def get_sources(self) -> str:
        """Get a list of FRED sources."""
        endpoint = "sources"
        params = {
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "sources" not in data:
            return "Unable to fetch sources or no data found."

        sources = data["sources"]
        formatted_sources = [
            f"ID: {src['id']}, Name: {src['name']}" for src in sources
        ]
        return "\n".join(formatted_sources)

    async def get_tags(self) -> str:
        """Get a list of FRED tags."""
        endpoint = "tags"
        params = {
            "api_key": FREDService.API_KEY,
            "file_type": "json"
        }
        data = await self.make_request(endpoint, params)

        if not data or "tags" not in data:
            return "Unable to fetch tags or no data found."

        tags = data["tags"]
        formatted_tags = [
            f"ID: {tag['id']}, Name: {tag['name']}" for tag in tags
        ]
        return "\n".join(formatted_tags)
