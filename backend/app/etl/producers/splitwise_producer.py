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
    Process splitwise file with skip tracking
    """
    print(f"📂 Processing Splitwise File: {filepath}")
    
    try:
        # Header detection (same as before)
        header_row = 0
        with open(filepath, 'r') as f:
            first_line = f.readline()
            if "Date" not in first_line:
                header_row = 1
                
        df = pd.read_csv(filepath, skiprows=header_row)
        
        producer = get_kafka_producer()
        count = 0
        excluded_count = 0
        skipped_not_involved = 0  # ✅ NEW counter

        # Iterate and Produce
        for _, row in df.iterrows():
            raw_date = str(row['Date']).strip()
            description = str(row.get('Description', '')).strip()

            # Stop conditions (same as before)
            if "Total balance" in description:
                print("🛑 Reached 'Total balance' footer. Stopping.")
                break
            
            if pd.isna(row['Date']) or raw_date == '' or raw_date.lower() == 'nan':
                print("🛑 Reached empty row. Stopping.")
                break

            clean_data = normalize_splitwise_row(row, user_id)
        
            if clean_data:
                # ✅ NEW: Check if should skip
                if clean_data.get('skip'):
                    skipped_not_involved += 1
                    continue
                
                transaction_date = clean_data['date']
                
                # Date range filter
                if start_date <= transaction_date <= end_date:
                    # ✅ Add source field (temporary, for consumer)
                    clean_data['source'] = 'SPLITWISE'
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
        print(f"⏭️  Skipped {skipped_not_involved} transactions (not involved)")  # ✅ NEW
        
        return {
            "status": "success",
            "processed": count,
            "excluded": excluded_count,
            "skipped_not_involved": skipped_not_involved  # ✅ NEW
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