import os

class Config:
    # RabbitMQ Configuration
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
    RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
    RABBITMQ_QUEUE = "transactions_queue"
    
    # Splitwise Configuration
    SPLITWISE_USER_NAME = "Prathamesh Patil"  # Must match CSV column name
    UPLOAD_SESSION_PREFIX = "session_"
    
    # Date Formats
    DATE_FORMAT_DB = "%Y-%m-%d"  # Standard ISO format for Postgres