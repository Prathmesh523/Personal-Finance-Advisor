from app.database.connection import get_db_connection
from difflib import SequenceMatcher

def detect_settlements(user_id=1, session_id=None):
    """Add WHERE upload_session_id = session_id"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n🔍 Starting Settlement Detection...")
    
    # Step 1: Find Splitwise Payment entries
    cur.execute("""
        SELECT id, date, meta_total_bill, description
        FROM transactions
        WHERE user_id = %s 
          AND source = 'SPLITWISE'
          AND role = 'PAYER'
          AND status = 'UNLINKED'
          AND upload_session_id = %s
          AND (
            LOWER(category) = 'payment'
            OR LOWER(description) LIKE '%%payment%%'
            OR LOWER(description) LIKE '%%settle%%'
            OR LOWER(description) LIKE '%%paid back%%'
        )
    """, (user_id, session_id))
    
    settlement_candidates = cur.fetchall()
    print(f"📋 Found {len(settlement_candidates)} potential settlement entries in Splitwise")
    
    if len(settlement_candidates) == 0:
        print("✅ No settlements to process")
        cur.close()
        conn.close()
        return 0
    
    settlements_marked = 0
    
    # Step 2: Process each settlement
    for split_txn in settlement_candidates:
        split_id, split_date, split_total, split_desc = split_txn  # 4 columns = 4 variables ✓
        
        if split_total is None:
            print(f"⚠️  Skipping {split_desc} - no amount")
            continue
        
        target_amount = float(split_total)
        tolerance = target_amount * 0.02
        
        print(f"\n🔎 Processing: {split_desc} | ₹{target_amount} | {split_date}")
        
        # Step 3: Find matching Bank withdrawal
        cur.execute("""
            SELECT id, date, description
            FROM transactions
            WHERE user_id = %s 
              AND source = 'BANK'
              AND amount < 0
              AND ABS(ABS(amount) - %s) <= %s
              AND date >= (%s::date - INTERVAL '2 days')
              AND date <= (%s::date + INTERVAL '2 days')
              AND status = 'UNLINKED'
        """, (user_id, target_amount, tolerance, split_date, split_date))
        
        bank_candidates = cur.fetchall()
        
        if len(bank_candidates) == 0:
            print("   ⚠️  No matching bank withdrawal found")
            continue
        
        # Step 4: Pick best match
        if len(bank_candidates) == 1:
            best_match = bank_candidates[0]
            print("   ✓ Single match found")
        else:
            # Multiple matches - use name similarity
            best_match = find_best_settlement_match(split_desc, bank_candidates)
            print(f"   ✓ Best match from {len(bank_candidates)} candidates")
        
        if best_match:
            bank_id = best_match[0]
            
            # Step 5: Mark both as Settlement
            cur.execute("""
                UPDATE transactions 
                SET category = 'Settlement', status = 'TRANSFER'
                WHERE id = %s
            """, (split_id,))
            
            cur.execute("""
                UPDATE transactions 
                SET category = 'Settlement', status = 'TRANSFER'
                WHERE id = %s
            """, (bank_id,))
            
            conn.commit()
            settlements_marked += 1
            
            print(f"   🔗 MARKED AS SETTLEMENT!")
            print(f"      Splitwise ID: {split_id}, Bank ID: {bank_id}")
    
    print(f"\n✅ Settlement Detection Complete. Marked {settlements_marked} settlements.")
    
    cur.close()
    conn.close()
    
    return settlements_marked

def auto_categorize_bank_transactions(session_id, user_id=1):
    """
    Auto-categorize bank transactions based on merchant keywords
    Should be run AFTER settlement/transfer detection
    """
    
    CATEGORY_KEYWORDS = {
        'Food & Dining': [
            'SWIGGY', 'ZOMATO', 'RESTAURANT', 'CAFE', 'KFC', 'MCDONALD', 
            'PIZZA', 'STARBUCKS', 'DOMINOS', 'SUBWAY', 'BURGER', 'HOTEL',
            'KITCHEN', 'CANTEEN', 'FOOD', 'DINING', 'DUNKIN', 'BASKIN'
        ],
        'Groceries': [
            'INSTAMART', 'BLINKIT', 'ZEPTO', 'BIGBASKET', 'DMART', 
            'SUPERMARKET', 'GROCERY', 'FRESH', 'VEGETABLES', 'FRUITS'
        ],
        'Transport': [
            'UBER', 'OLA', 'RAPIDO', 'METRO', 'IRCTC', 'BUS', 'PETROL', 
            'FUEL', 'TRAIN', 'FLIGHT', 'AIRLINE', 'MAKEMYTRIP', 'GOIBIBO',
            'CAB', 'TAXI', 'AUTO'
        ],
        'Shopping': [
            'AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'MEESHO', 'MALL',
            'SHOP', 'STORE', 'RETAIL', 'NYKAA', 'LENSKART'
        ],
        'Entertainment': [
            'NETFLIX', 'PRIME', 'HOTSTAR', 'BOOKMYSHOW', 'PVR', 'INOX',
            'SPOTIFY', 'YOUTUBE', 'CINEMA', 'MOVIE', 'GAME', 'GAMING'
        ],
        'Bills & Utilities': [
            'ELECTRICITY', 'WATER', 'GAS', 'BROADBAND', 'MOBILE', 'RECHARGE',
            'AIRTEL', 'JIO', 'VODAFONE', 'BILL', 'TATA POWER', 'BSNL'
        ],
        'Health': [
            'PHARMACY', 'MEDICINE', 'APOLLO', 'MEDPLUS', 'HOSPITAL',
            'DOCTOR', 'CLINIC', 'HEALTH', 'MEDICAL', '1MG', 'PHARMEASY'
        ],
        'Investment':[
            'GROWW', 'ZERODHA', 'ANGEL ONE', 'UPSTOX'
        ]
    }
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n🏷️  Auto-Categorizing Bank Transactions...")
    
    total_categorized = 0
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            cur.execute("""
                UPDATE transactions
                SET category = %s
                WHERE upload_session_id = %s
                  AND user_id = %s
                  AND source = 'BANK'
                  AND (category IS NULL OR category = 'Uncategorized')
                  AND status != 'TRANSFER'
                  AND UPPER(description) LIKE %s
            """, (category, session_id, user_id, f'%{keyword}%'))
            
            count = cur.rowcount
            if count > 0:
                total_categorized += count
                print(f"   ✓ {count} → '{category}' (keyword: {keyword})")
            
            conn.commit()
    
    # Set remaining as 'Other'
    cur.execute("""
        UPDATE transactions
        SET category = 'Other'
        WHERE upload_session_id = %s
          AND user_id = %s
          AND source = 'BANK'
          AND (category IS NULL OR category = 'Uncategorized')
          AND status != 'TRANSFER'
    """, (session_id, user_id))

    other_count = cur.rowcount
    if other_count > 0:
        print(f"   ℹ️  {other_count} → 'Other' (no keyword match)")
        total_categorized += other_count
    
    conn.commit()
    
    print(f"\n✅ Auto-Categorization Complete. Categorized {total_categorized} transactions.")
    
    cur.close()
    conn.close()
    
    return total_categorized

def find_best_settlement_match(split_desc, bank_candidates):
    """
    Pick best bank transaction when multiple candidates exist.
    """
    names = ['daksh', 'rk', 'prathamesh', 'goyal']
    
    best_match = None
    highest_score = -1
    
    for candidate in bank_candidates:
        bank_id, bank_date, bank_desc = candidate  # 3 columns = 3 variables ✓
        
        split_lower = split_desc.lower()
        bank_lower = bank_desc.lower()
        
        # Check name matches
        score = 0
        for name in names:
            if name in split_lower and name in bank_lower:
                score = 0.9
                break
        
        if score == 0:
            score = SequenceMatcher(None, split_lower, bank_lower).ratio()
        
        if score > highest_score:
            highest_score = score
            best_match = candidate
    
    return best_match if highest_score >= 0.3 else bank_candidates[0]


def detect_other_transfers(user_id=1, session_id=None):  
    """Add WHERE upload_session_id = session_id"""

    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n💳 Detecting Other Non-Spending Transactions...")
    
    transfer_patterns = {
        'Investment': ['ZERODHA', 'GROWW', 'UPSTOX', 'KUVERA', 'COIN', 'SMALLCASE'],
        'Credit Card': ['CREDIT CARD', 'CC PAYMENT', 'CRED', 'CARD BILL'],
        'Savings': ['TO SAVINGS', 'FIXED DEPOSIT', 'FD ', 'RD '],
        'Self Transfer': ['SELF TRANSFER', 'OWN ACCOUNT']
    }
    
    transfers_found = 0
    
    for transfer_type, keywords in transfer_patterns.items():
        for keyword in keywords:
            cur.execute("""
                UPDATE transactions
                SET category = %s, status = 'TRANSFER'
                WHERE user_id = %s
                  AND source = 'BANK'
                  AND UPPER(description) LIKE %s
                  AND status = 'UNLINKED'
                  AND upload_session_id = %s
            """, (transfer_type, user_id, f'%{keyword}%', session_id))
            
            count = cur.rowcount
            if count > 0:
                transfers_found += count
                print(f"   ✓ Marked {count} as '{transfer_type}' (keyword: {keyword})")
            
            conn.commit()
    
    if transfers_found == 0:
        print("   ℹ️  No investment/transfer patterns detected")
    
    print(f"\n✅ Other Transfers Detection Complete. Marked {transfers_found} transactions.")
    
    cur.close()
    conn.close()
    
    return transfers_found


if __name__ == "__main__":
    settlements = detect_settlements(user_id=1)
    other_transfers = detect_other_transfers(user_id=1)
    
    print(f"\n📊 SUMMARY:")
    print(f"   Settlements: {settlements}")
    print(f"   Other Transfers: {other_transfers}")
    print(f"   Total Non-Spending: {settlements + other_transfers}")