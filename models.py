from pydantic import BaseModel
from typing import List, Optional
from datetime import date

# Basic request model
class ChatRequest(BaseModel):
    message: str
    email: Optional[str] = None  # Add this line

# User profile model
class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weekly_mileage: Optional[int] = None
    race_type: Optional[str] = None
    best_time: Optional[str] = None
    best_time_date: Optional[date] = None
    last_time: Optional[str] = None
    last_time_date: Optional[date] = None
    target_race: Optional[str] = None
    target_time: Optional[str] = None
    injury_history: Optional[List[str]] = None
    nutrition: Optional[List[str]] = None
    last_check_in: Optional[date] = None