import psycopg2
from psycopg2.extras import RealDictCursor

# Hardcoded for local dev, in prod use os.getenv()
DB_CONFIG = {
    "dbname": "finance_db",
    "user": "user",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise e