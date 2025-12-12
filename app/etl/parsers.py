import pandas as pd
import hashlib
import uuid
from datetime import datetime
from app.config import Config

def generate_transaction_hash(row_data_str):
    return hashlib.md5(row_data_str.encode()).hexdigest()

def clean_float(value):
    """
    Safely converts strings like '1,000.50', '', or 'NaN' to float.
    Returns 0.0 if conversion fails.
    """
    if pd.isna(value) or str(value).strip() == '':
        return 0.0
    try:
        # Remove commas and whitespace
        clean_str = str(value).replace(',', '').strip()
        return float(clean_str)
    except ValueError:
        return 0.0

def clean_description(raw_desc):
    # Remove common noise
    clean = raw_desc.upper()
    for noise in ['UPI-', 'POS-', 'IMPS-', 'NEFT-', 'RTGS-']:
        clean = clean.replace(noise, '')
    
    # Extract merchant name (after first dash if exists)
    parts = clean.split('-')
    if len(parts) > 1:
        return parts[1].strip()[:100]  # Limit length
    return clean.strip()[:100]

def normalize_bank_row(row, user_id=1):
    try:
        # 1. Parse Date
        raw_date = str(row['Date']).strip()
        date_obj = datetime.strptime(raw_date, Config.DATE_FORMAT_BANK)
        formatted_date = date_obj.strftime(Config.DATE_FORMAT_DB)

        # 2. Amount Calculation
        withdrawal = clean_float(row.get('Withdrawal Amt.', 0))
        deposit = clean_float(row.get('Deposit Amt.', 0))
        amount = deposit - withdrawal 

        # 3. Clean Description
        raw_desc = str(row.get('Narration', '')).strip()
        clean_desc=clean_description(raw_desc)

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
        # Only print error if it's not just a blank line
        if str(row.get('Date','')).strip() != '':
            print(f"⚠️ Skipping bank row: {e}")
        return None

def normalize_splitwise_row(row, user_id=1):
    try:
        # 1. Parse Date
        raw_date = str(row['Date']).strip()
        date_obj = pd.to_datetime(raw_date).date()
        formatted_date = date_obj.strftime(Config.DATE_FORMAT_DB)

        # 2. Extract Key Values safely
        total_cost = clean_float(row['Cost'])
        description = str(row['Description']).strip()
        category = str(row['Category']).strip()
        
        # 3. Get User's Net Balance
        my_col = Config.SPLITWISE_USER_NAME
        if my_col not in row:
            # Fallback check for "User" vs "User (You)" naming differences
            found = False
            for col in row.index:
                if Config.SPLITWISE_USER_NAME in col:
                    my_col = col
                    found = True
                    break
            if not found:
                raise ValueError(f"Column '{Config.SPLITWISE_USER_NAME}' not found")
            
        net_balance = clean_float(row[my_col])

        # 4. The Logic
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
        # Only print if it looks like real data
        if str(row.get('Description','')).strip() != '':
            print(f"⚠️ Skipping splitwise row: {e}")
        return None