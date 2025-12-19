import pandas as pd
import hashlib
from datetime import datetime
import re

def generate_transaction_hash(row_data_str):
    return hashlib.md5(row_data_str.encode()).hexdigest()

def clean_float(value):
    if pd.isna(value) or str(value).strip() == '':
        return 0.0
    try:
        clean_str = str(value).replace(',', '').strip()
        return float(clean_str)
    except ValueError:
        return 0.0

def clean_description(narration):
    """
    Applies multi-stage cleaning to extract meaningful entity names
    from Indian banking transaction strings (UPI, NEFT, ATM).
    """
    if not isinstance(narration, str):
        return str(narration)

    narration = narration.strip()
    
    # --- Layer 1: ATM & NEFT Handling ---
    # Handle ATM Withdrawals (NWD)
    # Format: NWD-CARD-REF-LOCATION
    if narration.startswith('NWD-'):
        parts = narration.split('-')
        location = parts[-1] if len(parts) > 1 else 'ATM Withdrawal'
        return f"ATM Withdrawal: {location}"

    # Handle NEFT / RTGS (Structure usually: TYPE-BANK-NAME-ID)
    if "NEFT" in narration or "RTGS" in narration:
        parts = narration.split('-')
        # Heuristic: Find the longest text segment that isn't a bank code
        candidates = [p.strip() for p in parts if len(p.strip()) > 2 and not p.strip().isdigit()]
        # Filter out bank codes (like CITI000...)
        candidates = [c for c in candidates if not re.match(r'^[A-Z]{4}\d+$', c)]
        
        if candidates:
            # The entity name is usually the longest remaining string
            return max(candidates, key=len).title()
        return narration # Fallback if pattern fails

    # --- Layer 2: UPI Handling ---
    # Remove technical prefixes
    prefix_pattern = r'^(UPI|IMPS|NEFT|POS|ATW|MB|CR)-?' 
    cleaned = re.sub(prefix_pattern, '', narration).strip()

    # Split by hyphen. Usually the format is: NAME-VPA-BANK...
    tokens = cleaned.split('-')
    raw_name = tokens[0]

    # --- Layer 3: Noise Reduction (The "Humanizer") ---
    
    # A. Remove Titles & Prefixes (Mr, Mrs, M/s, Shri)
    raw_name = re.sub(r'\b(MR|MRS|MS|M\/S|SHRI|SMT)\b\.?\s?', '', raw_name, flags=re.IGNORECASE)
    
    # B. Remove Corporate Suffixes
    raw_name = re.sub(r'\b(PVT|LTD|PRIVATE|LIMITED)\b\.?', '', raw_name, flags=re.IGNORECASE)

    # C. Remove Numbers at the start (Phone numbers common in UPI)
    raw_name = re.sub(r'^\d+', '', raw_name).strip()
    
    # D. Remove "UPI" if it lingers at the end
    raw_name = re.sub(r'\bUPI\b', '', raw_name, flags=re.IGNORECASE)

    # E. Remove Banking Junk Phrases
    noise_phrases = [
        "A UNIT OF", "PAYMENT FOR", "PAYMENT TO", "PAYMENT FROM", 
        "SENT USING", "VIA", "BILLED TO"
    ]
    for phrase in noise_phrases:
        if phrase in raw_name.upper():
             raw_name = re.split(phrase, raw_name, flags=re.IGNORECASE)[0]

    # F. Final Polish (Remove special chars, fix spaces)
    raw_name = re.sub(r'[^\w\s]', ' ', raw_name) 
    raw_name = re.sub(r'\s+', ' ', raw_name).strip()

    return raw_name.title()

def parse_date_smart(date_str):
    """Parse date with explicit format"""
    try:
        # Bank format: YYYY-MM-DD (ISO format)
        return pd.to_datetime(date_str, format='%Y-%m-%d')
    except:
        try:
            # Splitwise also uses YYYY-MM-DD
            return pd.to_datetime(date_str, format='%Y-%m-%d')
        except:
            # Last resort: no dayfirst
            try:
                return pd.to_datetime(date_str)
            except:
                return None

def normalize_bank_row(row, user_id=1):
    try:
        raw_date = str(row['Date']).strip()
        date_obj = parse_date_smart(raw_date)
        
        if date_obj is None:
            return None
        
        formatted_date = date_obj.strftime("%Y-%m-%d")
        withdrawal = clean_float(row.get('Withdrawal Amt.', 0))
        deposit = clean_float(row.get('Deposit Amt.', 0))
        amount = deposit - withdrawal 
        raw_desc = str(row.get('Narration', '')).strip()
        clean_desc = clean_description(raw_desc)

        return {
            "transaction_id": generate_transaction_hash(f"{formatted_date}{amount}{raw_desc}"),
            "user_id": user_id,
            "date": formatted_date,
            "amount": amount,
            "description": clean_desc,
            "source": "BANK",
            "category": "Uncategorized",
            "status": "UNLINKED",
            "raw_data": str(row.to_dict())
        }
    except Exception as e:
        if str(row.get('Date','')).strip() != '':
            print(f"⚠️ Skipping bank row: {e}")
        return None

def normalize_splitwise_row(row, user_id=1):
    try:
        raw_date = str(row['Date']).strip()
        date_obj = parse_date_smart(raw_date)
        
        if date_obj is None:
            return None
        
        formatted_date = date_obj.strftime("%Y-%m-%d")
        total_cost = clean_float(row['Cost'])
        description = str(row['Description']).strip()
        category = str(row['Category']).strip()
        
        my_col = "Prathamesh Patil"  # Your name
        if my_col not in row:
            for col in row.index:
                if "Prathamesh" in col:
                    my_col = col
                    break
            
        net_balance = clean_float(row[my_col])

        my_share = 0.0
        role = "PARTICIPANT"
        
        if net_balance > 0:
            my_share = total_cost - net_balance
            role = "PAYER"
        elif net_balance < 0:
            my_share = abs(net_balance)
            role = "BORROWER"

        final_amount = -1 * my_share

        return {
            "transaction_id": generate_transaction_hash(f"{formatted_date}{final_amount}{description}SPLIT"),
            "user_id": user_id,
            "date": formatted_date,
            "amount": final_amount,
            "description": description,
            "source": "SPLITWISE",
            "category": category,
            "status": "UNLINKED",
            "meta_role": role,
            "meta_total_cost": total_cost,
            "meta_net_balance": net_balance
        }

    except Exception as e:
        if str(row.get('Description','')).strip() != '':
            print(f"⚠️ Skipping splitwise row: {e}")
        return None