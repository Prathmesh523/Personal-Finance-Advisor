import os

class Config:
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_RAW = "raw_transactions"
    
    # Splitwise Configuration
    # This must match the column name in your CSV exactly
    SPLITWISE_USER_NAME = "Prathamesh Patil" 
    UPLOAD_SESSION_PREFIX = "session_"
    
    # Date Formats
    DATE_FORMAT_DB = "%Y-%m-%d"        # Standard ISO format for Postgres