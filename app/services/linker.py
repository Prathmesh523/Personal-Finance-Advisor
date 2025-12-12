from app.database.connection import get_db_connection
from difflib import SequenceMatcher

def calculate_similarity(bank_desc, split_desc):
    b_clean = bank_desc.lower()
    for noise in ['upi', 'pos', 'txn', 'imps', 'neft', 'limited', 'private', 'ltd', 'pay for intent']:
        b_clean = b_clean.replace(noise, '')
    
    s_clean = split_desc.lower()
    b_tokens = set(b_clean.split())
    s_tokens = set(s_clean.split())
    
    common = b_tokens.intersection(s_tokens)
    if len(common) > 0:
        return 0.85 + (0.05 * len(common)) 
        
    return SequenceMatcher(None, b_clean, s_clean).ratio()

def pick_best_candidate(s_desc, candidates, threshold=0.0):
    best_id = None
    highest_score = -1.0
    
    for c in candidates:
        # Correctly unpacks 3 values now
        c_id, c_date, c_desc = c 
        score = calculate_similarity(c_desc, s_desc)
        
        if score > highest_score:
            highest_score = score
            best_id = c_id
            
    if highest_score >= threshold:
        return best_id
    return None

def link_transactions(cur, split_id, bank_id, method):
    cur.execute("UPDATE transactions SET status='LINKED', link_id=%s WHERE id=%s", (bank_id, split_id))
    cur.execute("UPDATE transactions SET status='LINKED', link_id=%s WHERE id=%s", (split_id, bank_id))
    print(f"   🔗 LINKED! Split {split_id} <-> Bank {bank_id} [{method}]")

def run_linker(user_id=1, session_id=None):  # NEW parameter
    """Add WHERE upload_session_id = session_id to all queries"""
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("🔄 Starting System Linker...")
    
    # Modified query with session filter
    cur.execute("""
        SELECT id, date, meta_total_bill, description
        FROM transactions 
        WHERE user_id = %s 
          AND source = 'SPLITWISE' 
          AND role = 'PAYER'
          AND status = 'UNLINKED'
          AND upload_session_id = %s
        ORDER BY date
    """, (user_id, session_id))  # NEW
    
    splitwise_txns = cur.fetchall()
    print(f"🔍 Found {len(splitwise_txns)} Splitwise entries to process.")
    
    links_made = 0
    
    # --- PASS 1: EXACT MATCH ---
    print("\n🚀 Pass 1: Exact Match (Same Day, Same Amount)")
    
    unmatched_after_pass1 = []
    
    for s_txn in splitwise_txns:
        s_id, s_date, s_total, s_desc = s_txn
        target_amount = float(s_total)
        
        # FIX: Select 'date' so tuple unpacking works
        cur.execute("""
            SELECT id, date, description FROM transactions 
            WHERE user_id = %s AND source = 'BANK' AND status = 'UNLINKED'
            AND ABS(ABS(amount) - %s) < 1.00
            AND date = %s
        """, (user_id, target_amount, s_date))
        
        candidates = cur.fetchall()
        
        if len(candidates) == 1:
            b_id, b_date, b_desc = candidates[0]
            link_transactions(cur, s_id, b_id, "Pass 1: Perfect")
            links_made += 1
            conn.commit() 
        elif len(candidates) > 1:
            best_id = pick_best_candidate(s_desc, candidates)
            if best_id:
                link_transactions(cur, s_id, best_id, "Pass 1: Tie-Break")
                links_made += 1
                conn.commit()
            else:
                unmatched_after_pass1.append(s_txn)
        else:
            unmatched_after_pass1.append(s_txn)

    # --- PASS 2: FUZZY DATE ---
    print("\n🚀 Pass 2: Fuzzy Date (±2 Days) + Description Match")
    
    unmatched_after_pass2 = []

    for s_txn in unmatched_after_pass1:
        s_id, s_date, s_total, s_desc = s_txn
        target_amount = float(s_total)
        
        # FIX: Added s_date TWICE to arguments
        cur.execute("""
            SELECT id, date, description FROM transactions 
            WHERE user_id = %s AND source = 'BANK' AND status = 'UNLINKED'
            AND ABS(ABS(amount) - %s) < 1.00
            AND date >= (%s::date - INTERVAL '2 days')
            AND date <= (%s::date + INTERVAL '2 days')
        """, (user_id, target_amount, s_date, s_date)) 
        
        candidates = cur.fetchall()
        
        best_id = pick_best_candidate(s_desc, candidates, threshold=0.3)
        
        if best_id:
            link_transactions(cur, s_id, best_id, "Pass 2: Fuzzy Date")
            links_made += 1
            conn.commit()
        else:
            unmatched_after_pass2.append(s_txn)

    # --- PASS 3: BLIND TRUST ---
    print("\n🚀 Pass 3: Blind Match (Strict Amount, Tight Date, Ignore Name)")
    
    for s_txn in unmatched_after_pass2:
        s_id, s_date, s_total, s_desc = s_txn
        target_amount = float(s_total)
        
        # FIX: Added s_date TWICE to arguments
        cur.execute("""
            SELECT id, date, description FROM transactions 
            WHERE user_id = %s AND source = 'BANK' AND status = 'UNLINKED'
            AND ABS(ABS(amount) - %s) < 1.00
            AND date >= (%s::date - INTERVAL '1 day')
            AND date <= (%s::date + INTERVAL '1 day')
        """, (user_id, target_amount, s_date, s_date))
        
        candidates = cur.fetchall()
        
        if len(candidates) == 1:
            b_id, b_date, b_desc = candidates[0]
            score = calculate_similarity(s_desc, b_desc)
            if score > 0.15:
                link_transactions(cur, s_id, b_id, "Pass 3: Blind Trust")
                links_made += 1
                conn.commit()

    print(f"\n✅ Linker finished. Total Linked: {links_made}")
    cur.close()
    conn.close()

def run_full_pipeline(session_id, user_id=1):  # NEW parameter
    """
    Complete pipeline for specific upload session
    """
    from app.services.categorization import detect_settlements, detect_other_transfers
    
    print("=" * 60)
    print("🚀 RUNNING FULL FINANCIAL ANALYSIS PIPELINE")
    print(f"   Session: {session_id}")
    print("=" * 60)
    
    # Pass session_id to all functions
    settlements = detect_settlements(user_id, session_id)
    run_linker(user_id, session_id)
    other_transfers = detect_other_transfers(user_id, session_id)
    
    # Mark session complete
    from app.services.session_manager import mark_session_complete
    mark_session_complete(session_id)
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_full_pipeline()