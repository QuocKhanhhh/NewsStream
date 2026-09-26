import json
from kafka import KafkaProducer
from typing import Any, Dict

class KafkaClient:
    def __init__(self, bootstrap_servers: list[str]):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(
                value,
                ensure_ascii=False,
            ).encode("utf-8"),
            acks="all",
            retries=5,
        )
        
    def publish(self, topic: str, message: Dict[str, Any], key: str | None = None):
        encoded_key = key.encode("utf-8") if key else None
        future = self.producer.send(topic, value=message, key=encoded_key)
        return future.get(timeout=30)  # Wait for the send to complete and return metadata
    
    def flush(self):
        self.producer.flush()  # Ensure all messages are sent before closing
        
    def close(self):
        self.producer.close()  # Close the producer to free up resources
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.flush()
        self.close()  # Ensure the producer is closed when exiting the context manager
        
        