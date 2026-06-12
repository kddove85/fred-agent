from typing import Any
import asyncio
import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()


class CensusService:
    """Service for interacting with the US Census Bureau Data API."""

    CENSUS_API_BASE = "https://api.census.gov/data"
    USER_AGENT = "census-service/1.0"
    API_KEY = os.getenv("CENSUS_API_KEY")

    # Dataset paths (pinned to most recent stable year)
    ACS5_PATH = "2023/acs/acs5"        # American Community Survey 5-Year
    CBP_PATH = "2022/cbp"               # County Business Patterns
    SAIPE_PATH = "2022/saipe"           # Small Area Income and Poverty Estimates
    PEP_PATH = "2023/pep/population"    # Population Estimates Program

    # Valid 2-digit state FIPS codes
    VALID_STATE_FIPS = {
        "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13",
        "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25",
        "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36",
        "37", "38", "39", "40", "41", "42", "44", "45", "46", "47", "48",
        "49", "50", "51", "53", "54", "55", "56", "72",
    }

    # Convenience: state name → FIPS
    STATE_NAME_TO_FIPS: dict[str, str] = {
        "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05",
        "california": "06", "colorado": "08", "connecticut": "09", "delaware": "10",
        "district of columbia": "11", "florida": "12", "georgia": "13",
        "hawaii": "15", "idaho": "16", "illinois": "17", "indiana": "18",
        "iowa": "19", "kansas": "20", "kentucky": "21", "louisiana": "22",
        "maine": "23", "maryland": "24", "massachusetts": "25", "michigan": "26",
        "minnesota": "27", "mississippi": "28", "missouri": "29", "montana": "30",
        "nebraska": "31", "nevada": "32", "new hampshire": "33", "new jersey": "34",
        "new mexico": "35", "new york": "36", "north carolina": "37",
        "north dakota": "38", "ohio": "39", "oklahoma": "40", "oregon": "41",
        "pennsylvania": "42", "rhode island": "44", "south carolina": "45",
        "south dakota": "46", "tennessee": "47", "texas": "48", "utah": "49",
        "vermont": "50", "virginia": "51", "washington": "53",
        "west virginia": "54", "wisconsin": "55", "wyoming": "56",
        "puerto rico": "72",
    }

    @staticmethod
    def _json_response(payload: dict[str, Any]) -> str:
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
        payload: dict[str, Any] = {
            "ok": False,
            "endpoint": endpoint,
            "error": {"code": code, "message": message},
        }
        if status_code is not None:
            payload["status_code"] = status_code
        if params is not None:
            payload["params"] = {k: v for k, v in params.items() if k != "key"}
        if details is not None:
            payload["details"] = details
        return CensusService._json_response(payload)

    @staticmethod
    def _success_response(
        endpoint: str,
        params: dict[str, Any],
        data: Any,
        *,
        meta: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "ok": True,
            "endpoint": endpoint,
            "params": {k: v for k, v in params.items() if k != "key"},
            "data": data,
        }
        if meta:
            payload["meta"] = meta
        return CensusService._json_response(payload)

    @staticmethod
    def _parse_response(raw: list[list[str]]) -> list[dict[str, str]]:
        """Transpose Census JSON array (headers + rows) into list-of-dicts."""
        if not raw or len(raw) < 2:
            return []
        headers = raw[0]
        return [dict(zip(headers, row)) for row in raw[1:]]

    def _resolve_state_fips(self, value: str) -> tuple[str | None, str | None]:
        """Resolve state FIPS from FIPS code or state name. Returns (fips, error_msg)."""
        if value == "*":
            return "*", None
        # Try direct FIPS
        padded = value.zfill(2)
        if padded in self.VALID_STATE_FIPS:
            return padded, None
        # Try state name
        name_fips = self.STATE_NAME_TO_FIPS.get(value.lower().strip())
        if name_fips:
            return name_fips, None
        return None, (
            f"'{value}' is not a valid state FIPS code or state name. "
            "Use a 2-digit FIPS code (e.g. '06' for California), a state name, or '*' for all states."
        )

    def _base_params(self) -> tuple[dict[str, Any] | None, str | None]:
        """Return base parameters or an error when the API key is missing."""
        if not self.API_KEY:
            return None, self._error_response(
                "auth",
                "missing_api_key",
                "CENSUS_API_KEY is not configured. Get a free key at https://api.census.gov/data/key_signup.html",
            )
        return {"key": self.API_KEY}, None

    @staticmethod
    async def make_request(dataset_path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Make a Census API request with retry logic."""
        headers = {
            "User-Agent": CensusService.USER_AGENT,
            "Accept": "application/json",
        }
        url = f"{CensusService.CENSUS_API_BASE}/{dataset_path}"
        timeout_seconds = float(os.getenv("CENSUS_HTTP_TIMEOUT", "30"))
        max_retries = int(os.getenv("CENSUS_HTTP_MAX_RETRIES", "2"))
        retry_backoff = float(os.getenv("CENSUS_HTTP_RETRY_BACKOFF", "0.5"))
        retry_statuses = {429, 500, 502, 503, 504}

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=timeout_seconds, headers=headers, follow_redirects=True
                ) as client:
                    response = await client.get(url, params=params)

                # Census returns HTML for missing-key errors with 200 status
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    return {
                        "ok": False,
                        "status_code": response.status_code,
                        "error": {
                            "error_code": "html_response",
                            "error_message": "Census API returned HTML instead of JSON. The API key may be missing or invalid.",
                        },
                    }

                try:
                    body = response.json()
                except ValueError:
                    body = {"raw": response.text[:500]}

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
                return {
                    "ok": False, "status_code": None,
                    "error": {"error_code": "network_error", "error_message": str(exc)},
                }
            except Exception as exc:  # noqa: BLE001
                return {
                    "ok": False, "status_code": None,
                    "error": {"error_code": "unexpected_error", "error_message": str(exc)},
                }

        return {
            "ok": False, "status_code": None,
            "error": {"error_code": "retry_exhausted", "error_message": "Request retries exhausted."},
        }

    # -------------------------------------------------------------------------
    # ACS 5-Year: Income
    # -------------------------------------------------------------------------

    async def get_acs_income(
        self,
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get ACS income and poverty estimates by geography."""
        endpoint = self.ACS5_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        # Variables: median household income, per capita income, poverty count, total pop for poverty universe
        variables = "NAME,B19013_001E,B19301_001E,B17001_002E,B17001_001E"
        params: dict[str, Any] = {**base_params, "get": variables}

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = f"county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "median_household_income": r.get("B19013_001E"),
                "per_capita_income": r.get("B19301_001E"),
                "poverty_count": r.get("B17001_002E"),
                "poverty_universe": r.get("B17001_001E"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={"count": len(labeled), "year": "2023", "dataset": "ACS 5-Year"},
        )

    # -------------------------------------------------------------------------
    # ACS 5-Year: Demographics
    # -------------------------------------------------------------------------

    async def get_acs_demographics(
        self,
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get ACS demographic estimates (population, age, race) by geography."""
        endpoint = self.ACS5_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        # Total pop, male, female; white alone, black alone, asian alone, hispanic
        variables = (
            "NAME,"
            "B01001_001E,"   # total population
            "B01001_002E,"   # male
            "B01001_026E,"   # female
            "B02001_002E,"   # white alone
            "B02001_003E,"   # black or african american alone
            "B02001_005E,"   # asian alone
            "B03001_003E"    # hispanic or latino
        )
        params: dict[str, Any] = {**base_params, "get": variables}

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = "county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "total_population": r.get("B01001_001E"),
                "male": r.get("B01001_002E"),
                "female": r.get("B01001_026E"),
                "white_alone": r.get("B02001_002E"),
                "black_alone": r.get("B02001_003E"),
                "asian_alone": r.get("B02001_005E"),
                "hispanic_or_latino": r.get("B03001_003E"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={"count": len(labeled), "year": "2023", "dataset": "ACS 5-Year"},
        )

    # -------------------------------------------------------------------------
    # ACS 5-Year: Employment / Labor Force
    # -------------------------------------------------------------------------

    async def get_acs_employment(
        self,
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get ACS labor force and employment estimates by geography."""
        endpoint = self.ACS5_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        # B23025: Employment Status for Pop 16+
        variables = (
            "NAME,"
            "B23025_001E,"   # total pop 16+
            "B23025_002E,"   # in labor force
            "B23025_003E,"   # civilian labor force
            "B23025_004E,"   # employed
            "B23025_005E,"   # unemployed
            "B23025_006E,"   # armed forces
            "B23025_007E"    # not in labor force
        )
        params: dict[str, Any] = {**base_params, "get": variables}

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = "county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "population_16_plus": r.get("B23025_001E"),
                "in_labor_force": r.get("B23025_002E"),
                "civilian_labor_force": r.get("B23025_003E"),
                "employed": r.get("B23025_004E"),
                "unemployed": r.get("B23025_005E"),
                "armed_forces": r.get("B23025_006E"),
                "not_in_labor_force": r.get("B23025_007E"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={"count": len(labeled), "year": "2023", "dataset": "ACS 5-Year"},
        )

    # -------------------------------------------------------------------------
    # ACS 5-Year: Housing
    # -------------------------------------------------------------------------

    async def get_acs_housing(
        self,
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get ACS housing characteristic estimates by geography."""
        endpoint = self.ACS5_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        # Housing units, owner/renter-occupied, median home value, median gross rent
        variables = (
            "NAME,"
            "B25001_001E,"   # total housing units
            "B25002_002E,"   # occupied housing units
            "B25002_003E,"   # vacant housing units
            "B25003_002E,"   # owner-occupied
            "B25003_003E,"   # renter-occupied
            "B25077_001E,"   # median home value (owner-occupied)
            "B25064_001E"    # median gross rent
        )
        params: dict[str, Any] = {**base_params, "get": variables}

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = "county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "total_housing_units": r.get("B25001_001E"),
                "occupied_units": r.get("B25002_002E"),
                "vacant_units": r.get("B25002_003E"),
                "owner_occupied": r.get("B25003_002E"),
                "renter_occupied": r.get("B25003_003E"),
                "median_home_value": r.get("B25077_001E"),
                "median_gross_rent": r.get("B25064_001E"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={"count": len(labeled), "year": "2023", "dataset": "ACS 5-Year"},
        )

    # -------------------------------------------------------------------------
    # County Business Patterns
    # -------------------------------------------------------------------------

    async def get_county_business_patterns(
        self,
        state_fips: str,
        county_fips: str | None = None,
        naics_code: str | None = None,
    ) -> str:
        """Get County Business Patterns: establishments, employment, payroll by industry."""
        endpoint = self.CBP_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        variables = "NAME,ESTAB,EMP,PAYANN,NAICS2017,NAICS2017_LABEL"
        params: dict[str, Any] = {**base_params, "get": variables}

        # NAICS2017="00" means total-all-industries
        params["NAICS2017"] = naics_code if naics_code else "00"

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = "county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "naics_code": r.get("NAICS2017"),
                "naics_label": r.get("NAICS2017_LABEL"),
                "establishments": r.get("ESTAB"),
                "employees": r.get("EMP"),
                "annual_payroll_thousands": r.get("PAYANN"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={
                "count": len(labeled),
                "year": "2022",
                "dataset": "County Business Patterns",
                "naics_filter": params["NAICS2017"],
                "note": "EMP = employees in week of March 12; PAYANN = annual payroll in $1,000s",
            },
        )

    # -------------------------------------------------------------------------
    # SAIPE: Small Area Income and Poverty Estimates
    # -------------------------------------------------------------------------

    async def get_income_poverty_estimates(
        self,
        state_fips: str,
        county_fips: str | None = None,
    ) -> str:
        """Get SAIPE median household income and poverty rate estimates."""
        endpoint = self.SAIPE_PATH
        base_params, error = self._base_params()
        if error:
            return error

        resolved_state, err = self._resolve_state_fips(state_fips)
        if err:
            return self._error_response(endpoint, "invalid_state_fips", err)

        # SAEMHI_PT = median household income estimate
        # SAEPOVRAT_PT = poverty rate estimate (all ages)
        # SAEPOVRTCH_PT = child poverty rate estimate (ages 0-17)
        # SAEPOV_PT = number in poverty
        variables = "NAME,SAEMHI_PT,SAEPOVRAT_PT,SAEPOVRTCH_PT,SAEPOV_PT"
        params: dict[str, Any] = {**base_params, "get": variables}

        if county_fips and resolved_state != "*":
            county_padded = county_fips.zfill(3)
            params["for"] = f"county:{county_padded}"
            params["in"] = f"state:{resolved_state}"
        elif resolved_state == "*":
            params["for"] = "state:*"
        else:
            params["for"] = "county:*"
            params["in"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "county_fips": r.get("county"),
                "median_household_income": r.get("SAEMHI_PT"),
                "poverty_rate_pct": r.get("SAEPOVRAT_PT"),
                "child_poverty_rate_pct": r.get("SAEPOVRTCH_PT"),
                "poverty_count": r.get("SAEPOV_PT"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={
                "count": len(labeled),
                "year": "2022",
                "dataset": "SAIPE",
                "note": "poverty_rate_pct and child_poverty_rate_pct are percentages (0-100)",
            },
        )

    # -------------------------------------------------------------------------
    # Population Estimates Program (PEP)
    # -------------------------------------------------------------------------

    async def get_population_estimates(
        self,
        state_fips: str | None = None,
    ) -> str:
        """Get current population estimates from the Population Estimates Program."""
        endpoint = self.PEP_PATH
        base_params, error = self._base_params()
        if error:
            return error

        variables = "NAME,POP_2023,DENSITY_2023"
        params: dict[str, Any] = {**base_params, "get": variables}

        if state_fips is None or state_fips == "*":
            params["for"] = "state:*"
        else:
            resolved_state, err = self._resolve_state_fips(state_fips)
            if err:
                return self._error_response(endpoint, "invalid_state_fips", err)
            params["for"] = f"state:{resolved_state}"

        response = await self.make_request(endpoint, params)
        if not response["ok"]:
            err_body = response.get("error", {})
            return self._error_response(
                endpoint, str(err_body.get("error_code", "request_failed")),
                str(err_body.get("error_message", "Census request failed.")),
                status_code=response.get("status_code"), params=params, details=err_body,
            )

        rows = self._parse_response(response["data"])
        labeled = [
            {
                "name": r.get("NAME"),
                "state_fips": r.get("state"),
                "population_2023": r.get("POP_2023"),
                "population_density_per_sq_mile": r.get("DENSITY_2023"),
            }
            for r in rows
        ]
        return self._success_response(
            endpoint, params, labeled,
            meta={"count": len(labeled), "year": "2023", "dataset": "Population Estimates Program"},
        )
