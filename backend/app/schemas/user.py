# In app/schemas/users.py (or a similar file)
from pydantic import BaseModel

class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True # or orm_mode = True