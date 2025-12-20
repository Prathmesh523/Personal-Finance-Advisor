#!/usr/bin/env python3
"""
Reset database schema - Drop all tables and create fresh ones
"""
import psycopg2
from app.database.connection import DB_CONFIG

def reset_schema():
    """Drop all tables and recreate with new schema"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    
    print("\n" + "="*60)
    print("🗑️  DROPPING OLD TABLES")
    print("="*60)
    
    # Drop old tables (order matters - FK constraints)
    tables_to_drop = [
        "bank_transactions", 
        "splitwise_transactions",
        "upload_sessions"
    ]
    
    for table in tables_to_drop:
        try:
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"   ✅ Dropped {table}")
        except Exception as e:
            print(f"   ⚠️  {table}: {e}")
    
    print("\n" + "="*60)
    print("🏗️  CREATING NEW TABLES")
    print("="*60)
    
    # Create upload_sessions table
    cur.execute("""
        CREATE TABLE upload_sessions (
            id VARCHAR(50) PRIMARY KEY,
            user_id INTEGER NOT NULL,
            selected_month VARCHAR(7) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR(20) DEFAULT 'processing',
            bank_count INTEGER DEFAULT 0,
            splitwise_count INTEGER DEFAULT 0,
            excluded_count INTEGER DEFAULT 0,
            skipped_not_involved INTEGER DEFAULT 0,
            user_config JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Created upload_sessions")
    
    # Create splitwise_transactions table (first, because bank references it)
    cur.execute("""
        CREATE TABLE splitwise_transactions (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            upload_session_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            total_cost NUMERIC(10, 2) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            
            my_column_value NUMERIC(10, 2) NOT NULL,
            my_share NUMERIC(10, 2) NOT NULL,
            role VARCHAR(50) NOT NULL,
            
            status VARCHAR(50) DEFAULT 'UNLINKED',
            linked_bank_id INTEGER,
            match_confidence NUMERIC(3, 2),
            match_method VARCHAR(50),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ Created splitwise_transactions")
    
    # Create bank_transactions table
    cur.execute("""
        CREATE TABLE bank_transactions (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(255) UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            upload_session_id VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            description TEXT,
            category VARCHAR(100) DEFAULT 'Uncategorized',
            
            status VARCHAR(50) DEFAULT 'UNLINKED',
            linked_splitwise_id INTEGER,
            match_confidence NUMERIC(3, 2),
            match_method VARCHAR(50),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (linked_splitwise_id) REFERENCES splitwise_transactions(id) ON DELETE SET NULL
        )
    """)
    print("   ✅ Created bank_transactions")
    
    # Add FK from splitwise to bank (circular reference, so added after both tables exist)
    cur.execute("""
        ALTER TABLE splitwise_transactions
        ADD CONSTRAINT fk_splitwise_bank
        FOREIGN KEY (linked_bank_id) REFERENCES bank_transactions(id) ON DELETE SET NULL
    """)
    print("   ✅ Added foreign key constraints")
    
    print("\n" + "="*60)
    print("📊 CREATING INDEXES")
    print("="*60)
    
    # Bank transaction indexes
    bank_indexes = [
        "CREATE INDEX idx_bank_user_session ON bank_transactions(user_id, upload_session_id)",
        "CREATE INDEX idx_bank_date ON bank_transactions(date)",
        "CREATE INDEX idx_bank_status ON bank_transactions(status)",
        "CREATE INDEX idx_bank_amount ON bank_transactions(amount) WHERE amount < 0",
        "CREATE INDEX idx_bank_category ON bank_transactions(category)",
        "CREATE INDEX idx_bank_linked_splitwise ON bank_transactions(linked_splitwise_id) WHERE linked_splitwise_id IS NOT NULL"
    ]
    
    for idx_sql in bank_indexes:
        cur.execute(idx_sql)
    print("   ✅ Created bank_transactions indexes")
    
    # Splitwise transaction indexes
    split_indexes = [
        "CREATE INDEX idx_split_user_session ON splitwise_transactions(user_id, upload_session_id)",
        "CREATE INDEX idx_split_date ON splitwise_transactions(date)",
        "CREATE INDEX idx_split_status ON splitwise_transactions(status)",
        "CREATE INDEX idx_split_role ON splitwise_transactions(role)",
        "CREATE INDEX idx_split_category ON splitwise_transactions(category)",
        "CREATE INDEX idx_split_linked_bank ON splitwise_transactions(linked_bank_id) WHERE linked_bank_id IS NOT NULL"
    ]
    
    for idx_sql in split_indexes:
        cur.execute(idx_sql)
    print("   ✅ Created splitwise_transactions indexes")
    
    # Upload sessions indexes
    cur.execute("CREATE INDEX idx_session_user_month ON upload_sessions(user_id, selected_month)")
    cur.execute("CREATE INDEX idx_session_status ON upload_sessions(status)")
    print("   ✅ Created upload_sessions indexes")
    
    print("\n" + "="*60)
    print("✅ SCHEMA RESET COMPLETE!")
    print("="*60)
    print()
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        reset_schema()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()