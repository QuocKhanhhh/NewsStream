import json 
import redis

class RedisClient:
    def __init__(self, host: str="redis", port: int=6379, db: int=0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
    
    def replace_list(self, key: str, values: list[dict]):
        serialized_values = [json.dumps(value) for value in values] 
        
        with self.client.pipeline() as pipe:
            pipe.delete(key)  # Delete the existing list
            if serialized_values:
                pipe.rpush(key, *serialized_values)  # Push new values to the list
            pipe.execute()  # Execute the pipeline
            
       
    def get_first(self, key: str) -> dict | None:
        serialized_value = self.client.lindex(key, 0)  # Get the first element of the list
        if serialized_value is not None:
            return json.loads(serialized_value)  # Deserialize the JSON string back to a dictionary
        return None
    
    def remove_first(self, key: str):
        self.client.lpop(key)  # Remove the first element of the list

    def pop_first(self, key: str) -> dict | None:
        serialized_value = self.client.lpop(key)
        if serialized_value is None:
            return None
        return json.loads(serialized_value)

    def push_last(self, key: str, value: dict):
        self.client.rpush(key, json.dumps(value))

    def remove_value(self, key: str, value: dict):
        self.client.lrem(key, 1, json.dumps(value))
        
        
    def ping(self) -> bool:
        try:
            return self.client.ping()  # Check if the Redis server is reachable
        except redis.ConnectionError:
            return False
