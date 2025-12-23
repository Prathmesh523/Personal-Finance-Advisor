"""
Recommendations Service
Generates personalized financial recommendations
"""
from app.database.connection import get_db_connection
from app.services.analytics import get_category_breakdown
from app.services.recurring_detection import get_recurring_summary
import re

def get_category_comparison(session_id, user_id=1):
    """
    Compare current session with previous session
    Returns increases and decreases
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get current session month
    cur.execute("""
        SELECT selected_month, start_date
        FROM upload_sessions
        WHERE id = %s
    """, (session_id,))
    
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        return None, None
    
    current_month, current_start = result
    
    # Get previous session (month before)
    cur.execute("""
        SELECT id, selected_month
        FROM upload_sessions
        WHERE user_id = %s
          AND selected_month < %s
          AND status = 'completed'
        ORDER BY selected_month DESC
        LIMIT 1
    """, (user_id, current_month))
    
    prev_result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not prev_result:
        return None, None  # No previous month to compare
    
    prev_session_id = prev_result[0]
    
    # Get category breakdowns
    current_categories = get_category_breakdown(session_id, user_id)
    prev_categories = get_category_breakdown(prev_session_id, user_id)
    
    # Convert to dict for easier lookup
    current_dict = {cat['category']: cat['amount'] for cat in current_categories}
    prev_dict = {cat['category']: cat['amount'] for cat in prev_categories}
    
    increases = []
    decreases = []
    
    # Compare each category
    all_categories = set(current_dict.keys()) | set(prev_dict.keys())
    
    for category in all_categories:
        current_amt = current_dict.get(category, 0)
        prev_amt = prev_dict.get(category, 0)
        
        if prev_amt == 0:
            continue  # Skip new categories
        
        change_amt = current_amt - prev_amt
        change_pct = (change_amt / prev_amt) * 100
        
        if change_pct >= 10:  # Increase threshold
            reason = detect_increase_reason(session_id, category, user_id)
            recommendation = generate_recommendation(category, change_pct)
            
            increases.append({
                'category': category,
                'current': round(current_amt, 2),
                'previous': round(prev_amt, 2),
                'change_amount': round(change_amt, 2),
                'change_percentage': round(change_pct, 1),
                'reason': reason,
                'recommendation': recommendation
            })
        
        elif change_pct <= -10:  # Decrease threshold
            decreases.append({
                'category': category,
                'current': round(current_amt, 2),
                'previous': round(prev_amt, 2),
                'change_amount': round(abs(change_amt), 2),
                'change_percentage': round(abs(change_pct), 1),
                'saved': round(abs(change_amt), 2)
            })
    
    # Sort by percentage change
    increases.sort(key=lambda x: x['change_percentage'], reverse=True)
    decreases.sort(key=lambda x: x['change_percentage'], reverse=True)
    
    return increases[:3], decreases[:3]


def detect_increase_reason(session_id, category, user_id=1):
    """
    Detect reason for spending increase
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get transactions for this category
    cur.execute("""
        SELECT description, amount
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND category = %s
          AND amount < 0
        ORDER BY amount
    """, (session_id, user_id, category))
    
    txns = cur.fetchall()
    cur.close()
    conn.close()
    
    if not txns:
        return f"{len(txns)} transactions"
    
    # Find dominant merchant
    merchant_counts = {}
    for description, amount in txns:
        merchant = extract_merchant_pattern(description)
        if merchant:
            merchant_counts[merchant] = merchant_counts.get(merchant, 0) + 1
    
    if merchant_counts:
        top_merchant = max(merchant_counts, key=merchant_counts.get)
        count = merchant_counts[top_merchant]
        
        if count >= 5:
            return f"{count} {top_merchant} orders"
    
    # Fallback
    if len(txns) <= 3:
        return f"{len(txns)} large purchases"
    else:
        return f"{len(txns)} transactions"


def extract_merchant_pattern(description):
    """Extract merchant name"""
    if not description:
        return None
    
    cleaned = description
    prefixes = ['UPI-', 'POS-', 'IMPS-', 'NEFT-']
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
    cleaned = re.sub(r'[-\d]+$', '', cleaned)
    parts = re.split(r'[-.]', cleaned)
    
    if parts:
        merchant = parts[0].strip()
        if len(merchant) > 2:
            return merchant.title()
    
    return None


def generate_recommendation(category, change_pct):
    """Generate actionable recommendation"""
    
    recommendations = {
        'Food & Dining': "Cook 3 more meals/week to save ₹3,000/month",
        'Groceries': "Plan weekly meals to reduce waste",
        'Shopping': "Set monthly budget of ₹5,000",
        'Transport': "Consider metro pass for ₹1,200/month",
        'Entertainment': "Limit to 2 outings/month",
        'Bills & Utilities': "Review subscriptions and optimize",
        'Health': "Check for unnecessary medical expenses",
    }
    
    return recommendations.get(category, "Set a monthly budget to control spending")


def get_all_recommendations(session_id, user_id=1):
    """
    Get all recommendations for a session
    """
    # 1. Recurring expenses
    recurring = get_recurring_summary(user_id)
    
    # 2. Category comparison
    increases, decreases = get_category_comparison(session_id, user_id)
    
    return {
        'recurring': recurring,
        'high_spending': increases or [],
        'savings': decreases or []
    }