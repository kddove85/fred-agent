from datetime import datetime

def get_system_message() -> dict:
    return {
        "role": "system",
        "content": (
            "You are a helpful assistant with access to FRED economic data tools.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Your knowledge cutoff is November 2023, but you have access to CURRENT data through tools\n"
            "2. When asked about 'current', 'latest', or 'now', you MUST use tools to get recent data\n"
            "3. When using get_series_observations:\n"
            "   - For 'current' data: Set limit=10 and sort_order='desc' to get the 10 most recent values\n"
            "   - For historical data: Use appropriate observation_start/observation_end dates\n"
            "4. ALWAYS report the observation date along with the value\n"
            "5. The most recent observation in the tool results IS the current value\n"
            "6. Never answer with information from your training data when asked about current values\n\n"
            f"7. Today's date is {datetime.now().strftime('%Y-%m-%d')}\n\n"
            "Example: If asked 'What is the current GDP?', use get_series_observations with sort_order='desc' and limit=1"
        )
    }

def enhance_temporal_query(query: str) -> str:
    """Add temporal context hints to queries about current data."""
    temporal_keywords = ['current', 'latest', 'recent', 'now', 'today']
    if any(keyword in query.lower() for keyword in temporal_keywords):
        return (
            f"{query}\n\n"
            f"[System hint: When fetching data, use sort_order='desc' and limit=1 or limit=10 "
            f"to get the most recent observations efficiently.]"
        )
    return query
