from app.database.connection import get_db_connection
from difflib import SequenceMatcher
import re
from psycopg2.extras import execute_values

def apply_user_categorization_rules(session_id, user_id=1):
    """
    Apply user-defined categorization rules BEFORE keyword matching
    This gives user rules highest priority
    """
    from app.services.categorization_rules import apply_user_rules_to_transaction
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n🎯 Applying User Categorization Rules...")
    
    # Apply to bank transactions
    cur.execute("""
        SELECT id, description
        FROM bank_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND (category IS NULL OR category = 'Uncategorized')
          AND status != 'TRANSFER'
    """, (session_id, user_id))
    
    bank_txns = cur.fetchall()
    bank_categorized = 0
    
    for txn_id, description in bank_txns:
        matched_category = apply_user_rules_to_transaction(description, 'BANK', user_id)
        if matched_category:
            cur.execute("""
                UPDATE bank_transactions
                SET category = %s
                WHERE id = %s
            """, (matched_category, txn_id))
            bank_categorized += 1
    
    conn.commit()
    
    # Apply to splitwise transactions
    cur.execute("""
        SELECT id, description
        FROM splitwise_transactions
        WHERE upload_session_id = %s
          AND user_id = %s
          AND (category IS NULL OR category = 'Uncategorized')
    """, (session_id, user_id))
    
    split_txns = cur.fetchall()
    split_categorized = 0
    
    for txn_id, description in split_txns:
        matched_category = apply_user_rules_to_transaction(description, 'SPLITWISE', user_id)
        if matched_category:
            cur.execute("""
                UPDATE splitwise_transactions
                SET category = %s
                WHERE id = %s
            """, (matched_category, txn_id))
            split_categorized += 1
    
    conn.commit()
    
    if bank_categorized > 0 or split_categorized > 0:
        print(f"   ✅ User rules: {bank_categorized} bank, {split_categorized} splitwise")
    
    cur.close()
    conn.close()
    
    return bank_categorized + split_categorized

def detect_settlements(user_id=1, session_id=None):
    """Detect and mark settlement transactions"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("\n🔍 Starting Settlement Detection...")
    
    # Step 1: Find Splitwise settlements (already marked during parsing)
    cur.execute("""
        SELECT id, date, total_cost, description
        FROM splitwise_transactions
        WHERE user_id = %s 
          AND upload_session_id = %s
          AND status = 'SETTLEMENT'
    """, (user_id, session_id))
    
    settlement_candidates = cur.fetchall()
    print(f"📋 Found {len(settlement_candidates)} settlement entries in Splitwise")
    
    if len(settlement_candidates) == 0:
        print("✅ No settlements to process")
        cur.close()
        conn.close()
        return 0
    
    settlements_marked = 0
    
    # Step 2: Process each settlement
    for split_txn in settlement_candidates:
        split_id, split_date, split_total, split_desc = split_txn
        
        if split_total is None:
            print(f"⚠️ Skipping {split_desc} - no amount")
            continue
        
        target_amount = float(split_total)
        tolerance = target_amount * 0.02
        
        print(f"\n🔎 Processing: {split_desc} | ₹{target_amount} | {split_date}")
        
        # Step 3: Find matching Bank transaction
        cur.execute("""
            SELECT id, date, description
            FROM bank_transactions
            WHERE user_id = %s 
              AND ABS(ABS(amount) - %s) <= %s
              AND date >= (%s::date - INTERVAL '2 days')
              AND date <= (%s::date + INTERVAL '2 days')
              AND status = 'UNLINKED'
        """, (user_id, target_amount, tolerance, split_date, split_date))
        
        bank_candidates = cur.fetchall()
        
        if len(bank_candidates) == 0:
            print("   ⚠️ No matching bank transaction found")
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
            
            # Step 5: Mark both as Settlement and link them
            cur.execute("""
                UPDATE splitwise_transactions 
                SET category = 'Settlement', 
                    linked_bank_id = %s,
                    status = 'LINKED'
                WHERE id = %s
            """, (bank_id, split_id))
            
            cur.execute("""
                UPDATE bank_transactions 
                SET category = 'Settlement', 
                    linked_splitwise_id = %s,
                    status = 'TRANSFER'
                WHERE id = %s
            """, (split_id, bank_id))
            
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
    Auto-categorize bank transactions with user config support
    """
    
    # PRIORITY 1: Apply user rules first
    apply_user_categorization_rules(session_id, user_id)
    
    # PRIORITY 2: Get user config from session
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_config FROM upload_sessions WHERE id = %s
    """, (session_id,))
    
    result = cur.fetchone()
    user_config = {}
    
    if result and result[0]:
        user_config = result[0]  # ✅ FIXED - Already a dict from JSONB
    
    family_members = user_config.get('family_members', [])
    monthly_rent = user_config.get('monthly_rent')
    
    print(f"\n🎯 User Config: Family={family_members}, Rent={monthly_rent}")
    
    # Expanded keyword categories (same as before)
    CATEGORY_KEYWORDS = {
        'Food & Dining': [
            'SWIGGY', 'ZOMATO', 'DUNZO', 'FRESHMENU', 'FAASOS', 'BEHROUZ',
            'RESTAURANT', 'CAFE', 'COFFEE', 'KFC', 'MCDONALD', 'PIZZA', 
            'DOMINO', 'SUBWAY', 'BURGER', 'STARBUCKS', 'CCD', 'BARISTA',
            'HOTEL', 'DHABA', 'KITCHEN', 'CANTEEN', 'FOOD', 'DINING',
            'BASKIN', 'DUNKIN', 'TACO BELL', 'HALDIRAM', 'BIRYANI',
            'CHINESE', 'NORTH INDIAN', 'SOUTH INDIAN', 'CONTINENTAL'
        ],
        'Groceries': [
            'INSTAMART', 'BLINKIT', 'ZEPTO', 'BIGBASKET', 'DMART', 
            'SUPERMARKET', 'GROCERY', 'FRESH', 'VEGETABLES', 'FRUITS',
            'RELIANCE FRESH', 'MORE MEGASTORE', 'SPAR', 'JIOMART'
        ],
        'Transport': [
            'UBER', 'OLA', 'RAPIDO', 'METRO', 'IRCTC', 'BUS', 'PETROL', 
            'FUEL', 'TRAIN', 'FLIGHT', 'AIRLINE', 'MAKEMYTRIP', 'GOIBIBO',
            'CAB', 'TAXI', 'AUTO', 'INDIAN OIL', 'HP PETROL', 'BHARAT PETROLEUM',
            'FASTAG', 'PARKING', 'TOLL'
        ],
        'Shopping': [
            'AMAZON', 'FLIPKART', 'MYNTRA', 'AJIO', 'MEESHO', 'MALL',
            'SHOP', 'STORE', 'RETAIL', 'NYKAA', 'LENSKART', 'CROMA',
            'LIFESTYLE', 'WESTSIDE', 'PANTALOONS', 'MAX FASHION',
            'DECATHLON', 'NIKE', 'ADIDAS'
        ],
        'Entertainment': [
            'NETFLIX', 'PRIME', 'HOTSTAR', 'BOOKMYSHOW', 'PVR', 'INOX',
            'SPOTIFY', 'YOUTUBE', 'CINEMA', 'MOVIE', 'GAME', 'GAMING',
            'PLAY STORE', 'APP STORE', 'STEAM', 'XBOX', 'PLAYSTATION'
        ],
        'Bills & Utilities': [
            'ELECTRICITY', 'WATER', 'GAS', 'BROADBAND', 'MOBILE', 'RECHARGE',
            'AIRTEL', 'JIO', 'VODAFONE', 'BILL', 'TATA POWER', 'BSNL',
            'ACT FIBERNET', 'HATHWAY', 'DTH', 'DISH TV'
        ],
        'Health': [
            'PHARMACY', 'MEDICINE', 'APOLLO', 'MEDPLUS', 'HOSPITAL',
            'DOCTOR', 'CLINIC', 'HEALTH', 'MEDICAL', '1MG', 'PHARMEASY',
            'NETMEDS', 'DIAGNOSTIC', 'LAB TEST', 'PRACTO'
        ],
        'Investment': [
            'GROWW', 'ZERODHA', 'ANGEL ONE', 'UPSTOX', 'SIP', 'MUTUAL FUND',
            'STOCKS', 'KUVERA', 'COIN', 'SMALLCASE', 'ETF'
        ],
        'Education': [
            'UDEMY', 'COURSERA', 'UNACADEMY', 'BYJU', 'SCHOOL', 'COLLEGE',
            'TUITION', 'COURSE', 'BOOK', 'EXAM FEE'
        ]
    }
    
    total_categorized = 0
    family_categorized = 0
    rent_categorized = 0
    
    # 1. Family Transfer Detection (Fuzzy match)
    if family_members:
        for member in family_members:
            member_upper = member.upper().strip()
            
            # Fuzzy search: match if ANY word from member name appears
            name_parts = member_upper.split()
            
            for name_part in name_parts:
                if len(name_part) >= 3:  # Skip very short words like "MR", "MS"
                    cur.execute("""
                        UPDATE bank_transactions
                        SET category = 'Family Transfer'
                        WHERE upload_session_id = %s
                          AND user_id = %s
                          AND (category IS NULL OR category = 'Uncategorized')
                          AND status != 'TRANSFER'
                          AND UPPER(description) LIKE %s
                    """, (session_id, user_id, f'%{name_part}%'))
                    
                    count = cur.rowcount
                    if count > 0:
                        family_categorized += count
                        print(f"   ✅ {count} → 'Family Transfer' (matched: {name_part})")
                    
                    conn.commit()
    
    # 2. Rent Detection (Amount-based with tolerance)
    if monthly_rent and monthly_rent > 0:
        tolerance = monthly_rent * 0.05  # ±5% tolerance
        
        cur.execute("""
            UPDATE bank_transactions
            SET category = 'Rent'
            WHERE upload_session_id = %s
              AND user_id = %s
              AND (category IS NULL OR category = 'Uncategorized')
              AND status != 'TRANSFER'
              AND amount < 0
              AND ABS(ABS(amount) - %s) <= %s
        """, (session_id, user_id, monthly_rent, tolerance))
        
        rent_categorized = cur.rowcount
        if rent_categorized > 0:
            print(f"   ✅ {rent_categorized} → 'Rent' (amount ≈ ₹{monthly_rent:,.0f})")
        
        conn.commit()
    
    # 3. Keyword-based categorization
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            cur.execute("""
                UPDATE bank_transactions
                SET category = %s
                WHERE upload_session_id = %s
                  AND user_id = %s
                  AND (category IS NULL OR category = 'Uncategorized')
                  AND status != 'TRANSFER'
                  AND UPPER(description) LIKE %s
            """, (category, session_id, user_id, f'%{keyword}%'))
            
            count = cur.rowcount
            if count > 0:
                total_categorized += count
                print(f"   ✅ {count} → '{category}' (keyword: {keyword})")
            
            conn.commit()
    
    # 4. Set remaining as 'Other'
    cur.execute("""
        UPDATE bank_transactions
        SET category = 'Other'
        WHERE upload_session_id = %s
          AND user_id = %s
          AND (category IS NULL OR category = 'Uncategorized')
          AND status != 'TRANSFER'
    """, (session_id, user_id))

    other_count = cur.rowcount
    if other_count > 0:
        print(f"   ℹ️  {other_count} → 'Other' (no keyword match)")
        total_categorized += other_count
    
    conn.commit()
    
    print(f"\n✅ Categorization Complete:")
    print(f"   Family: {family_categorized}")
    print(f"   Rent: {rent_categorized}")
    print(f"   Keywords: {total_categorized - family_categorized - rent_categorized}")
    print(f"   Total: {total_categorized}")
    
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
    """Detect non-spending transactions like investments, CC payments"""
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
                UPDATE bank_transactions
                SET category = %s, status = 'TRANSFER'
                WHERE user_id = %s
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