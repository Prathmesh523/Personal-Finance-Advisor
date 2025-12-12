from app.database.connection import get_db_connection
from datetime import date

def get_data_summary(user_id=1):
    """
    Returns the min/max dates for Bank vs Splitwise data
    to help the Frontend pick a default date range.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    summary = {}
    
    # 1. Get Bank Range (The Truth Source)
    cur.execute("""
        SELECT MIN(date), MAX(date), COUNT(*) 
        FROM transactions 
        WHERE user_id = %s AND source = 'BANK'
    """, (user_id,))
    bank_min, bank_max, bank_count = cur.fetchone()
    
    summary['bank'] = {
        'start': str(bank_min) if bank_min else None,
        'end': str(bank_max) if bank_max else None,
        'count': bank_count
    }

    # 2. Get Splitwise Range
    cur.execute("""
        SELECT MIN(date), MAX(date), COUNT(*) 
        FROM transactions 
        WHERE user_id = %s AND source = 'SPLITWISE'
    """, (user_id,))
    split_min, split_max, split_count = cur.fetchone()
    
    summary['splitwise'] = {
        'start': str(split_min) if split_min else None,
        'end': str(split_max) if split_max else None,
        'count': split_count
    }
    
    # 3. Smart Suggestion Logic
    # Default: Show the Bank Statement range if available (since that defines cash flow)
    # If no bank data, show Splitwise range.
    if bank_min and bank_max:
        summary['suggested_range'] = {'start': str(bank_min), 'end': str(bank_max)}
    elif split_min:
        summary['suggested_range'] = {'start': str(split_min), 'end': str(split_max)}
    else:
        # Fallback to current month
        today = date.today()
        summary['suggested_range'] = {
            'start': date(today.year, today.month, 1).strftime('%Y-%m-%d'),
            'end': str(today)
        }

    cur.close()
    conn.close()
    return summary