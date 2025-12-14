import psycopg2

DB_CONFIG = {
    "dbname": "finance_db",
    "user": "user",
    "password": "password", 
    "host": "localhost",
    "port": "5432"
}

conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

print("🗑️ Dropping old tables...")
cur.execute("DROP TABLE IF EXISTS transactions CASCADE;")
cur.execute("DROP TABLE IF EXISTS upload_sessions CASCADE;")

cur.close()
conn.close()

print("✅ Tables dropped. Now run: python init_db.py")