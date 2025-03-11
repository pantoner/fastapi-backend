@app.post("/profile-chat")
def profile_chat(req: ProfileChatRequest):
    """
    1) Find/create user in DB by email
    2) Parse user's current message with 'extract_run_info' => store in appropriate DB fields
    3) Call the conversation manager => returns { profile_complete, final_prompt }
    4) If complete => short-circuit
    5) Otherwise => call query_openai_model(final_prompt) => return to user
    """

    # 1) Find user
    user = get_user_by_email(req.email)
    if not user:
        new_id = create_user("NewUser", req.email, "temp123")
        if not new_id:
            return {"assistant_response": "Error creating user in DB."}
        create_default_profile(new_id)
        user = get_user_by_email(req.email)
    user_id = user["id"]

    # 2) Get their DB profile
    db_profile = get_user_profile(user_id)
    if not db_profile:
        create_default_profile(user_id)
        db_profile = get_user_profile(user_id)

    # 2a) parse the user's message for fields
    parsed = extract_run_info(req.message)
    profile_updated = False
    
    # Process extracted data and update the profile
    # Weekly mileage - from "number" field
    if parsed["number"]:
        try:
            miles = int(parsed["number"])
            db_profile["weekly_mileage"] = miles
            profile_updated = True
            print(f"✅ Parsed weekly_mileage: {miles}")
        except ValueError:
            print(f"❌ Could not parse number as integer: {parsed['number']}")
    
    # Race type - from "racetype" field
    if parsed["racetype"]:
        db_profile["race_type"] = parsed["racetype"]
        profile_updated = True
        print(f"✅ Parsed race_type: {parsed['racetype']}")
    
    # Dates - could be for various date fields
    if parsed["dates"]:
        # The context of the conversation should determine which date field to update
        # For now, let's use context clues from the message to decide
        message_lower = req.message.lower()
        
        # Look for context clues in the message
        if "best" in message_lower or "pr" in message_lower or "personal record" in message_lower:
            db_profile["best_time_date"] = parsed["dates"]
            print(f"✅ Updated best_time_date: {parsed['dates']}")
        elif "last" in message_lower or "previous" in message_lower or "recent" in message_lower:
            db_profile["last_time_date"] = parsed["dates"]
            print(f"✅ Updated last_time_date: {parsed['dates']}")
        else:
            # Default to last_time_date if no specific context
            db_profile["last_time_date"] = parsed["dates"]
            print(f"✅ Updated last_time_date (default): {parsed['dates']}")
        
        profile_updated = True

    # 2b) Enhanced extraction based on conversation context
    message_lower = req.message.lower()
    
    # If race type is mentioned, see if "target" race is also mentioned
    if parsed["racetype"] and ("target" in message_lower or "upcoming" in message_lower or "next" in message_lower):
        # We already have the race type, now look for a specific race name
        # This is tricky without advanced NLP, but we'll use a simple approach
        
        # First try to extract proper nouns that might be race names
        # For simplicity, we'll check if there are words with capital letters that aren't at the start of a sentence
        words = req.message.split()
        capitalized_words = []
        
        for i, word in enumerate(words):
            # Skip first word of sentences
            if i > 0 and word[0].isupper() and not words[i-1].endswith('.'):
                capitalized_words.append(word)
        
        if capitalized_words and parsed["racetype"]:
            # If we found capitalized words, use them as the race name along with the race type
            race_name = " ".join(capitalized_words)
            db_profile["target_race"] = f"{race_name} {parsed['racetype']}"
            profile_updated = True
            print(f"✅ Extracted target_race: {db_profile['target_race']}")
        elif "yes" in message_lower and db_profile.get("race_type"):
            # If user confirms with "yes" and we have a race type, use it
            race_type = db_profile.get("race_type", "")
            if race_type:
                db_profile["target_race"] = f"{race_type}"
                profile_updated = True
                print(f"✅ Setting target_race from confirmation: {db_profile['target_race']}")

    # Time information (could be best_time, last_time, or target_time)
    import re
    time_match = re.search(r'(\d{1,2}):(\d{2})', message_lower)
    if time_match:
        time_str = f"{time_match.group(1)}:{time_match.group(2)}"
        
        # Determine which time field to update based on context
        if "target" in message_lower or "goal" in message_lower or "aiming for" in message_lower:
            db_profile["target_time"] = time_str
            print(f"✅ Updated target_time: {time_str}")
        elif "best" in message_lower or "pr" in message_lower or "fastest" in message_lower:
            db_profile["best_time"] = time_str
            print(f"✅ Updated best_time: {time_str}")
        elif "last" in message_lower or "previous" in message_lower or "recent" in message_lower:
            db_profile["last_time"] = time_str
            print(f"✅ Updated last_time: {time_str}")
        else:
            # If no context clues, use previous message history to determine intent
            # This is a simplified approach - ideally you'd track conversation state
            db_profile["target_time"] = time_str
            print(f"✅ Updated target_time (default): {time_str}")
        
        profile_updated = True

    # 2c) Save updated profile in DB only if we made changes
    if profile_updated:
        print(f"Saving updated profile to DB: {db_profile}")
        success = save_user_profile(user_id, db_profile)
        if not success:
            print("❌ Failed to save profile updates to database")
        else:
            print("✅ Successfully saved profile updates to database")
            # Refresh the profile data from the database to ensure we have the latest
            db_profile = get_user_profile(user_id)
            print(f"Refreshed profile from DB: {db_profile}")

    # 3) Call the conversation manager
    body = {
        "user_message": req.message,
        "profile_data": db_profile
    }
    try:
        manager_resp = requests.post(CONVERSATION_MANAGER_URL, json=body)
        if manager_resp.status_code != 200:
            return {
                "assistant_response": f"Error from manager: {manager_resp.text}",
                "profile_data": db_profile
            }
        manager_data = manager_resp.json()
    except Exception as e:
        return {
            "assistant_response": f"Could not contact manager: {str(e)}",
            "profile_data": db_profile
        }

    # 4) If profile_complete
    if manager_data.get("profile_complete"):
        return {
            "assistant_response": "Profile is complete!",
            "profile_data": db_profile
        }

    # 5) Otherwise, we get a final_prompt from the manager
    final_prompt = manager_data.get("final_prompt", "")
    updated_profile = manager_data.get("profile_data", db_profile)
    
    # If the manager returned updated profile data, save it to the database
    if updated_profile != db_profile:
        success = save_user_profile(user_id, updated_profile)
        if not success:
            print("❌ Failed to save manager-updated profile to database")
        else:
            print("✅ Successfully saved manager-updated profile to database")
            # Refresh again to ensure we have the latest data
            db_profile = get_user_profile(user_id)

    # We call openai to get a short response
    openai_reply = query_openai_model(final_prompt)

    return {
        "assistant_response": openai_reply,
        "profile_data": db_profile  # Return the latest profile from the database
    }