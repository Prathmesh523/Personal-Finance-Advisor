from app.database.connection import get_db_connection
from datetime import datetime

CATEGORY_MAPPING = {
    'General': 'Other',
    'Gas/fuel': 'Transport',
    'Bus/train': 'Transport',
    'Utilities - Other': 'Bills & Utilities',
}

def calculate_net_consumption(session_id, user_id=1):
    """
    Calculate consumption breakdown
    
    Returns:
    - Solo Spend: Unlinked bank transactions (exclude self-transfers)
    - My Share (I Paid): My share where I paid the bill (splitwise > 0)
    - My Share (They Paid): My share where friend paid (splitwise < 0)
    - Total: Sum of above three
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Solo Spend (unlinked bank, exclude self-transfers)
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND amount < 0
          AND status = 'UNLINKED'
          AND category NOT IN ('Self Transfer')
    """, (session_id, user_id))
    
    solo_spend = float(cur.fetchone()[0])
    
    # 2. My Share (I Paid) - where role = PAYER (not settlements)
    cur.execute("""
        SELECT COALESCE(SUM(my_share), 0)
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'PAYER'
    """, (session_id, user_id))
    
    split_i_paid = float(cur.fetchone()[0])
    
    # 3. My Share (They Paid) - where role = BORROWER
    cur.execute("""
        SELECT COALESCE(SUM(my_share), 0)
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'BORROWER'
    """, (session_id, user_id))
    
    split_they_paid = float(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
    total = solo_spend + split_i_paid + split_they_paid
    
    return {
        'total': round(total, 2),
        'breakdown': {
            'solo_spend': round(solo_spend, 2),
            'split_i_paid': round(split_i_paid, 2),
            'split_they_paid': round(split_they_paid, 2)
        }
    }

def calculate_cash_outflow(session_id, user_id=1):
    """
    Calculate total money that left your bank account
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND amount < 0
    """, (session_id, user_id))
    
    total = float(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
    return round(total, 2)

def calculate_monthly_float(session_id, user_id=1):
    """
    Calculate monthly float (difference between cash outflow and net consumption)
    """
    net_consumption = calculate_net_consumption(session_id, user_id)
    cash_outflow = calculate_cash_outflow(session_id, user_id)
    
    float_amount = cash_outflow - net_consumption['total']
    
    return round(float_amount, 2)

def get_category_breakdown(session_id, user_id=1):
    """
    Get spending breakdown by category
    Shows only CONSUMPTION (what you spent), not all transactions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    category_totals = {}
    
    # 1. Solo expenses (unlinked bank)
    cur.execute("""
        SELECT 
            category,
            SUM(ABS(amount)) as total_amount
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND amount < 0
          AND status = 'UNLINKED'
          AND category NOT IN ('Settlement', 'Investment', 'Credit Card', 'Savings', 'Self Transfer')
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        raw_category = row[0] or 'Other'
        category = CATEGORY_MAPPING.get(raw_category, raw_category)
        amount = float(row[1])
        category_totals[category] = category_totals.get(category, 0) + amount
    
    # 2. Split expenses (you paid) - use YOUR SHARE
    cur.execute("""
        SELECT 
            category,
            SUM(my_share) as your_share
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'PAYER'
          AND status = 'LINKED'
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        raw_category = row[0] or 'Other'
        category = CATEGORY_MAPPING.get(raw_category, raw_category)
        your_share = float(row[1])
        category_totals[category] = category_totals.get(category, 0) + your_share
    
    # 3. Split expenses (friend paid) - use YOUR SHARE
    cur.execute("""
        SELECT 
            category,
            SUM(my_share) as your_share
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'BORROWER'
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        raw_category = row[0] or 'Other'
        category = CATEGORY_MAPPING.get(raw_category, raw_category)
        amount = float(row[1])
        category_totals[category] = category_totals.get(category, 0) + amount
    
    cur.close()
    conn.close()
    
    # Calculate total for percentages
    total_spending = sum(category_totals.values())
    
    if total_spending == 0:
        return []
    
    # Convert to list and calculate percentages
    breakdown = []
    for category, amount in category_totals.items():
        percentage = (amount / total_spending * 100) if total_spending > 0 else 0
        breakdown.append({
            'category': category,
            'amount': round(amount, 2),
            'percentage': round(percentage, 1)
        })
    
    # Sort by amount descending
    breakdown.sort(key=lambda x: x['amount'], reverse=True)
    
    return breakdown

def get_transaction_stats(session_id, user_id=1):
    """
    Get general transaction statistics
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Total transactions (both tables)
    cur.execute("""
        SELECT 
            (SELECT COUNT(*) FROM bank_transactions WHERE upload_session_id = %s AND user_id = %s) +
            (SELECT COUNT(*) FROM splitwise_transactions WHERE upload_session_id = %s AND user_id = %s)
    """, (session_id, user_id, session_id, user_id))
    total_count = cur.fetchone()[0]
    
    # Status breakdown (bank)
    cur.execute("""
        SELECT status, COUNT(*) 
        FROM bank_transactions
        WHERE upload_session_id = %s AND user_id = %s
        GROUP BY status
    """, (session_id, user_id))
    status_breakdown = {row[0]: row[1] for row in cur.fetchall()}
    
    # Source breakdown
    cur.execute("""
        SELECT 
            'BANK' as source,
            (SELECT COUNT(*) FROM bank_transactions WHERE upload_session_id = %s AND user_id = %s)
        UNION ALL
        SELECT 
            'SPLITWISE' as source,
            (SELECT COUNT(*) FROM splitwise_transactions WHERE upload_session_id = %s AND user_id = %s)
    """, (session_id, user_id, session_id, user_id))
    source_breakdown = {row[0]: row[1] for row in cur.fetchall()}
    
    # Average transaction (bank only, expenses only)
    cur.execute("""
        SELECT AVG(ABS(amount))
        FROM bank_transactions
        WHERE upload_session_id = %s 
          AND user_id = %s
          AND status != 'TRANSFER'
          AND amount < 0
    """, (session_id, user_id))
    avg_transaction = float(cur.fetchone()[0] or 0)
    
    # Largest expense (bank)
    cur.execute("""
        SELECT description, ABS(amount), category
        FROM bank_transactions
        WHERE upload_session_id = %s 
          AND user_id = %s
          AND status != 'TRANSFER'
          AND amount < 0 
        ORDER BY ABS(amount) DESC
        LIMIT 1
    """, (session_id, user_id))
    
    largest = cur.fetchone()
    largest_expense = {
        'description': largest[0],
        'amount': float(largest[1]),
        'category': largest[2]
    } if largest else None
    
    cur.close()
    conn.close()
    
    return {
        'total_transactions': total_count,
        'status_breakdown': status_breakdown,
        'source_breakdown': source_breakdown,
        'avg_transaction': round(avg_transaction, 2),
        'largest_expense': largest_expense
    }

def get_unlinked_splitwise_payer(session_id, user_id=1):
    """
    Get unlinked Splitwise transactions where you were the PAYER
    These might be causing double-counting in solo expenses
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            date,
            description,
            total_cost,
            my_share,
            category
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'PAYER'
          AND status = 'UNLINKED'
        ORDER BY date DESC
    """, (session_id, user_id))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    unlinked = []
    total_amount = 0
    
    for row in results:
        date, desc, total_cost, my_share, category = row
        total_cost = float(total_cost) if total_cost else 0
        my_share = float(my_share)
        
        # What friends owe you = total - your share
        owed_to_you = total_cost - my_share
        
        unlinked.append({
            'date': date,
            'description': desc,
            'total_bill': total_cost,
            'your_share': my_share,
            'owed_to_you': owed_to_you,
            'category': category
        })
        total_amount += total_cost
    
    return {
        'count': len(unlinked),
        'total_amount': round(total_amount, 2),
        'transactions': unlinked
    }

def get_monthly_metrics(session_id, user_id=1):
    """
    Main function - returns all metrics for a session
    """
    print(f"\n📊 Calculating metrics for session: {session_id}")
    
    net_consumption = calculate_net_consumption(session_id, user_id)
    cash_outflow = calculate_cash_outflow(session_id, user_id)
    monthly_float = calculate_monthly_float(session_id, user_id)
    category_breakdown = get_category_breakdown(session_id, user_id)
    transaction_stats = get_transaction_stats(session_id, user_id)
    unlinked_payer = get_unlinked_splitwise_payer(session_id, user_id)
    
    return {
        'session_id': session_id,
        'net_consumption': net_consumption,
        'cash_outflow': cash_outflow,
        'monthly_float': monthly_float,
        'category_breakdown': category_breakdown,
        'transaction_stats': transaction_stats,
        'unlinked_payer': unlinked_payer
    }


def print_report(metrics):
    """
    Print beautiful console report
    """
    session_id = metrics['session_id']
    net = metrics['net_consumption']
    outflow = metrics['cash_outflow']
    float_amount = metrics['monthly_float']
    categories = metrics['category_breakdown']
    stats = metrics['transaction_stats']
    
    print("\n" + "="*70)
    print("💰 FINANCIAL ANALYSIS REPORT".center(70))
    print("="*70)
    
    # Get session info
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT selected_month FROM upload_sessions WHERE id = %s", (session_id,))
    month = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\n📅 Period: {month}")
    print(f"🆔 Session: {session_id}")
    
    print("\n" + "─"*70)
    print("💵 NET CONSUMPTION (Your True Spending)")
    print("─"*70)
    print(f"   ₹{net['total']:,.2f}")
    print(f"\n   Breakdown:")
    print(f"   • Solo Spend:           ₹{net['breakdown']['solo_spend']:,.2f}")
    print(f"   • My Share (I Paid):    ₹{net['breakdown']['split_i_paid']:,.2f}")
    print(f"   • My Share (They Paid): ₹{net['breakdown']['split_they_paid']:,.2f}")
    
    print("\n" + "─"*70)
    print("💸 CASH OUTFLOW")
    print("─"*70)
    print(f"   ₹{outflow:,.2f}")
    print(f"   (Total money that left your bank account)")
    
    print("\n" + "─"*70)
    print("📊 MONTHLY FLOAT")
    print("─"*70)
    print(f"   ₹{float_amount:,.2f}")
    
    if abs(float_amount) < 100:
        print(f"   Perfectly balanced!")
    elif float_amount > 0:
        print(f"   You paid ₹{float_amount:,.2f} extra this month")
        print(f"   (Friends will settle later)")
    else:
        print(f"   Friends paid ₹{abs(float_amount):,.2f} extra this month")
        print(f"   (You may owe them)")
    
    print("\n" + "─"*70)
    print("📈 SPENDING BY CATEGORY")
    print("─"*70)
    
    if categories:
        for cat in categories[:10]:  # Top 10
            bar_length = int(cat['percentage'] / 2)
            bar = "█" * bar_length
            print(f"   {cat['category']:20} ₹{cat['amount']:>10,.2f} ({cat['percentage']:>5.1f}%) {bar}")
    else:
        print("   No categorized transactions")
    
    print("\n" + "─"*70)
    print("📊 TRANSACTION SUMMARY")
    print("─"*70)
    print(f"   Total processed:  {stats['total_transactions']}")
    print(f"   Linked pairs:     {stats['status_breakdown'].get('LINKED', 0)}")
    print(f"   Settlements:      {stats['status_breakdown'].get('TRANSFER', 0)}")
    
    if stats['largest_expense']:
        print(f"\n   💰 Largest expense:")
        print(f"      ₹{stats['largest_expense']['amount']:,.2f} - {stats['largest_expense']['description'][:40]}")
        print(f"      ({stats['largest_expense']['category']})")

    unlinked_payer = metrics['unlinked_payer']
    
    if unlinked_payer['count'] > 0:
        print("\n" + "─"*70)
        print("⚠️  POTENTIAL DOUBLE-COUNTING WARNING")
        print("─"*70)
        print(f"   You have {unlinked_payer['count']} unlinked split expense(s)")
        print(f"   Total: ₹{unlinked_payer['total_amount']:,.2f}")
        print()
        print("   These might already be counted in solo expenses above.")
        print("   Review them to verify:")
        print()
        
        for txn in unlinked_payer['transactions'][:5]:
            owed = txn['owed_to_you']
            your_share = txn['your_share']
            
            print(f"   • {txn['date']} | ₹{txn['total_bill']:,.2f} - {txn['description'][:40]}")
            print(f"     Your share: ₹{your_share:,.2f} | Friends owe: ₹{owed:,.2f}")
        
        if unlinked_payer['count'] > 5:
            print(f"\n   ... and {unlinked_payer['count'] - 5} more")
    
    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.services.analytics <session_id>")
        print("\nExample: python -m app.services.analytics session_abc123def456")
        sys.exit(1)
    
    session_id = sys.argv[1]
    
    try:
        metrics = get_monthly_metrics(session_id)
        print_report(metrics)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)