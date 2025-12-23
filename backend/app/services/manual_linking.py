"""
Manual Linking Service
Helps users link unmatched Splitwise PAYER transactions to bank transactions
"""
from app.database.connection import get_db_connection
from difflib import SequenceMatcher

def calculate_text_similarity(text1, text2):
    """Calculate similarity between two strings (0-1)"""
    if not text1 or not text2:
        return 0.0
    
    # Clean texts
    t1 = text1.lower().strip()
    t2 = text2.lower().strip()
    
    # Remove common noise words
    noise_words = ['upi', 'pos', 'txn', 'imps', 'neft', 'limited', 'private', 'ltd']
    for noise in noise_words:
        t1 = t1.replace(noise, '')
        t2 = t2.replace(noise, '')
    
    # Token overlap
    tokens1 = set(t1.split())
    tokens2 = set(t2.split())
    common = tokens1.intersection(tokens2)
    
    if len(common) > 0:
        return 0.7 + (0.1 * min(len(common), 3))  # Max 1.0
    
    # Sequence matching
    return SequenceMatcher(None, t1, t2).ratio()


def calculate_match_score(splitwise_txn, bank_txn):
    """
    Calculate match score between splitwise and bank transaction
    Returns: (score, reasons)
    """
    score = 0.0
    reasons = []
    
    # 1. Amount match (40% weight)
    bank_amount = abs(bank_txn['amount'])
    split_amount = splitwise_txn['total_cost']
    amount_diff = abs(bank_amount - split_amount)
    amount_diff_pct = amount_diff / split_amount if split_amount > 0 else 1.0
    
    if amount_diff < 1:  # Exact match
        score += 0.40
        reasons.append("exact amount")
    elif amount_diff_pct < 0.05:  # Within 5%
        score += 0.35
        reasons.append("very close amount")
    elif amount_diff_pct < 0.15:  # Within 15%
        score += 0.20
        reasons.append("similar amount")
    
    # 2. Date match (30% weight)
    from datetime import datetime
    split_date = datetime.fromisoformat(splitwise_txn['date']) if isinstance(splitwise_txn['date'], str) else splitwise_txn['date']
    bank_date = datetime.fromisoformat(bank_txn['date']) if isinstance(bank_txn['date'], str) else bank_txn['date']
    date_diff = abs((bank_date - split_date).days)
    
    if date_diff == 0:
        score += 0.30
        reasons.append("same day")
    elif date_diff == 1:
        score += 0.25
        reasons.append("1 day apart")
    elif date_diff <= 3:
        score += 0.15
        reasons.append(f"{date_diff} days apart")
    elif date_diff <= 5:
        score += 0.10
        reasons.append(f"{date_diff} days apart")
    
    # 3. Description similarity (30% weight)
    text_score = calculate_text_similarity(
        bank_txn['description'],
        splitwise_txn['description']
    )
    score += text_score * 0.30
    
    if text_score > 0.7:
        reasons.append("strong name match")
    elif text_score > 0.4:
        reasons.append("partial name match")
    
    return round(score, 2), ", ".join(reasons)


def find_potential_matches(splitwise_txn, session_id, user_id=1):
    """
    Find potential bank matches for a splitwise transaction
    Returns top 3 candidates with scores
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    split_amount = splitwise_txn['total_cost']
    split_date = splitwise_txn['date']
    
    # Search criteria: ±5 days, ±15% amount, unlinked only
    amount_min = split_amount * 0.85
    amount_max = split_amount * 1.15
    
    cur.execute("""
        SELECT 
            id, date, description, amount, category
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND status = 'UNLINKED'
          AND amount < 0
          AND ABS(amount) BETWEEN %s AND %s
          AND date >= (%s::date - INTERVAL '5 days')
          AND date <= (%s::date + INTERVAL '5 days')
        ORDER BY date DESC
        LIMIT 10
    """, (session_id, user_id, amount_min, amount_max, split_date, split_date))
    
    candidates = []
    for row in cur.fetchall():
        bank_txn = {
            'id': row[0],
            'date': row[1],
            'description': row[2],
            'amount': float(row[3]),
            'category': row[4]
        }
        
        # Calculate match score
        score, reason = calculate_match_score(splitwise_txn, bank_txn)
        
        candidates.append({
            'id': bank_txn['id'],
            'date': bank_txn['date'].isoformat(),
            'description': bank_txn['description'],
            'amount': bank_txn['amount'],
            'category': bank_txn['category'],
            'match_score': score,
            'match_reason': reason
        })
    
    cur.close()
    conn.close()
    
    # Sort by score and return top 3
    candidates.sort(key=lambda x: x['match_score'], reverse=True)
    return candidates[:3]


def get_unmatched_splitwise(session_id, user_id=1):
    """
    Get all unmatched splitwise PAYER transactions with suggested matches
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get unmatched splitwise PAYER transactions
    cur.execute("""
        SELECT 
            id, date, description, total_cost, my_share, category
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND role = 'PAYER'
          AND status = 'UNLINKED'
        ORDER BY date DESC
    """, (session_id, user_id))
    
    unmatched = []
    for row in cur.fetchall():
        split_txn = {
            'id': row[0],
            'date': row[1],
            'description': row[2],
            'total_cost': float(row[3]),
            'my_share': float(row[4]),
            'category': row[5]
        }
        
        # Find potential matches
        suggested_matches = find_potential_matches(split_txn, session_id, user_id)
        
        # Determine if we should pre-select
        preselect_id = None
        if suggested_matches and suggested_matches[0]['match_score'] >= 0.85:
            preselect_id = suggested_matches[0]['id']
        
        unmatched.append({
            'id': split_txn['id'],
            'date': split_txn['date'].isoformat(),
            'description': split_txn['description'],
            'total_cost': split_txn['total_cost'],
            'my_share': split_txn['my_share'],
            'category': split_txn['category'],
            'suggested_matches': suggested_matches,
            'preselect_id': preselect_id
        })
    
    cur.close()
    conn.close()
    
    return unmatched


def link_transactions_manual(splitwise_id, bank_id, session_id, user_id=1):
    """
    Manually link a splitwise transaction to a bank transaction
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify both transactions exist and are unlinked
    cur.execute("""
        SELECT status FROM splitwise_transactions 
        WHERE id = %s AND upload_session_id = %s AND user_id = %s
    """, (splitwise_id, session_id, user_id))
    
    split_result = cur.fetchone()
    if not split_result:
        cur.close()
        conn.close()
        raise ValueError("Splitwise transaction not found")
    
    if split_result[0] != 'UNLINKED':
        cur.close()
        conn.close()
        raise ValueError("Splitwise transaction already linked")
    
    cur.execute("""
        SELECT status FROM bank_transactions 
        WHERE id = %s AND upload_session_id = %s AND user_id = %s
    """, (bank_id, session_id, user_id))
    
    bank_result = cur.fetchone()
    if not bank_result:
        cur.close()
        conn.close()
        raise ValueError("Bank transaction not found")
    
    if bank_result[0] != 'UNLINKED':
        cur.close()
        conn.close()
        raise ValueError("Bank transaction already linked")
    
    # Update splitwise transaction
    cur.execute("""
        UPDATE splitwise_transactions
        SET status = 'LINKED',
            linked_bank_id = %s,
            match_confidence = 1.0,
            match_method = 'manual'
        WHERE id = %s
    """, (bank_id, splitwise_id))
    
    # Update bank transaction
    cur.execute("""
        UPDATE bank_transactions
        SET status = 'LINKED',
            linked_splitwise_id = %s,
            match_confidence = 1.0,
            match_method = 'manual',
            category = (SELECT category FROM splitwise_transactions WHERE id = %s)
        WHERE id = %s
    """, (splitwise_id, splitwise_id, bank_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return True


def skip_transaction(splitwise_id, reason, session_id, user_id=1):
    """
    Mark splitwise transaction as skipped (user confirmed no bank match exists)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Verify transaction exists
    cur.execute("""
        SELECT status FROM splitwise_transactions 
        WHERE id = %s AND upload_session_id = %s AND user_id = %s
    """, (splitwise_id, session_id, user_id))
    
    result = cur.fetchone()
    if not result:
        cur.close()
        conn.close()
        raise ValueError("Splitwise transaction not found")
    
    # Update status to SKIPPED
    cur.execute("""
        UPDATE splitwise_transactions
        SET status = 'SKIPPED',
            match_method = %s
        WHERE id = %s
    """, (f'manual_skip:{reason}', splitwise_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return True