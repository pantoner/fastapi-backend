import datetime

def create_log_entry(user_input, corrected_input, flan_t5_output, sent_to_gemini, final_gemini_output):
    """Create a structured log entry for conversation tracking."""
    return {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),  # ✅ Fixed timezone-aware datetime
        "user_input": user_input,
        "corrected_input": corrected_input,
        "flan_t5_output": flan_t5_output,
        "sent_to_gemini": sent_to_gemini,
        "final_gemini_output": final_gemini_output
    }
