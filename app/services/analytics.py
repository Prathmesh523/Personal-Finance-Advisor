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
    Calculate TRUE spending (what you actually consumed)
    
    Formula:
    = Solo expenses (unlinked bank transactions)
      + Your share of splits (where you paid)
      + Your share of splits (where friend paid)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Solo expenses (bank transactions not linked to Splitwise)
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'BANK'
          AND amount < 0
          AND status = 'UNLINKED'
          AND category NOT IN ('Settlement', 'Investment', 'Credit Card', 'Savings', 'Self Transfer')
    """, (session_id, user_id))
    
    solo_expenses = float(cur.fetchone()[0])
    
    # 2. Your share of splits where YOU paid the bill
    cur.execute("""
        SELECT COALESCE(SUM(meta_total_bill - ABS(amount)), 0)
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
          AND role = 'PAYER'
          AND status = 'LINKED'
    """, (session_id, user_id))
    
    split_you_paid = float(cur.fetchone()[0])
    
    # 3. Your share of splits where FRIEND paid the bill
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
          AND role = 'BORROWER'
    """, (session_id, user_id))
    
    split_friend_paid = float(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
    total = solo_expenses + split_you_paid + split_friend_paid
    
    return {
        'total': round(total, 2),
        'breakdown': {
            'solo': round(solo_expenses, 2),
            'split_you_paid': round(split_you_paid, 2),
            'split_friend_paid': round(split_friend_paid, 2)
        }
    }


def calculate_cash_outflow(session_id, user_id=1):
    """
    Calculate total money that left your bank account
    
    Includes:
    - Solo expenses
    - Split expenses (where you paid)
    - Settlements (paying back debts)
    
    Excludes:
    - Investments (Zerodha, Groww, etc.)
    - Credit card payments (just moving debt)
    - Savings transfers (money didn't leave, just moved)
    - Self transfers (between your own accounts)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'BANK'
          AND amount < 0
    """, (session_id, user_id))
    
    total = float(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
    return round(total, 2)


def calculate_monthly_float(session_id, user_id=1):
    """
    Calculate money you paid extra this month (that friends will settle later)
    
    Formula:
    = Sum of positive net balances in Splitwise
    
    Note: This is NOT total debt, just this month's float
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COALESCE(SUM(ABS(amount)), 0)
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
          AND role = 'PAYER'
          AND status = 'LINKED'
          AND meta_total_bill > ABS(amount)
    """, (session_id, user_id))
    
    total = float(cur.fetchone()[0])
    
    cur.close()
    conn.close()
    
    return round(total, 2)

def get_category_breakdown(session_id, user_id=1):
    """
    Get spending breakdown by category
    Shows only CONSUMPTION (what you spent), not all transactions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    category_totals = {}
    
    # 1. Solo expenses (unlinked bank) - use bank category
    cur.execute("""
        SELECT 
            category,
            SUM(ABS(amount)) as total_amount
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'BANK'
          AND amount < 0  -- ✅ ONLY EXPENSES (negative)
          AND status = 'UNLINKED'
          AND category NOT IN ('Settlement', 'Investment', 'Credit Card', 'Savings', 'Self Transfer')
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        category = row[0] or 'Other'
        category_totals[category] = category_totals.get(category, 0) + float(row[1])
    
    # 2. Split expenses (you paid) - use Splitwise category with YOUR SHARE
    cur.execute("""
        SELECT 
            category,
            SUM(meta_total_bill - ABS(amount)) as your_share
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
          AND role = 'PAYER'
          AND status = 'LINKED'
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        category = row[0] or 'Other'
        your_share = float(row[1])
        category_totals[category] = category_totals.get(category, 0) + your_share
    
    # 3. Split expenses (friend paid) - use Splitwise category
    cur.execute("""
        SELECT 
            category,
            SUM(ABS(amount)) as your_share
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
          AND role = 'BORROWER'
        GROUP BY category
    """, (session_id, user_id))
    
    for row in cur.fetchall():
        category = row[0] or 'Other'
        category = CATEGORY_MAPPING.get(category, category)
        category_totals[category] = category_totals.get(category, 0) + float(row[1])
    
    cur.close()
    conn.close()
    
    # Calculate total for percentages
    total_spending = sum(category_totals.values())
    
    if total_spending == 0:
        return []
    
    # Convert to list and sort
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
    
    # Total transactions
    cur.execute("""
        SELECT COUNT(*) FROM transactions
        WHERE upload_session_id = %s AND user_id = %s
    """, (session_id, user_id))
    total_count = cur.fetchone()[0]
    
    # Status breakdown
    cur.execute("""
        SELECT status, COUNT(*) 
        FROM transactions
        WHERE upload_session_id = %s AND user_id = %s
        GROUP BY status
    """, (session_id, user_id))
    status_breakdown = {row[0]: row[1] for row in cur.fetchall()}
    
    # Source breakdown
    cur.execute("""
        SELECT source, COUNT(*) 
        FROM transactions
        WHERE upload_session_id = %s AND user_id = %s
        GROUP BY source
    """, (session_id, user_id))
    source_breakdown = {row[0]: row[1] for row in cur.fetchall()}
    
    # Average transaction
    cur.execute("""
        SELECT AVG(ABS(amount))
        FROM transactions
        WHERE upload_session_id = %s 
          AND user_id = %s
          AND status != 'TRANSFER'
    """, (session_id, user_id))
    avg_transaction = float(cur.fetchone()[0] or 0)
    
    # Largest expense
    cur.execute("""
        SELECT description, ABS(amount), category
        FROM transactions
        WHERE upload_session_id = %s 
          AND user_id = %s
          AND status != 'TRANSFER'
          AND amount<0 
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
            meta_total_bill as total_bill,
            ABS(amount) as amount_owed_to_you,
            category
        FROM transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'SPLITWISE'
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
        date, desc, total_bill, owed, category = row
        unlinked.append({
            'date': date,
            'description': desc,
            'total_bill': float(total_bill) if total_bill else 0,
            'owed_to_you': float(owed),
            'category': category
        })
        total_amount += float(total_bill) if total_bill else 0
    
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
    unlinked_payer = get_unlinked_splitwise_payer(session_id, user_id)  # NEW
    
    return {
        'session_id': session_id,
        'net_consumption': net_consumption,
        'cash_outflow': cash_outflow,
        'monthly_float': monthly_float,
        'category_breakdown': category_breakdown,
        'transaction_stats': transaction_stats,
        'unlinked_payer': unlinked_payer  # NEW
    }


def print_report(metrics):
    """
    Print beautiful console report
    """
    session_id = metrics['session_id']
    net = metrics['net_consumption']
    outflow = metrics['cash_outflow']
    float_amount = metrics['monthly_float']  # ✅ This is correct
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
    print("💵 YOUR TRUE SPENDING")
    print("─"*70)
    print(f"   ₹{net['total']:,.2f}")
    print(f"\n   Breakdown:")
    print(f"   • Solo expenses:         ₹{net['breakdown']['solo']:,.2f}")
    print(f"   • Your share (you paid): ₹{net['breakdown']['split_you_paid']:,.2f}")
    print(f"   • Your share (friend paid): ₹{net['breakdown']['split_friend_paid']:,.2f}")
    
    print("\n" + "─"*70)
    print("💸 CASH OUTFLOW")
    print("─"*70)
    print(f"   ₹{outflow:,.2f}")
    print(f"   (Total money that left your bank account)")
    
    print("\n" + "─"*70)
    print("📊 THE DIFFERENCE")
    print("─"*70)

    difference = outflow - net['total']

    if difference > 0:
        print(f"   ₹{difference:,.2f}")
        print(f"   You paid this extra for friends this month")
        print(f"   (They'll settle via Splitwise)")
        if float_amount > 0:
            print(f"\n   💡 Monthly float: ₹{float_amount:,.2f}")
    elif difference < 0:
        print(f"   ₹{abs(difference):,.2f}")
        print(f"   Friends paid this much for you this month")
        print(f"   (You owe them - check Splitwise)")
        
        # Show breakdown if there's complexity
        if float_amount > 0:
            you_owe = abs(difference) + float_amount
            print(f"\n   📊 Breakdown:")
            print(f"   • Friends owe you: ₹{float_amount:,.2f}")
            print(f"   • You owe friends: ₹{you_owe:,.2f}")
            print(f"   • Net: You owe ₹{abs(difference):,.2f}")
    else:
        print(f"   ₹0.00")
        print(f"   Perfectly balanced!")
    
    print("\n" + "─"*70)
    print("📈 SPENDING BY CATEGORY")
    print("─"*70)
    
    if categories:
        for cat in categories[:10]:  # Top 10
            bar_length = int(cat['percentage'] / 2)  # Scale for display
            bar = "█" * bar_length
            print(f"   {cat['category']:20} ₹{cat['amount']:>10,.2f} ({cat['percentage']:>5.1f}%) {bar}")
    else:
        print("   No categorized transactions")
    
    print("\n" + "─"*70)
    print("📊 TRANSACTION SUMMARY")
    print("─"*70)
    print(f"   Total processed:  {stats['total_transactions']}")
    print(f"   Linked pairs:     {stats['status_breakdown'].get('LINKED', 0) // 2}")
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
        
        for txn in unlinked_payer['transactions'][:5]:  # Show max 5
            owed = txn['owed_to_you']
            total = txn['total_bill']
            your_share = total - owed if total > owed else 0
            
            print(f"   • {txn['date']} | ₹{total:,.2f} - {txn['description'][:40]}")
            print(f"     Your share: ₹{your_share:,.2f} | Friends owe: ₹{owed:,.2f}")
        
        if unlinked_payer['count'] > 5:
            print(f"\n   ... and {unlinked_payer['count'] - 5} more")
        
        print("\n   💡 Tip: These are counted in 'Solo expenses' above.")
        print("      If they match bank transactions, no issue.")
        print("      If not, your true spending might be higher.")
    
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