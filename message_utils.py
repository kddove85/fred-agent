import json

def truncate_messages(messages: list, max_messages: int = 20) -> list:
    """Keep only recent messages while maintaining proper message structure."""
    if len(messages) <= max_messages:
        return messages

    truncated = [messages[0]]
    recent = messages[-(max_messages-1):]

    # Find a safe starting point
    start_idx = 0
    for i, msg in enumerate(recent):
        if msg.get('tool_calls'):
            start_idx = i
            break
        if msg.get('role') == 'tool':
            start_idx = i + 1

    truncated.extend(recent[start_idx:])
    return truncated

def is_incomplete_response(message_content: str) -> bool:
    """Check if the LLM response indicates it will take more actions."""
    if not message_content:
        return True

    incomplete_phrases = [
        "i'll now", "i will now", "let me fetch", "let me get",
        "i need to", "next, i'll", "i'll retrieve", "i will retrieve"
    ]

    outdated_indicators = [
        "as of my last update", "my training data", "as of 2023",
        "through 2023", "the current year is 2023", "as of april 2024"
    ]

    content_lower = message_content.lower()
    has_outdated = any(phrase in content_lower for phrase in outdated_indicators)

    return any(phrase in content_lower for phrase in incomplete_phrases) or has_outdated

def format_tool_result(result_text: str, tool_input: dict, max_length: int = 2000) -> str:
    """Format tool results intelligently, with special handling for time series data."""
    try:
        data = json.loads(result_text)

        if isinstance(data, list) and len(data) > 0:
            is_desc_sorted = tool_input.get('sort_order') == 'desc'

            if is_desc_sorted:
                summary = {
                    "note": "Data sorted by most recent first",
                    "latest_observation": data[0],
                    "total_observations": len(data),
                    "all_observations": data if len(data) <= 10 else data[:10]
                }
            else:
                summary = {
                    "note": "Data sorted by oldest first",
                    "latest_observation": data[-1],
                    "total_observations": len(data),
                    "recent_observations": data[-10:] if len(data) > 10 else data
                }

            return json.dumps(summary, indent=2)
        else:
            return json.dumps(data, indent=2)

    except (json.JSONDecodeError, TypeError):
        if len(result_text) > max_length:
            return result_text[:max_length] + f"... (truncated from {len(result_text)} chars)"
        return result_text
