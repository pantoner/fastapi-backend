import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Insert a test user
cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", 
               ("John Doe", "john@example.com", "securepassword"))
conn.commit()

print("✅ Test user inserted successfully!")

# Retrieve and display users
cursor.execute("SELECT * FROM users;")
rows = cursor.fetchall()

print("\n📌 Users in Database:")
for row in rows:
    print(row)

conn.close
