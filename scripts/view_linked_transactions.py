#!/usr/bin/env python3
"""
View all linked transactions (Bank <-> Splitwise pairs)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database.connection import get_db_connection
import sys

def view_linked_transactions(session_id=None):
    """
    Display all linked transaction pairs
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build WHERE clause
    where_clause = ""
    params = []
    
    if session_id:
        where_clause = "WHERE t1.upload_session_id = %s"
        params = [session_id]
    
    # Get all linked pairs
    query = f"""
        SELECT 
            t1.id as bank_id,
            t1.date as bank_date,
            t1.description as bank_desc,
            t1.amount as bank_amount,
            t1.category as bank_category,
            t2.id as split_id,
            t2.date as split_date,
            t2.description as split_desc,
            t2.meta_total_bill as total_bill,
            t2.amount as split_amount,
            t2.category as split_category,
            t1.match_confidence,
            t1.match_method
        FROM transactions t1
        JOIN transactions t2 ON t1.link_id = t2.id
        {where_clause}
        AND t1.source = 'BANK'
        AND t2.source = 'SPLITWISE'
        AND t1.status = 'LINKED'
        ORDER BY t1.date DESC
    """
    
    cur.execute(query, params)
    results = cur.fetchall()
    
    if not results:
        print("\n❌ No linked transactions found")
        if session_id:
            print(f"   For session: {session_id}")
        cur.close()
        conn.close()
        return
    
    print("\n" + "="*100)
    print(f"🔗 LINKED TRANSACTIONS ({len(results)} pairs)")
    if session_id:
        print(f"   Session: {session_id}")
    print("="*100)
    
    for i, row in enumerate(results, 1):
        bank_id, bank_date, bank_desc, bank_amount, bank_cat = row[0:5]
        split_id, split_date, split_desc, total_bill, split_amount, split_cat = row[5:11]
        confidence, method = row[11:13]
        
        # Calculate your share
        your_share = total_bill - abs(split_amount) if total_bill else 0
        
        print(f"\n{'─'*100}")
        print(f"Pair #{i}")
        print(f"{'─'*100}")
        
        # Bank side
        print(f"🏦 BANK:")
        print(f"   Date:        {bank_date}")
        print(f"   Amount:      ₹{abs(bank_amount):,.2f}")
        print(f"   Description: {bank_desc[:60]}")
        print(f"   Category:    {bank_cat}")
        
        # Splitwise side
        print(f"\n🍕 SPLITWISE:")
        print(f"   Date:        {split_date}")
        print(f"   Total Bill:  ₹{total_bill:,.2f}")
        print(f"   Your Share:  ₹{your_share:,.2f}")
        print(f"   Description: {split_desc[:60]}")
        print(f"   Category:    {split_cat}")
        
        # Match details
        print(f"\n🎯 MATCH:")
        if confidence:
            print(f"   Confidence:  {confidence*100:.0f}%")
        if method:
            print(f"   Method:      {method}")
        
        # Date difference
        if bank_date and split_date:
            diff = abs((bank_date - split_date).days)
            if diff == 0:
                print(f"   Date Match:  ✓ Same day")
            else:
                print(f"   Date Match:  ± {diff} days")
    
    print(f"\n{'='*100}")
    print(f"✅ Total Linked Pairs: {len(results)}")
    print(f"{'='*100}\n")
    
    cur.close()
    conn.close()


def list_sessions():
    """Show available sessions"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            id,
            selected_month,
            bank_count + splitwise_count as total_txns,
            created_at
        FROM upload_sessions
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    sessions = cur.fetchall()
    
    if not sessions:
        print("\n❌ No sessions found")
        cur.close()
        conn.close()
        return
    
    print("\n" + "="*80)
    print("📁 AVAILABLE SESSIONS")
    print("="*80)
    
    for session in sessions:
        session_id, month, total, created = session
        print(f"\n{session_id}")
        print(f"   Month: {month} | Transactions: {total} | Created: {created}")
    
    print("\n" + "="*80 + "\n")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("\n💡 Usage:")
        print("   python view_linked_transactions.py <session_id>")
        print("   python view_linked_transactions.py --list-sessions")
        print("\nExamples:")
        print("   python view_linked_transactions.py session_abc123def456")
        print("   python view_linked_transactions.py --list-sessions")
        sys.exit(0)
    
    if sys.argv[1] == "--list-sessions":
        list_sessions()
    else:
        session_id = sys.argv[1]
        view_linked_transactions(session_id)