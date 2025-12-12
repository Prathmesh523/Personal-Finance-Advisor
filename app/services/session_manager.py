import uuid
from datetime import datetime, timedelta
from app.database.connection import get_db_connection

def create_upload_session(user_id, selected_month, selected_year):
    """
    Create new upload session
    Returns: session_id, start_date, end_date
    """
    # Generate session ID
    session_id = f"session_{uuid.uuid4().hex[:12]}"
    
    # Calculate month boundaries
    start_date = f"{selected_year}-{selected_month:02d}-01"
    
    # Calculate last day of month
    if selected_month == 12:
        end_date = f"{selected_year}-12-31"
    else:
        next_month = datetime(selected_year, selected_month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        end_date = f"{selected_year}-{selected_month:02d}-{last_day}"
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO upload_sessions 
        (id, user_id, selected_month, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, %s, 'processing')
    """, (session_id, user_id, f"{selected_year}-{selected_month:02d}", start_date, end_date))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'session_id': session_id,
        'start_date': start_date,
        'end_date': end_date
    }


def update_session_counts(session_id, bank_count, splitwise_count, excluded_count):
    """Update transaction counts for session"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE upload_sessions
        SET bank_count = %s,
            splitwise_count = %s,
            excluded_count = %s
        WHERE id = %s
    """, (bank_count, splitwise_count, excluded_count, session_id))
    
    conn.commit()
    cur.close()
    conn.close()


def mark_session_complete(session_id):
    """Mark session as completed"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE upload_sessions
        SET status = 'completed'
        WHERE id = %s
    """, (session_id,))
    
    conn.commit()
    cur.close()
    conn.close()


def check_duplicate_session(user_id, selected_month):
    """Check if month already analyzed"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, created_at, bank_count, splitwise_count
        FROM upload_sessions
        WHERE user_id = %s AND selected_month = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (user_id, selected_month))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result:
        return {
            'exists': True,
            'session_id': result[0],
            'created_at': result[1],
            'transaction_count': result[2] + result[3]
        }
    
    return {'exists': False}