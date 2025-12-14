from datetime import datetime
import threading

class LoggerService:
    def __init__(self):
        self.lock = threading.Lock()
    
    def log(self, level: str, message: str, user_id: str = None, action: str = None):
        with self.lock:
            timestamp = datetime.now().isoformat()
            log_entry = f"[{timestamp}] [{level}]"
            
            if user_id:
                log_entry += f" [User: {user_id}]"
            
            if action:
                log_entry += f" [Action: {action}]"
            
            log_entry += f" {message}"
            
            print(log_entry)
