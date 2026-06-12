from typing import Any
import asyncio
import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()

class FREDService:
    """Service for interacting with the FRED API."""

    FRED_API_BASE = "https://api.stlouisfed.org/fred"
    USER_AGENT = "fred-service/1.0"
    API_KEY = os.getenv("FRED_API_KEY")
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    ALLOWED_SORT_ORDER = {"asc", "desc"}
    ALLOWED_UNITS = {"lin", "chg", "ch1", "pch", "pc1", "pca", "cch", "cca", "log"}
    ALLOWED_FREQUENCY = {
        "d", "w", "bw", "m", "q", "sa", "a", "wef", "weth", "wew", "wetu", "wem", "wesu", "wesa", "bwew", "bwem"
    }
    ALLOWED_AGGREGATION_METHOD = {"avg", "sum", "eop"}
    MIN_LIMIT = 1
    MAX_LIMIT = 100000

    @staticmethod
    def _json_response(payload: dict[str, Any]) -> str:
        """Return standardized JSON text for all tools."""
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _error_response(
        endpoint: str,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        params: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Build a consistent error envelope for MCP consumers."""
        payload: dict[str, Any] = {
            "ok": False,
            "endpoint": endpoint,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if status_code is not None:
            payload["status_code"] = status_code
        if params is not None:
            payload["params"] = params
        if details is not None:
            payload["details"] = details
        return FREDService._json_response(payload)

    @staticmethod
    def _success_response(
        endpoint: str,
        params: dict[str, Any],
        data: Any,
        *,
        meta: dict[str, Any] | None = None,
    ) -> str:
        """Build a consistent success envelope for MCP consumers."""
        payload: dict[str, Any] = {
            "ok": True,
            "endpoint": endpoint,
            "params": params,
            "data": data,
        }
        if meta:
            payload["meta"] = meta
        return FREDService._json_response(payload)

    @staticmethod
    def _validate_date(value: str | None, field_name: str) -> str | None:
        """Validate YYYY-MM-DD date strings for FRED request fields."""
        if value is None:
            return None
        if not FREDService.DATE_PATTERN.match(value):
            return f"Invalid {field_name}. Expected YYYY-MM-DD."
        return None

    @staticmethod
    def _parse_observation_value(raw_value: str | None) -> float | None:
        """Convert valid FRED values to float and keep missing values as None."""
        if raw_value in {None, "", "."}:
            return None
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    async def make_request(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the FRED API with retries and detailed errors."""
        headers = {
            "User-Agent": FREDService.USER_AGENT,
            "Accept": "application/json"
        }
        timeout_seconds = float(os.getenv("FRED_HTTP_TIMEOUT", "30"))
        max_retries = int(os.getenv("FRED_HTTP_MAX_RETRIES", "2"))
        retry_backoff = float(os.getenv("FRED_HTTP_RETRY_BACKOFF", "0.5"))
        retry_statuses = {429, 500, 502, 503, 504}

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
                    response = await client.get(f"{FREDService.FRED_API_BASE}/{endpoint}", params=params)

                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text}

                if response.status_code in retry_statuses and attempt < max_retries:
                    await asyncio.sleep(retry_backoff * (2 ** attempt))
                    continue

                if response.is_error:
                    return {
                        "ok": False,
                        "status_code": response.status_code,
                        "error": body,
                    }

                return {
                    "ok": True,
                    "status_code": response.status_code,
                    "data": body,
                }
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(retry_backoff * (2 ** attempt))
                    continue
                return {
                    "ok": False,
                    "status_code": None,
                    "error": {
                        "error_code": "network_error",
                        "error_message": str(exc),
                    },
                }
            except Exception as exc:  # noqa: BLE001
                return {
                    "ok": False,
                    "status_code": None,
                    "error": {
                        "error_code": "unexpected_error",
                        "error_message": str(exc),
                    },
                }

        return {
            "ok": False,
            "status_code": None,
            "error": {
                "error_code": "retry_exhausted",
                "error_message": "Request retries were exhausted without a response.",
            },
        }

    def _base_params(self) -> tuple[dict[str, Any] | None, str | None]:
        """Return base parameters or a user-facing error when key is missing."""
        if not self.API_KEY:
            return None, self._error_response(
                "auth",
                "missing_api_key",
                "FRED_API_KEY is not configured. Set it in your environment before calling FRED tools.",
            )
        return {
            "api_key": self.API_KEY,
            "file_type": "json",
        }, None

    @staticmethod
    def _extract_error_message(error_payload: dict[str, Any]) -> tuple[str, str]:
        """Normalize FRED error payload to code and message."""
        code = str(error_payload.get("error_code", "request_failed"))
        message = str(error_payload.get("error_message", "FRED request failed."))
        return code, message


    async def search_series(self, search_text: str) -> str:
        """Search for FRED series by keyword."""
        endpoint = "series/search"
        base_params, error = self._base_params()
        if error:
            return error
        params = {
            **base_params,
            "search_text": search_text,
        }
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        results = data.get("seriess", [])
        simplified = [
            {
                "id": series.get("id"),
                "title": series.get("title"),
                "frequency": series.get("frequency"),
                "units": series.get("units"),
                "last_updated": series.get("last_updated"),
            }
            for series in results
        ]
        return self._success_response(
            endpoint,
            params,
            simplified,
            meta={
                "count": len(simplified),
                "total_results": data.get("count"),
                "offset": data.get("offset"),
                "limit": data.get("limit"),
            },
        )

    async def get_series_observations(
        self,
        series_id: str,
        limit: int = 100,
        sort_order: str = "asc",
        observation_start: str | None = None,
        observation_end: str | None = None,
        frequency: str | None = None,
        aggregation_method: str = "avg",
        units: str = "lin",
        offset: int = 0,
    ) -> str:
        """Get observations for a series with interval-aware controls."""
        endpoint = "series/observations"
        base_params, error = self._base_params()
        if error:
            return error

        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(
                endpoint,
                "invalid_sort_order",
                "sort_order must be one of: asc, desc.",
            )
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(
                endpoint,
                "invalid_limit",
                f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.",
            )
        if offset < 0:
            return self._error_response(
                endpoint,
                "invalid_offset",
                "offset must be a non-negative integer.",
            )
        if units not in self.ALLOWED_UNITS:
            return self._error_response(
                endpoint,
                "invalid_units",
                "units must be one of: lin, chg, ch1, pch, pc1, pca, cch, cca, log.",
            )
        if frequency is not None and frequency not in self.ALLOWED_FREQUENCY:
            return self._error_response(
                endpoint,
                "invalid_frequency",
                "frequency is not recognized by FRED series/observations.",
            )
        if aggregation_method not in self.ALLOWED_AGGREGATION_METHOD:
            return self._error_response(
                endpoint,
                "invalid_aggregation_method",
                "aggregation_method must be one of: avg, sum, eop.",
            )

        start_error = self._validate_date(observation_start, "observation_start")
        if start_error:
            return self._error_response(endpoint, "invalid_observation_start", start_error)
        end_error = self._validate_date(observation_end, "observation_end")
        if end_error:
            return self._error_response(endpoint, "invalid_observation_end", end_error)

        params: dict[str, Any] = {
            **base_params,
            "series_id": series_id,
            "sort_order": sort_order,
            "limit": limit,
            "offset": offset,
            "units": units,
        }
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if frequency:
            params["frequency"] = frequency
            params["aggregation_method"] = aggregation_method

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        observations = data.get("observations", [])
        normalized_observations: list[dict[str, Any]] = []
        missing_values = 0

        for obs in observations:
            raw_value = obs.get("value")
            numeric_value = self._parse_observation_value(raw_value)
            is_missing = numeric_value is None
            if is_missing:
                missing_values += 1
            normalized_observations.append(
                {
                    "date": obs.get("date"),
                    "value": numeric_value,
                    "value_raw": raw_value,
                    "is_missing": is_missing,
                    "realtime_start": obs.get("realtime_start"),
                    "realtime_end": obs.get("realtime_end"),
                }
            )

        return self._success_response(
            endpoint,
            params,
            normalized_observations,
            meta={
                "series_id": series_id,
                "count": data.get("count", len(normalized_observations)),
                "returned": len(normalized_observations),
                "missing_values": missing_values,
                "offset": data.get("offset"),
                "limit": data.get("limit"),
                "units_applied": data.get("units", units),
                "frequency_applied": data.get("frequency", frequency),
                "aggregation_method": data.get("aggregation_method", aggregation_method if frequency else None),
                "observation_start": data.get("observation_start"),
                "observation_end": data.get("observation_end"),
                "realtime_start": data.get("realtime_start"),
                "realtime_end": data.get("realtime_end"),
            },
        )

    async def get_series_info(self, series_id: str) -> str:
        """Get information about a specific FRED series."""
        endpoint = "series"
        base_params, error = self._base_params()
        if error:
            return error
        params = {
            **base_params,
            "series_id": series_id,
        }
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        series_list = data.get("seriess", [])
        if not series_list:
            return self._error_response(
                endpoint,
                "series_not_found",
                "No series metadata was returned for the provided series_id.",
                params=params,
            )

        series_info = series_list[0]
        normalized = {
            "id": series_info.get("id"),
            "title": series_info.get("title"),
            "frequency": series_info.get("frequency"),
            "frequency_short": series_info.get("frequency_short"),
            "units": series_info.get("units"),
            "units_short": series_info.get("units_short"),
            "seasonal_adjustment": series_info.get("seasonal_adjustment"),
            "seasonal_adjustment_short": series_info.get("seasonal_adjustment_short"),
            "observation_start": series_info.get("observation_start"),
            "observation_end": series_info.get("observation_end"),
            "last_updated": series_info.get("last_updated"),
            "popularity": series_info.get("popularity"),
            "notes": series_info.get("notes"),
        }
        return self._success_response(endpoint, params, normalized)

    async def get_categories(self, category_id: int = 0) -> str:
        """Get a list of FRED categories."""
        endpoint = "category/children"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(
                endpoint,
                "invalid_category_id",
                "category_id must be a non-negative integer.",
            )

        params = {
            **base_params,
            "category_id": str(category_id),
        }
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        categories = data["categories"]
        normalized_categories = [
            {
                "id": cat.get("id"),
                "name": cat.get("name"),
                "parent_id": cat.get("parent_id"),
            }
            for cat in categories
        ]
        return self._success_response(
            endpoint,
            params,
            normalized_categories,
            meta={"count": len(normalized_categories)},
        )

    async def get_releases(self) -> str:
        """Get a list of FRED releases."""
        endpoint = "releases"
        base_params, error = self._base_params()
        if error:
            return error
        params = {**base_params}
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        releases = data["releases"]
        normalized_releases = [
            {
                "id": rel.get("id"),
                "name": rel.get("name"),
                "press_release": rel.get("press_release"),
                "link": rel.get("link"),
                "release_date": rel.get("release_date"),
            }
            for rel in releases
        ]
        return self._success_response(
            endpoint,
            params,
            normalized_releases,
            meta={"count": len(normalized_releases)},
        )

    async def get_sources(self) -> str:
        """Get a list of FRED sources."""
        endpoint = "sources"
        base_params, error = self._base_params()
        if error:
            return error
        params = {**base_params}
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        sources = data["sources"]
        normalized_sources = [
            {
                "id": src.get("id"),
                "name": src.get("name"),
                "link": src.get("link"),
            }
            for src in sources
        ]
        return self._success_response(
            endpoint,
            params,
            normalized_sources,
            meta={"count": len(normalized_sources)},
        )

    async def get_tags(self) -> str:
        """Get a list of FRED tags."""
        endpoint = "tags"
        base_params, error = self._base_params()
        if error:
            return error
        params = {**base_params}
        response = await self.make_request(endpoint, params)

        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(
                endpoint,
                code,
                message,
                status_code=response["status_code"],
                params=params,
                details=response["error"],
            )

        data = response["data"]
        tags = data["tags"]
        normalized_tags = [
            {
                "name": tag.get("name"),
                "group_id": tag.get("group_id"),
                "popularity": tag.get("popularity"),
                "series_count": tag.get("series_count"),
            }
            for tag in tags
        ]
        return self._success_response(
            endpoint,
            params,
            normalized_tags,
            meta={"count": len(normalized_tags)},
        )

    # -------------------------------------------------------------------------
    # Group 1: Series metadata
    # -------------------------------------------------------------------------

    async def get_series_categories(
        self,
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get categories for a FRED series."""
        endpoint = "series/categories"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "series_id": series_id}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        categories = data.get("categories", [])
        return self._success_response(endpoint, params, categories, meta={"count": len(categories)})

    async def get_series_release(
        self,
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get the release for a FRED series."""
        endpoint = "series/release"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "series_id": series_id}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        releases = data.get("releases", [])
        return self._success_response(endpoint, params, releases[0] if releases else None)

    async def get_series_tags(
        self,
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        order_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Get tags for a FRED series."""
        endpoint = "series/tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order is not None and sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "series_id": series_id}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if order_by:
            params["order_by"] = order_by
        if sort_order:
            params["sort_order"] = sort_order
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def get_series_updates(
        self,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 100,
        offset: int = 0,
        filter_value: str | None = None,
    ) -> str:
        """Get recently updated FRED series."""
        endpoint = "series/updates"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        if offset < 0:
            return self._error_response(endpoint, "invalid_offset", "offset must be a non-negative integer.")
        params: dict[str, Any] = {**base_params, "limit": limit, "offset": offset}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if filter_value:
            params["filter_value"] = filter_value
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        series_list = data.get("seriess", [])
        return self._success_response(endpoint, params, series_list, meta={"count": len(series_list), "limit": data.get("limit"), "offset": data.get("offset")})

    async def get_series_vintagedates(
        self,
        series_id: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str = "asc",
    ) -> str:
        """Get vintage dates for a FRED series."""
        endpoint = "series/vintagedates"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        if offset < 0:
            return self._error_response(endpoint, "invalid_offset", "offset must be a non-negative integer.")
        params: dict[str, Any] = {**base_params, "series_id": series_id, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        vintage_dates = data.get("vintage_dates", [])
        return self._success_response(endpoint, params, vintage_dates, meta={"count": len(vintage_dates), "limit": data.get("limit"), "offset": data.get("offset")})

    async def search_series_tags(
        self,
        series_search_text: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        tag_search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags matching a series search."""
        endpoint = "series/search/tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "series_search_text": series_search_text, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if tag_names:
            params["tag_names"] = tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if tag_search_text:
            params["tag_search_text"] = tag_search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def search_series_related_tags(
        self,
        series_search_text: str,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        tag_search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get related tags for a series search filtered by tag names."""
        endpoint = "series/search/related_tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "series_search_text": series_search_text, "tag_names": tag_names, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if tag_search_text:
            params["tag_search_text"] = tag_search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    # -------------------------------------------------------------------------
    # Group 2: Category deep-dive
    # -------------------------------------------------------------------------

    async def get_category(
        self,
        category_id: int,
    ) -> str:
        """Get information about a specific FRED category."""
        endpoint = "category"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(endpoint, "invalid_category_id", "category_id must be a non-negative integer.")
        params: dict[str, Any] = {**base_params, "category_id": str(category_id)}
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        categories = data.get("categories", [])
        return self._success_response(endpoint, params, categories[0] if categories else None)

    async def get_category_related(
        self,
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get related categories for a FRED category."""
        endpoint = "category/related"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(endpoint, "invalid_category_id", "category_id must be a non-negative integer.")
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "category_id": str(category_id)}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        categories = data.get("categories", [])
        return self._success_response(endpoint, params, categories, meta={"count": len(categories)})

    async def get_category_series(
        self,
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        filter_variable: str | None = None,
        filter_value: str | None = None,
        tag_names: str | None = None,
        exclude_tag_names: str | None = None,
    ) -> str:
        """Get series belonging to a FRED category."""
        endpoint = "category/series"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(endpoint, "invalid_category_id", "category_id must be a non-negative integer.")
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        if offset < 0:
            return self._error_response(endpoint, "invalid_offset", "offset must be a non-negative integer.")
        params: dict[str, Any] = {**base_params, "category_id": str(category_id), "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if order_by:
            params["order_by"] = order_by
        if filter_variable:
            params["filter_variable"] = filter_variable
        if filter_value:
            params["filter_value"] = filter_value
        if tag_names:
            params["tag_names"] = tag_names
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        series_list = data.get("seriess", [])
        return self._success_response(endpoint, params, series_list, meta={"count": len(series_list), "total": data.get("count"), "limit": data.get("limit"), "offset": data.get("offset")})

    async def get_category_tags(
        self,
        category_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags for a FRED category."""
        endpoint = "category/tags"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(endpoint, "invalid_category_id", "category_id must be a non-negative integer.")
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "category_id": str(category_id), "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if tag_names:
            params["tag_names"] = tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if search_text:
            params["search_text"] = search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def get_category_related_tags(
        self,
        category_id: int,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get related tags for a FRED category filtered by tag names."""
        endpoint = "category/related_tags"
        base_params, error = self._base_params()
        if error:
            return error
        if category_id < 0:
            return self._error_response(endpoint, "invalid_category_id", "category_id must be a non-negative integer.")
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "category_id": str(category_id), "tag_names": tag_names, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if search_text:
            params["search_text"] = search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    # -------------------------------------------------------------------------
    # Group 3: Releases
    # -------------------------------------------------------------------------

    async def get_release(
        self,
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get information about a specific FRED release."""
        endpoint = "release"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "release_id": str(release_id)}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        releases = data.get("releases", [])
        return self._success_response(endpoint, params, releases[0] if releases else None)

    async def get_releases_dates(
        self,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        include_release_dates_with_no_data: bool = False,
    ) -> str:
        """Get release dates for all FRED releases."""
        endpoint = "releases/dates"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        params: dict[str, Any] = {**base_params, "limit": limit, "offset": offset, "sort_order": sort_order, "include_release_dates_with_no_data": str(include_release_dates_with_no_data).lower()}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        release_dates = data.get("release_dates", [])
        return self._success_response(endpoint, params, release_dates, meta={"count": len(release_dates), "limit": data.get("limit"), "offset": data.get("offset")})

    async def get_release_dates(
        self,
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 10000,
        offset: int = 0,
        sort_order: str = "asc",
        include_release_dates_with_no_data: bool = False,
    ) -> str:
        """Get release dates for a specific FRED release."""
        endpoint = "release/dates"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "release_id": str(release_id), "limit": limit, "offset": offset, "sort_order": sort_order, "include_release_dates_with_no_data": str(include_release_dates_with_no_data).lower()}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        release_dates = data.get("release_dates", [])
        return self._success_response(endpoint, params, release_dates, meta={"count": len(release_dates), "limit": data.get("limit"), "offset": data.get("offset")})

    async def get_release_series(
        self,
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
        filter_variable: str | None = None,
        filter_value: str | None = None,
        tag_names: str | None = None,
        exclude_tag_names: str | None = None,
    ) -> str:
        """Get series belonging to a FRED release."""
        endpoint = "release/series"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        params: dict[str, Any] = {**base_params, "release_id": str(release_id), "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if order_by:
            params["order_by"] = order_by
        if filter_variable:
            params["filter_variable"] = filter_variable
        if filter_value:
            params["filter_value"] = filter_value
        if tag_names:
            params["tag_names"] = tag_names
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        series_list = data.get("seriess", [])
        return self._success_response(endpoint, params, series_list, meta={"count": len(series_list), "total": data.get("count"), "limit": data.get("limit"), "offset": data.get("offset")})

    async def get_release_sources(
        self,
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get sources for a FRED release."""
        endpoint = "release/sources"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "release_id": str(release_id)}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        sources = data.get("sources", [])
        return self._success_response(endpoint, params, sources, meta={"count": len(sources)})

    async def get_release_tags(
        self,
        release_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags for a FRED release."""
        endpoint = "release/tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "release_id": str(release_id), "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if tag_names:
            params["tag_names"] = tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if search_text:
            params["search_text"] = search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def get_release_related_tags(
        self,
        release_id: int,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get related tags for a FRED release filtered by tag names."""
        endpoint = "release/related_tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "release_id": str(release_id), "tag_names": tag_names, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if search_text:
            params["search_text"] = search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def get_release_tables(
        self,
        release_id: int,
        element_id: int | None = None,
        include_observation_values: bool = False,
        observation_date: str | None = None,
    ) -> str:
        """Get release table data for a FRED release."""
        endpoint = "release/tables"
        base_params, error = self._base_params()
        if error:
            return error
        if observation_date:
            err = self._validate_date(observation_date, "observation_date")
            if err:
                return self._error_response(endpoint, "invalid_observation_date", err)
        params: dict[str, Any] = {**base_params, "release_id": str(release_id), "include_observation_values": str(include_observation_values).lower()}
        if element_id is not None:
            params["element_id"] = str(element_id)
        if observation_date:
            params["observation_date"] = observation_date
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        return self._success_response(endpoint, params, response["data"])

    # -------------------------------------------------------------------------
    # Group 4: Sources
    # -------------------------------------------------------------------------

    async def get_source(
        self,
        source_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
    ) -> str:
        """Get information about a specific FRED source."""
        endpoint = "source"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "source_id": str(source_id)}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        sources = data.get("sources", [])
        return self._success_response(endpoint, params, sources[0] if sources else None)

    async def get_source_releases(
        self,
        source_id: int,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get releases for a specific FRED source."""
        endpoint = "source/releases"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        params: dict[str, Any] = {**base_params, "source_id": str(source_id), "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        releases = data.get("releases", [])
        return self._success_response(endpoint, params, releases, meta={"count": len(releases), "limit": data.get("limit"), "offset": data.get("offset")})

    # -------------------------------------------------------------------------
    # Group 5: Tags
    # -------------------------------------------------------------------------

    async def get_related_tags(
        self,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        tag_group_id: str | None = None,
        search_text: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get tags related to one or more FRED tags."""
        endpoint = "related_tags"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        params: dict[str, Any] = {**base_params, "tag_names": tag_names, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        if tag_group_id:
            params["tag_group_id"] = tag_group_id
        if search_text:
            params["search_text"] = search_text
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        tags = data.get("tags", [])
        return self._success_response(endpoint, params, tags, meta={"count": len(tags)})

    async def get_tags_series(
        self,
        tag_names: str,
        realtime_start: str | None = None,
        realtime_end: str | None = None,
        exclude_tag_names: str | None = None,
        limit: int = 1000,
        offset: int = 0,
        order_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """Get series matching one or more FRED tags."""
        endpoint = "tags/series"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(realtime_start, "realtime_start"), (realtime_end, "realtime_end")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(endpoint, f"invalid_{name}", err)
        if sort_order not in self.ALLOWED_SORT_ORDER:
            return self._error_response(endpoint, "invalid_sort_order", "sort_order must be 'asc' or 'desc'.")
        if not (self.MIN_LIMIT <= limit <= self.MAX_LIMIT):
            return self._error_response(endpoint, "invalid_limit", f"limit must be between {self.MIN_LIMIT} and {self.MAX_LIMIT}.")
        params: dict[str, Any] = {**base_params, "tag_names": tag_names, "limit": limit, "offset": offset, "sort_order": sort_order}
        if realtime_start:
            params["realtime_start"] = realtime_start
        if realtime_end:
            params["realtime_end"] = realtime_end
        if exclude_tag_names:
            params["exclude_tag_names"] = exclude_tag_names
        if order_by:
            params["order_by"] = order_by
        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(endpoint, code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        series_list = data.get("seriess", [])
        return self._success_response(endpoint, params, series_list, meta={"count": len(series_list), "total": data.get("count"), "limit": data.get("limit"), "offset": data.get("offset")})

    # -------------------------------------------------------------------------
    # Group 6: GeoFRED
    # -------------------------------------------------------------------------

    GEOFRED_API_BASE = "https://api.stlouisfed.org/geofred"

    @staticmethod
    async def make_geofred_request(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a request to the GeoFRED API with retries and detailed errors."""
        headers = {
            "User-Agent": FREDService.USER_AGENT,
            "Accept": "application/json"
        }
        timeout_seconds = float(os.getenv("FRED_HTTP_TIMEOUT", "30"))
        max_retries = int(os.getenv("FRED_HTTP_MAX_RETRIES", "2"))
        retry_backoff = float(os.getenv("FRED_HTTP_RETRY_BACKOFF", "0.5"))
        retry_statuses = {429, 500, 502, 503, 504}

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
                    response = await client.get(f"{FREDService.GEOFRED_API_BASE}/{endpoint}", params=params)

                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text}

                if response.status_code in retry_statuses and attempt < max_retries:
                    await asyncio.sleep(retry_backoff * (2 ** attempt))
                    continue

                if response.is_error:
                    return {"ok": False, "status_code": response.status_code, "error": body}

                return {"ok": True, "status_code": response.status_code, "data": body}
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    await asyncio.sleep(retry_backoff * (2 ** attempt))
                    continue
                return {"ok": False, "status_code": None, "error": {"error_code": "network_error", "error_message": str(exc)}}
            except Exception as exc:  # noqa: BLE001
                return {"ok": False, "status_code": None, "error": {"error_code": "unexpected_error", "error_message": str(exc)}}

        return {"ok": False, "status_code": None, "error": {"error_code": "retry_exhausted", "error_message": "Request retries were exhausted without a response."}}

    async def get_geofred_series_group(self, series_id: str) -> str:
        """Get metadata for a geographic FRED series."""
        endpoint = "series/group"
        base_params, error = self._base_params()
        if error:
            return error
        params: dict[str, Any] = {**base_params, "series_id": series_id}
        response = await self.make_geofred_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(f"geofred/{endpoint}", code, message, status_code=response["status_code"], params=params, details=response["error"])
        return self._success_response(f"geofred/{endpoint}", params, response["data"].get("series_group"))

    async def get_geofred_series_data(
        self,
        series_id: str,
        date: str | None = None,
        start_date: str | None = None,
    ) -> str:
        """Get cross-sectional regional data for a geographic FRED series."""
        endpoint = "series/data"
        base_params, error = self._base_params()
        if error:
            return error
        for val, name in [(date, "date"), (start_date, "start_date")]:
            err = self._validate_date(val, name)
            if err:
                return self._error_response(f"geofred/{endpoint}", f"invalid_{name}", err)
        params: dict[str, Any] = {**base_params, "series_id": series_id}
        if date:
            params["date"] = date
        if start_date:
            params["start_date"] = start_date
        response = await self.make_geofred_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(f"geofred/{endpoint}", code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        return self._success_response(f"geofred/{endpoint}", params, data.get("data"), meta=data.get("meta"))

    async def get_geofred_regional_data(
        self,
        series_group: str,
        region_type: str,
        date: str,
        season: str,
        units: str,
        frequency: str,
        start_date: str | None = None,
        transformation: str | None = None,
        aggregation_method: str | None = None,
    ) -> str:
        """Get cross-sectional regional data by series group."""
        endpoint = "regional/data"
        base_params, error = self._base_params()
        if error:
            return error

        allowed_region_types = {"bea", "msa", "frb", "necta", "state", "country", "county", "censusregion"}
        if region_type not in allowed_region_types:
            return self._error_response(f"geofred/{endpoint}", "invalid_region_type", f"region_type must be one of: {', '.join(sorted(allowed_region_types))}.")
        allowed_seasons = {"SA", "NSA", "SSA", "SAAR", "NSAAR"}
        if season not in allowed_seasons:
            return self._error_response(f"geofred/{endpoint}", "invalid_season", f"season must be one of: {', '.join(sorted(allowed_seasons))}.")
        err = self._validate_date(date, "date")
        if err:
            return self._error_response(f"geofred/{endpoint}", "invalid_date", err)
        if start_date:
            err = self._validate_date(start_date, "start_date")
            if err:
                return self._error_response(f"geofred/{endpoint}", "invalid_start_date", err)
        if frequency not in self.ALLOWED_FREQUENCY:
            return self._error_response(f"geofred/{endpoint}", "invalid_frequency", f"frequency is required and must be one of: {', '.join(sorted(self.ALLOWED_FREQUENCY))}.")
        if transformation is not None and transformation not in self.ALLOWED_UNITS:
            return self._error_response(f"geofred/{endpoint}", "invalid_transformation", "transformation must be a valid FRED units code (lin, chg, ch1, pch, etc.).")
        if aggregation_method is not None and aggregation_method not in self.ALLOWED_AGGREGATION_METHOD:
            return self._error_response(f"geofred/{endpoint}", "invalid_aggregation_method", "aggregation_method must be one of: avg, sum, eop.")

        params: dict[str, Any] = {**base_params, "series_group": series_group, "region_type": region_type, "date": date, "season": season, "units": units, "frequency": frequency}
        if start_date:
            params["start_date"] = start_date
        if transformation:
            params["transformation"] = transformation
        if aggregation_method:
            params["aggregation_method"] = aggregation_method
        response = await self.make_geofred_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(f"geofred/{endpoint}", code, message, status_code=response["status_code"], params=params, details=response["error"])
        data = response["data"]
        return self._success_response(f"geofred/{endpoint}", params, data.get("data"), meta=data.get("meta"))

    async def get_geofred_shapes(self, shape: str) -> str:
        """Get GeoJSON shape files for geographic region boundaries."""
        endpoint = "shapes/file"
        base_params, error = self._base_params()
        if error:
            return error
        allowed_shapes = {"bea", "msa", "frb", "necta", "state", "country", "county", "censusregion", "censusdivision"}
        if shape not in allowed_shapes:
            return self._error_response(f"geofred/{endpoint}", "invalid_shape", f"shape must be one of: {', '.join(sorted(allowed_shapes))}.")
        params: dict[str, Any] = {**base_params, "shape": shape}
        response = await self.make_geofred_request(endpoint, params)
        if not response["ok"]:
            code, message = self._extract_error_message(response["error"])
            return self._error_response(f"geofred/{endpoint}", code, message, status_code=response["status_code"], params=params, details=response["error"])
        return self._success_response(f"geofred/{endpoint}", params, response["data"])
