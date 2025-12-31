import pandas as pd
import json
import os
import pika
from app.etl.parsers import normalize_bank_row
from app.config import Config
from app.logger import setup_logger

logger = setup_logger(__name__)

def get_rabbitmq_connection():
    """Create RabbitMQ connection"""
    credentials = pika.PlainCredentials(Config.RABBITMQ_USER, Config.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=Config.RABBITMQ_HOST,
        port=Config.RABBITMQ_PORT,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

def process_bank_file(filepath, session_id, start_date, end_date, user_id=1):
    """
    NEW PARAMETERS:
    - session_id: Upload session ID
    - start_date: Start of selected month
    - end_date: End of selected month
    """
    logger.info(f"Processing Bank File: {filepath}")
    
    try:
        # 1. Header Detection
        header_row_index = 0
        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if "Date" in line and "Narration" in line and "Withdrawal Amt." in line:
                    header_row_index = i
                    logger.info(f"Found header at row {i}")
                    break
        
        df = pd.read_csv(filepath, skiprows=header_row_index)
        
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue=Config.RABBITMQ_QUEUE, durable=True)
        count = 0
        excluded_count = 0

        for _, row in df.iterrows():
            raw_date = str(row['Date'])
            
            # Stop Conditions
            if "End Of Statement" in raw_date or "STATEMENT SUMMARY" in raw_date:
                logger.info("Reached end of statement")
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
                    
                    channel.basic_publish(
                        exchange='',
                        routing_key=Config.RABBITMQ_QUEUE,
                        body=json.dumps(clean_data),
                        properties=pika.BasicProperties(delivery_mode=2)  # Persistent
                    )
                    count += 1
                else:
                    excluded_count += 1
            
        connection.close()
        logger.info(f"Successfully queued {count} bank transactions")
        
        return {
            "status": "success",
            "processed": count,
            "excluded": excluded_count  # NEW
        }

    except Exception as e:
        logger.error(f"Failed to process file: {e}", exc_info=True)
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