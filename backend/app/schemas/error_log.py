from pydantic import BaseModel
from typing import Optional, Dict, Any

# This schema is NOT for an API.
# It's an internal "template" for creating a new error log entry.
class ErrorLogCreateSchema(BaseModel):
    level: str
    message: str
    traceback: Optional[str] = None
    request_context: Optional[Dict[str, Any]] = None
