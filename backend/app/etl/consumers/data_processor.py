import json
import psycopg2
from confluent_kafka import Consumer
from app.config import Config
from app.database.connection import DB_CONFIG

def process_messages():
    # 1. Connect to DB
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("🔌 Connected to Database.")
    except Exception as e:
        print(f"❌ DB Connection failed: {e}")
        return

    # 2. Connect to Kafka
    conf = {
        'bootstrap.servers': Config.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'processor-group-main',
        'auto.offset.reset': 'earliest'
    }
    consumer = Consumer(conf)
    consumer.subscribe([Config.KAFKA_TOPIC_RAW])
    
    print(f"👀 Consumer started. Listening on '{Config.KAFKA_TOPIC_RAW}'...")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None: continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            # 3. Parse Data
            try:
                data = json.loads(msg.value().decode('utf-8'))
                
                txn_hash = data['transaction_id']
                user_id = data['user_id']
                date = data['date']
                amount = float(data['amount'])
                desc = data['description']
                source = data['source']
                category = data.get('category', 'Uncategorized')
                status = data.get('status', 'UNLINKED') # FIX: Get Status
                
                role = data.get('meta_role', None)
                total_bill = data.get('meta_total_cost', None)

                # 4. Insert into Postgres (FIX: Added status column)
                insert_query = """
                INSERT INTO transactions 
                (transaction_id, user_id, date, amount, description, source, category, 
                status, role, meta_total_bill, upload_session_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (transaction_id) DO NOTHING;
                """
                
                # Add upload_session_id to values
                session_id = data.get('upload_session_id', None)  # NEW

                cur.execute(insert_query, (
                    txn_hash, user_id, date, amount, desc, source, 
                    category, status, role, total_bill, session_id  # NEW
                ))
                conn.commit()
                
                icon = "🏦" if source == "BANK" else "🍕"
                print(f"{icon} Saved: {desc[:20]}... | {amount}")

            except Exception as e:
                print(f"❌ Error processing message: {e}")
                conn.rollback()

    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        consumer.close()
        cur.close()
        conn.close()

if __name__ == "__main__":
    process_messages()