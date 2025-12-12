import psycopg2
from app.database.connection import DB_CONFIG

def create_tables():
    commands = (
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            upload_session_id VARCHAR(50),
            date DATE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            source VARCHAR(50),
            status VARCHAR(50) DEFAULT 'UNLINKED',
            
            role VARCHAR(50),
            meta_total_bill NUMERIC(10, 2),
            link_id INTEGER,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS upload_sessions (
            id VARCHAR(50) PRIMARY KEY,
            user_id INTEGER NOT NULL,
            selected_month VARCHAR(7) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'processing',
            bank_count INTEGER DEFAULT 0,
            splitwise_count INTEGER DEFAULT 0,
            excluded_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        "CREATE INDEX IF NOT EXISTS idx_user_date ON transactions (user_id, date);",
        "CREATE INDEX IF NOT EXISTS idx_source_status ON transactions (source, status);",
        "CREATE INDEX IF NOT EXISTS idx_amount ON transactions (amount);",
        "CREATE INDEX IF NOT EXISTS idx_session ON transactions(upload_session_id);"
    )
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        conn.commit()
        cur.close()
        print("✅ Database schema updated successfully!")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ DB Error: {error}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_tables()