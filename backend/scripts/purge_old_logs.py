# scripts/purge_old_logs.py

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.error_logs import ErrorLog

def purge_logs(days_to_keep: int = 30):
    """
    Deletes error logs older than a specified number of days.
    """
    db: Session = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        num_deleted = db.query(ErrorLog).filter(ErrorLog.last_seen_at < cutoff_date).delete()
        
        db.commit()
        print(f"Successfully purged {num_deleted} old error log records.")
    except Exception as e:
        print(f"Error purging logs: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Example: Purge logs older than 90 days
    purge_logs(days_to_keep=90)