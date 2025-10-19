import sqlite3
import os

# Connect to the database
conn = sqlite3.connect('app/medical_records.db')
cursor = conn.cursor()

# Add the encrypted_data column to the medical_record table
try:
    cursor.execute("ALTER TABLE medical_record ADD COLUMN encrypted_data TEXT")
    print("Successfully added encrypted_data column to medical_record table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("encrypted_data column already exists")
    else:
        print(f"Error adding column: {e}")

# Add the encrypted_data column to the patient table (if needed)
try:
    cursor.execute("ALTER TABLE patient ADD COLUMN encrypted_data TEXT")
    print("Successfully added encrypted_data column to patient table")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("encrypted_data column already exists in patient table")
    else:
        print(f"Error adding column to patient table: {e}")

conn.commit()
conn.close()

print("Database migration completed")