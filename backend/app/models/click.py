from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, INET
from app.core.database import Base
from datetime import datetime
import uuid
import enum
class ClickableType(str, enum.Enum):
    AD = "ad"
    POST = "story"
    # You can easily add more later, e.g., "USER_PROFILE", "EXTERNAL_LINK"

class Click(Base):
    __tablename__ = "clicks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # --- WHAT WAS CLICKED (Polymorphic Relationship) ---
    # The type of content that was clicked, e.g., "ad" or "post".
    clickable_type = Column(Enum(ClickableType), nullable=False, index=True)
    # The ID of the specific ad or post that was clicked.
    clickable_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # --- WHO CLICKED ---
    # The user who clicked. Nullable for anonymous (logged-out) users.
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    # A unique ID for the user's session. Helps track a user's journey before they log in.
    session_id = Column(String, nullable=True, index=True)
    
    # --- CONTEXT ---
    clicked_at = Column(DateTime, default=datetime.utcnow, index=True)
    # The IP address of the user. Good for geolocation and fraud detection.
    ip_address = Column(String(45), nullable=True) 
    # The user's browser/client information.
    user_agent = Column(String(255), nullable=True)
    # The URL the user came FROM. Essential for marketing analytics.
    referrer_url = Column(String, nullable=True)
    
    # --- BUSINESS METRICS ---
    # For ads, this would store the Cost Per Click (CPC) value. Null for other clicks.
    cost_per_click = Column(Numeric(10, 4), nullable=True)