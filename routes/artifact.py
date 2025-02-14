@router.post("/artifact/step/{step_name}")
async def submit_step(step_name: str, input_data: StepInput):
    """Process user input, save conversation history, and store final agreed artifact."""
    workflow = load_workflow()
    step = find_step(step_name, workflow)

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    artifact = load_artifact()
    chat_history = load_chat_history()

    # ✅ Save user response to chat history
    chat_history.append({"role": "user", "text": input_data.response})
    save_chat_history(chat_history)

    # ✅ LLM should generate a refined response
    refined_response = f"Refined artifact suggestion: {input_data.response} (improved by LLM)"
    
    # ✅ Save LLM response to chat history
    chat_history.append({"role": "bot", "text": refined_response})
    save_chat_history(chat_history)

    # ✅ Check if the user has confirmed the final artifact
    if input_data.response.lower() in ["yes", "i like that", "approved"]:
        # ✅ Store the final artifact
        last_llm_message = next((msg["text"] for msg in reversed(chat_history) if msg["role"] == "bot"), None)
        if last_llm_message:
            artifact["data"][step["step"]] = last_llm_message  # ✅ Save final artifact
            save_artifact(artifact)

    next_step = get_next_step(step["step"], workflow)
    if next_step:
        artifact["current_step"] = next_step
    else:
        artifact["current_step"] = "complete"  # ✅ Mark workflow as complete

    save_artifact(artifact)

    return {"message": "Step saved", "next_step": artifact["current_step"], "chat_history": chat_history}
