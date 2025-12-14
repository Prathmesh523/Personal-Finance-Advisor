import pandas as pd
import hashlib
from datetime import datetime

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

def clean_description(raw_desc):
    clean = raw_desc.upper()
    for noise in ['UPI-', 'POS-', 'IMPS-', 'NEFT-', 'RTGS-']:
        clean = clean.replace(noise, '')
    parts = clean.split('-')
    if len(parts) > 1:
        return parts[1].strip()[:100]
    return clean.strip()[:100]

def parse_date_smart(date_str):
    """Parse date in any common format"""
    try:
        return pd.to_datetime(date_str, dayfirst=True)
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