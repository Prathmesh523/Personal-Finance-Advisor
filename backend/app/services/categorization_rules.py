"""
User Categorization Rules Service
Allows users to create and apply custom categorization rules
"""
from app.database.connection import get_db_connection
import re

def extract_merchant_pattern(description):
    """
    Extract meaningful merchant name from transaction description
    
    Examples:
    - "UPI-SWIGGY-MUMBAI-123" → "SWIGGY"
    - "NETFLIX.COM" → "NETFLIX"
    - "UPI-Prathamesh Patil" → "Prathamesh Patil"
    """
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
    
    # Take first meaningful word/phrase (before hyphen or dot)
    parts = re.split(r'[-.]', cleaned)
    if parts:
        merchant = parts[0].strip()
        
        # If it's all caps and > 3 chars, it's likely a merchant
        if len(merchant) > 2:
            return merchant.upper()
    
    return None


def count_similar_transactions(session_id, source, pattern, current_txn_id, user_id=1):
    """
    Count how many transactions match the pattern (excluding current)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    if source == 'BANK':
        cur.execute("""
            SELECT COUNT(*)
            FROM bank_transactions
            WHERE upload_session_id = %s
              AND user_id = %s
              AND id != %s
              AND UPPER(description) LIKE %s
        """, (session_id, user_id, current_txn_id, f'%{pattern}%'))
    else:
        cur.execute("""
            SELECT COUNT(*)
            FROM splitwise_transactions
            WHERE upload_session_id = %s
              AND user_id = %s
              AND id != %s
              AND UPPER(description) LIKE %s
        """, (session_id, user_id, current_txn_id, f'%{pattern}%'))
    
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    return count


def save_categorization_rule(user_id, pattern, category, match_type='contains', source='BOTH'):
    """
    Save user categorization rule to database
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if rule already exists
    cur.execute("""
        SELECT id FROM user_categorization_rules
        WHERE user_id = %s AND pattern = %s AND source = %s
    """, (user_id, pattern, source))
    
    existing = cur.fetchone()
    
    if existing:
        # Update existing rule
        cur.execute("""
            UPDATE user_categorization_rules
            SET category = %s, match_type = %s
            WHERE id = %s
        """, (category, match_type, existing[0]))
    else:
        # Insert new rule
        cur.execute("""
            INSERT INTO user_categorization_rules
            (user_id, pattern, category, match_type, source)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, pattern, category, match_type, source))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return True


def apply_rule_to_similar(session_id, source, pattern, category, current_txn_id, user_id=1):
    """
    Apply category to all similar transactions in the session
    Returns count of updated transactions
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    if source == 'BANK':
        cur.execute("""
            UPDATE bank_transactions
            SET category = %s
            WHERE upload_session_id = %s
              AND user_id = %s
              AND id != %s
              AND UPPER(description) LIKE %s
        """, (category, session_id, user_id, current_txn_id, f'%{pattern}%'))
    else:
        cur.execute("""
            UPDATE splitwise_transactions
            SET category = %s
            WHERE upload_session_id = %s
              AND user_id = %s
              AND id != %s
              AND UPPER(description) LIKE %s
        """, (category, session_id, user_id, current_txn_id, f'%{pattern}%'))
    
    count = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    return count


def get_user_rules(user_id):
    """
    Get all categorization rules for a user
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, pattern, category, match_type, source, created_at
        FROM user_categorization_rules
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))
    
    rules = []
    for row in cur.fetchall():
        rules.append({
            'id': row[0],
            'pattern': row[1],
            'category': row[2],
            'match_type': row[3],
            'source': row[4],
            'created_at': row[5].isoformat()
        })
    
    cur.close()
    conn.close()
    
    return rules


def apply_user_rules_to_transaction(description, source, user_id=1):
    """
    Check if any user rule matches this transaction
    Returns category if matched, None otherwise
    
    Called during upload processing (in categorization.py)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get rules for this source
    cur.execute("""
        SELECT pattern, category, match_type
        FROM user_categorization_rules
        WHERE user_id = %s
          AND (source = %s OR source = 'BOTH')
        ORDER BY created_at DESC
    """, (user_id, source))
    
    rules = cur.fetchall()
    cur.close()
    conn.close()
    
    # Check each rule
    for pattern, category, match_type in rules:
        if match_type == 'contains':
            if pattern.upper() in description.upper():
                return category
        elif match_type == 'exact':
            if description.upper() == pattern.upper():
                return category
        elif match_type == 'starts_with':
            if description.upper().startswith(pattern.upper()):
                return category
    
    return None