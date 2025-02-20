import datetime

def create_log_entry(final_gemini_output):
    """Create a structured log entry for conversation tracking."""
    return {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),  # ✅ Fixed timezone-aware datetime
        "final_gemini_output": final_gemini_output
    }
