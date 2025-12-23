"""
Recurring Expense Detection
Detects subscription and recurring payment patterns
"""
from app.database.connection import get_db_connection
from collections import defaultdict
from datetime import datetime, timedelta
import re

def extract_merchant_pattern(description):
    """Extract merchant name from transaction description"""
    if not description:
        return None
    
    # Remove common prefixes
    cleaned = description
    prefixes = ['UPI-', 'POS-', 'IMPS-', 'NEFT-', 'ATM-', 'RTGS-']
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
    # Remove numbers and special chars at the end
    cleaned = re.sub(r'[-\d]+$', '', cleaned)
    
    # Take first meaningful word
    parts = re.split(r'[-.]', cleaned)
    if parts:
        merchant = parts[0].strip()
        if len(merchant) > 2:
            return merchant.upper()
    
    return None


def detect_recurring_expenses(user_id=1):
    """
    Detect recurring expenses across ALL sessions for a user
    Returns list of recurring subscriptions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all bank transactions (last 6 months for better detection)
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    cur.execute("""
        SELECT 
            id, date, description, amount, category
        FROM bank_transactions
        WHERE user_id = %s
          AND amount < 0
          AND status != 'TRANSFER'
          AND date >= %s
        ORDER BY description, date
    """, (user_id, six_months_ago))
    
    all_txns = cur.fetchall()
    cur.close()
    conn.close()
    
    # Group by merchant pattern
    merchant_groups = defaultdict(list)
    for txn_id, date, description, amount, category in all_txns:
        merchant = extract_merchant_pattern(description)
        if merchant:
            merchant_groups[merchant].append({
                'id': txn_id,
                'date': date,
                'amount': abs(float(amount)),
                'description': description,
                'category': category
            })
    
    # Detect recurring patterns
    recurring = []
    
    for merchant, txns in merchant_groups.items():
        if len(txns) < 3:  # Need at least 3 transactions
            continue
        
        # Sort by date
        txns.sort(key=lambda x: x['date'])
        
        # Calculate intervals between transactions
        intervals = []
        for i in range(1, len(txns)):
            days = (txns[i]['date'] - txns[i-1]['date']).days
            intervals.append(days)
        
        if not intervals:
            continue
        
        # Check if intervals are consistent (monthly = 28-32 days)
        avg_interval = sum(intervals) / len(intervals)
        
        # Check amount consistency (±10% variation)
        amounts = [t['amount'] for t in txns]
        avg_amount = sum(amounts) / len(amounts)
        amount_variance = max(amounts) - min(amounts)
        amount_variance_pct = (amount_variance / avg_amount) * 100 if avg_amount > 0 else 100
        
        # Determine if recurring
        is_monthly = 25 <= avg_interval <= 35
        is_consistent_amount = amount_variance_pct <= 15
        
        if is_monthly and is_consistent_amount:
            recurring.append({
                'merchant': merchant,
                'frequency': 'monthly',
                'interval_days': round(avg_interval),
                'average_amount': round(avg_amount, 2),
                'transaction_count': len(txns),
                'total_spent': sum(amounts),
                'first_date': txns[0]['date'].isoformat(),
                'last_date': txns[-1]['date'].isoformat(),
                'category': txns[0]['category'] or 'Other'
            })
    
    # Sort by average amount (highest first)
    recurring.sort(key=lambda x: x['average_amount'], reverse=True)
    
    return recurring


def get_recurring_summary(user_id=1):
    """
    Get summary of recurring expenses
    """
    recurring = detect_recurring_expenses(user_id)
    
    total_monthly = sum(r['average_amount'] for r in recurring)
    total_annual = total_monthly * 12
    
    return {
        'count': len(recurring),
        'monthly_total': round(total_monthly, 2),
        'annual_total': round(total_annual, 2),
        'subscriptions': recurring[:10]  # Top 10
    }