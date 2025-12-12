#!/usr/bin/env python3
"""
Quick test to verify settlement detection is working
"""
from app.database.connection import get_db_connection

def check_settlements():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n📊 SETTLEMENT DETECTION REPORT")
    print("=" * 60)
    
    # Count by status
    cur.execute("""
        SELECT status, COUNT(*), SUM(ABS(amount))
        FROM transactions
        GROUP BY status
    """)
    
    print("\nStatus Breakdown:")
    for row in cur.fetchall():
        status, count, total = row
        print(f"   {status:15} | Count: {count:4} | Total: ₹{total:,.2f}")
    
    # Show settlement details
    cur.execute("""
        SELECT date, description, ABS(amount) as amount, source
        FROM transactions
        WHERE category = 'Settlement'
        ORDER BY date DESC
    """)
    
    transfers = cur.fetchall()
    
    if transfers:
        print(f"\n🔍 Settlement Transactions ({len(transfers)} found):")
        for txn in transfers:
            date, desc, amount, source = txn
            print(f"   {date} | {source:10} | ₹{amount:8.2f} | {desc[:40]}")
    else:
        print("\n⚠️  No settlements detected yet.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_settlements()