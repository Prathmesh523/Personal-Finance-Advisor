import pandas as pd
import json
import os
from confluent_kafka import Producer
from app.etl.parsers import normalize_bank_row
from app.config import Config

def get_kafka_producer():
    conf = {'bootstrap.servers': Config.KAFKA_BOOTSTRAP_SERVERS}
    return Producer(conf)

def delivery_report(err, msg):
    if err:
        print(f'❌ Message delivery failed: {err}')

def process_bank_file(filepath, session_id, start_date, end_date, user_id=1):
    """
    NEW PARAMETERS:
    - session_id: Upload session ID
    - start_date: Start of selected month
    - end_date: End of selected month
    """
    print(f"📂 Processing Bank File: {filepath}")
    
    try:
        # 1. Header Detection
        header_row_index = 0
        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if "Date" in line and "Narration" in line and "Withdrawal Amt." in line:
                    header_row_index = i
                    print(f"🎯 Found Header at Row: {i}")
                    break
        
        df = pd.read_csv(filepath, skiprows=header_row_index)
        
        producer = get_kafka_producer()
        count = 0
        excluded_count = 0

        for _, row in df.iterrows():
            raw_date = str(row['Date'])
            
            # Stop Conditions
            if "End Of Statement" in raw_date or "STATEMENT SUMMARY" in raw_date:
                print("🛑 Reached End of Statement. Stopping.")
                break
            
            if "*" in raw_date or pd.isna(row['Date']) or raw_date.strip() == "":
                continue
                
            clean_data = normalize_bank_row(row, user_id)
        
            if clean_data:
                transaction_date = clean_data['date']
                
                if start_date <= transaction_date <= end_date:
                    # ✅ Add source field (temporary, for consumer)
                    clean_data['source'] = 'BANK'  # NEW LINE
                    clean_data['upload_session_id'] = session_id
                    
                    producer.produce(
                        Config.KAFKA_TOPIC_RAW,
                        key=str(user_id),
                        value=json.dumps(clean_data),
                        callback=delivery_report
                    )
                    count += 1
                else:
                    excluded_count += 1
            
        producer.flush()
        print(f"🚀 Successfully sent {count} bank transactions.")
        
        return {
            "status": "success",
            "processed": count,
            "excluded": excluded_count  # NEW
        }

    except Exception as e:
        print(f"❌ Failed to process file: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 4:
        session_id = sys.argv[1]
        start_date = sys.argv[2]
        end_date = sys.argv[3]
        
        process_bank_file(
            "data/raw_uploads/bank_statement.csv",
            session_id,
            start_date,
            end_date
        )
    else:
        print("Usage: python bank_producer.py <session_id> <start_date> <end_date>")