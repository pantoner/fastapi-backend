import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Check table structure
cursor.execute("PRAGMA table_info(users);")
columns = cursor.fetchall()

print("\n📌 Users Table Schema:")
for col in columns:
    print(col)  # Prints column ID, name, type, etc.

# Check existing data
cursor.execute("SELECT * FROM users;")
rows = cursor.fetchall()

print("\n📌 Existing Users Data:")
for row in rows:
    print(row)  # Prints existing rows in the users table

conn.close()
