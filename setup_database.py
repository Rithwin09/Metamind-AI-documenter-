import sqlite3

# Connect to the SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('sample.db')
cursor = conn.cursor()

print("Creating tables...")

# Create the 'users' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# Create the 'orders' table
cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_name TEXT NOT NULL,
    amount_usd DECIMAL(10, 2),
    order_date DATE,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
);
''')

print("Database 'sample.db' and tables created successfully.")

# Commit the changes and close the connection
conn.commit()
conn.close()