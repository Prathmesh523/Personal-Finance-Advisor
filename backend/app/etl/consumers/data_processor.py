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
                
                source = data.get('source')  # 'BANK' or 'SPLITWISE' (temporary field)
                
                if source == 'BANK':
                    # Insert into bank_transactions
                    insert_query = """
                    INSERT INTO bank_transactions 
                    (transaction_id, user_id, upload_session_id, date, amount, 
                     description, category, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO NOTHING;
                    """
                    
                    cur.execute(insert_query, (
                        data['transaction_id'],
                        data['user_id'],
                        data.get('upload_session_id'),
                        data['date'],
                        data['amount'],
                        data['description'],
                        data['category'],
                        data['status']
                    ))
                    
                    conn.commit()
                    icon = "🏦"
                    print(f"{icon} Bank: {data['description'][:30]:30} | ₹{data['amount']:,.2f}")
                
                elif source == 'SPLITWISE':
                    # Insert into splitwise_transactions
                    insert_query = """
                    INSERT INTO splitwise_transactions 
                    (transaction_id, user_id, upload_session_id, date, total_cost,
                     description, category, my_column_value, my_share, role, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO NOTHING;
                    """
                    
                    cur.execute(insert_query, (
                        data['transaction_id'],
                        data['user_id'],
                        data.get('upload_session_id'),
                        data['date'],
                        data['total_cost'],
                        data['description'],
                        data['category'],
                        data['my_column_value'],
                        data['my_share'],
                        data['role'],
                        data['status']
                    ))
                    
                    conn.commit()
                    icon = "🍕"
                    print(f"{icon} Split: {data['description'][:30]:30} | Role: {data['role'][:10]:10} | Share: ₹{data['my_share']:,.2f}")

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