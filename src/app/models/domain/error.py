from datetime import datetime

from src.app.utils.tracing_context_utils import (
    request_context,
    user_query_context,
)


class Error:
    def __init__(self, error_message: str):
        self.request_id: str = str(request_context.get())
        self.user_query: str = str(user_query_context.get())
        self.error_message: str = error_message
        self.timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "user_query": self.user_query,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }
