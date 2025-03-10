import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import json

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Create a database connection and close it when done."""
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        # Return dictionary-like results
        conn.cursor_factory = RealDictCursor
        yield conn
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        raise
    finally:
        if conn is not None:
            conn.close()

def init_db():
    """Initialize the database schema."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Create users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                
                # Create user_profiles table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    age INTEGER,
                    weekly_mileage INTEGER,
                    race_type VARCHAR(50),
                    best_time VARCHAR(20),
                    best_time_date DATE,
                    last_time VARCHAR(20),
                    last_time_date DATE,
                    target_race VARCHAR(100),
                    target_time VARCHAR(20),
                    last_check_in DATE,
                    UNIQUE(user_id)
                );
                """)
                
                # Create injury_history table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS injury_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    description VARCHAR(200) NOT NULL
                );
                """)
                
                # Create nutrition_info table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS nutrition_info (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    description VARCHAR(200) NOT NULL
                );
                """)
                
                conn.commit()
                print("✅ Database schema initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")

def seed_db():
    """Add seed data if the database is empty."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if there are any users
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()['count']
                
                if user_count == 0:
                    # Add sample users
                    sample_users = [
                        ("Test User", "test@example.com", "plaintextpassword"),
                        ("Secure User", "secure@example.com", "mypassword"),
                        ("Final User", "final@example.com", "finalpassword"),
                        ("John Doe", "john@example.com", "password123")
                    ]
                    
                    for name, email, password in sample_users:
                        cursor.execute(
                            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id",
                            (name, email, password)
                        )
                        user_id = cursor.fetchone()['id']
                        
                        # Add a profile for John Doe
                        if email == "john@example.com":
                            cursor.execute("""
                            INSERT INTO user_profiles (
                                user_id, age, weekly_mileage, race_type, 
                                best_time, best_time_date, last_time, last_time_date,
                                target_race, target_time, last_check_in
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                user_id, 35, 40, "marathon",
                                "3:25:00", "2022-10-15", "3:45:00", "2023-10-15",
                                "Boston Marathon", "3:20:00", "2025-01-15"
                            ))
                            
                            # Add injury history
                            cursor.execute(
                                "INSERT INTO injury_history (user_id, description) VALUES (%s, %s)",
                                (user_id, "Hamstring strain")
                            )
                            
                            # Add nutrition info
                            cursor.execute(
                                "INSERT INTO nutrition_info (user_id, description) VALUES (%s, %s)",
                                (user_id, "No meat")
                            )
                            cursor.execute(
                                "INSERT INTO nutrition_info (user_id, description) VALUES (%s, %s)",
                                (user_id, "Eats spinach daily")
                            )
                    
                    conn.commit()
                    print("✅ Added seed users to database")
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")

def get_user_by_email(email):
    """Get a user by email."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, email, password FROM users WHERE email = %s",
                    (email,)
                )
                user = cursor.fetchone()
                return dict(user) if user else None
    except Exception as e:
        print(f"❌ Error getting user: {str(e)}")
        return None

def create_user(name, email, password):
    """Create a new user."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id",
                    (name, email, password)
                )
                user_id = cursor.fetchone()['id']
                conn.commit()
                return user_id
    except psycopg2.errors.UniqueViolation:
        # Handle duplicate email
        if 'conn' in locals() and conn:
            conn.rollback()
        return None
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return None

def get_user_profile(user_id):
    """Get a user profile with all related data."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get user data
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                
                if not user:
                    return None
                
                # Get profile data
                cursor.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
                profile = cursor.fetchone()
                
                # Get injury history
                cursor.execute("SELECT description FROM injury_history WHERE user_id = %s", (user_id,))
                injuries = [row['description'] for row in cursor.fetchall()]
                
                # Get nutrition info
                cursor.execute("SELECT description FROM nutrition_info WHERE user_id = %s", (user_id,))
                nutrition = [row['description'] for row in cursor.fetchall()]
                
                # Combine all data
                result = {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "injury_history": injuries,
                    "nutrition": nutrition
                }
                
                # Add profile data if it exists
                if profile:
                    for key, value in profile.items():
                        if key != 'id' and key != 'user_id':
                            result[key] = value
                
                return result
    except Exception as e:
        print(f"❌ Error getting user profile: {str(e)}")
        return None

def save_user_profile(user_id, profile_data):
    """Save or update a user profile."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Extract lists for separate tables
                injury_history = profile_data.pop('injury_history', [])
                nutrition = profile_data.pop('nutrition', [])
                
                # Check if profile exists
                cursor.execute("SELECT id FROM user_profiles WHERE user_id = %s", (user_id,))
                profile_exists = cursor.fetchone()
                
                if profile_exists:
                    # Update existing profile
                    set_clauses = []
                    values = []
                    
                    for key, value in profile_data.items():
                        if key not in ['id', 'user_id']:
                            set_clauses.append(f"{key} = %s")
                            values.append(value)
                    
                    if set_clauses:
                        query = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE user_id = %s"
                        values.append(user_id)
                        cursor.execute(query, values)
                else:
                    # Create new profile
                    columns = ['user_id'] + [k for k in profile_data.keys()]
                    placeholders = ['%s'] * len(columns)
                    values = [user_id] + [profile_data.get(k) for k in profile_data.keys()]
                    
                    query = f"INSERT INTO user_profiles ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    cursor.execute(query, values)
                
                # Delete existing injury history and nutrition
                cursor.execute("DELETE FROM injury_history WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM nutrition_info WHERE user_id = %s", (user_id,))
                
                # Insert new injury history
                for injury in injury_history:
                    cursor.execute(
                        "INSERT INTO injury_history (user_id, description) VALUES (%s, %s)",
                        (user_id, injury)
                    )
                
                # Insert new nutrition
                for item in nutrition:
                    cursor.execute(
                        "INSERT INTO nutrition_info (user_id, description) VALUES (%s, %s)",
                        (user_id, item)
                    )
                
                conn.commit()
                return True
    except Exception as e:
        print(f"❌ Error saving user profile: {str(e)}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False


def create_default_profile(user_id):
    """Creates a new profile with all fields set to None when a user registers."""
    default_profile = {
        "user_id": user_id,
        "name": None,
        "age": None,
        "weekly_mileage": None,
        "race_type": None,
        "best_time": None,
        "best_time_date": None,
        "last_time": None,
        "last_time_date": None,
        "target_race": None,
        "target_time": None,
        "last_check_in": None,
        "injury_history": [],
        "nutrition": []
    }
    save_user_profile(user_id, default_profile)  # Save to DB


