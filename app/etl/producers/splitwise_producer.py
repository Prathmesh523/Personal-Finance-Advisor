import pandas as pd
import json
import os
from confluent_kafka import Producer
from app.etl.parsers import normalize_splitwise_row
from app.config import Config

def get_kafka_producer():
    conf = {'bootstrap.servers': Config.KAFKA_BOOTSTRAP_SERVERS}
    return Producer(conf)

def delivery_report(err, msg):
    if err:
        print(f'❌ Message delivery failed: {err}')

def process_splitwise_file(filepath, session_id, start_date, end_date, user_id=1):
    """
    NEW PARAMETERS:
    - session_id: Upload session ID  
    - start_date: Start of selected month
    - end_date: End of selected month
    """
    print(f"📂 Processing Splitwise File: {filepath}")
    
    try:
        # 1. Header Detection (Skip Title Rows)
        header_row = 0
        with open(filepath, 'r') as f:
            first_line = f.readline()
            if "Date" not in first_line:
                header_row = 1
                
        df = pd.read_csv(filepath, skiprows=header_row)
        
        producer = get_kafka_producer()
        count = 0
        excluded_count = 0

        # 2. Iterate and Produce
        for _, row in df.iterrows():
            raw_date = str(row['Date']).strip()
            description = str(row.get('Description', '')).strip()

            # --- STOPPING CONDITIONS ---
            # 1. Stop at the summary row at the bottom
            if "Total balance" in description:
                print("🛑 Reached 'Total balance' footer. Stopping.")
                break
            
            # 2. Stop at empty rows (End of file)
            if pd.isna(row['Date']) or raw_date == '' or raw_date.lower() == 'nan':
                print("🛑 Reached empty row. Stopping.")
                break

            clean_data = normalize_splitwise_row(row, user_id)
        
            if clean_data:
                transaction_date = clean_data['date']
                
                # NEW: Filter by date range
                if start_date <= transaction_date <= end_date:
                    # Add session_id
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
        print(f"🚀 Successfully sent {count} Splitwise transactions.")
        
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
        
        process_splitwise_file(
            "data/raw_uploads/splitwise_october.csv",
            session_id,
            start_date,
            end_date
        )
    else:
        print("Usage: python splitwise_producer.py <session_id> <start_date> <end_date>")