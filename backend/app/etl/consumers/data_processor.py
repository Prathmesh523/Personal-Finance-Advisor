import json
import psycopg2
import pika
from app.config import Config
from app.database.connection import DB_CONFIG
from app.logger import setup_logger

logger = setup_logger(__name__)

def process_messages():
    # 1. Connect to DB
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        logger.info("Connected to Database")
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return

    # 2. Connect to RabbitMQ
    credentials = pika.PlainCredentials(Config.RABBITMQ_USER, Config.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=Config.RABBITMQ_HOST,
        port=Config.RABBITMQ_PORT,
        credentials=credentials
    )
    
    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        logger.info("Connected to RabbitMQ")
    except Exception as e:
        logger.error(f"RabbitMQ Connection failed: {e}")
        cur.close()
        conn.close()
        return
    
    # Declare queue (idempotent - creates if doesn't exist)
    channel.queue_declare(queue=Config.RABBITMQ_QUEUE, durable=True)
    
    # Fair dispatch - don't give worker new message until it's done
    channel.basic_qos(prefetch_count=1)
    
    logger.info(f"Consumer started. Listening on queue: {Config.RABBITMQ_QUEUE}")

    # 3. Define callback function for message processing
    def callback(ch, method, properties, body):
        try:
            data = json.loads(body.decode('utf-8'))
            logger.info(f"Processing {data.get('source')} transaction: {data.get('transaction_id')}")
            
            source = data.get('source')  # 'BANK' or 'SPLITWISE'
            
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
                icon = "🦁"
                logger.info(f"{icon} Bank: {data['description'][:30]:30} | ₹{data['amount']:,.2f}")
            
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
                icon = "🕐"
                logger.info(f"{icon} Split: {data['description'][:30]:30} | Role: {data['role'][:10]:10} | Share: ₹{data['my_share']:,.2f}")
            
            # Acknowledge message (delete from queue)
            logger.info(f"Successfully processed {source} transaction")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            conn.rollback()
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    # 4. Start consuming messages
    channel.basic_consume(
        queue=Config.RABBITMQ_QUEUE,
        on_message_callback=callback,
        auto_ack=False  # Manual acknowledgment
    )
    
    try:
        logger.info("Waiting for messages. Press CTRL+C to exit.\n")
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Shutting down consumer")
        channel.stop_consuming()
    finally:
        connection.close()
        cur.close()
        conn.close()
        logger.info("Consumer stopped cleanly")

if __name__ == "__main__":
    process_messages()