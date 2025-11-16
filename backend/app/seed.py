import os
import sys
import logging
from dotenv import load_dotenv

# --- 1. LOAD ENV VARS FIRST ---
# This finds the .env file in the current directory (backend/)
# and loads it into the environment *before* we import config.
# This makes sure settings.DATABASE_URL is available.
load_dotenv()

# --- 2. NOW, IMPORT FROM APP ---
# These imports will now succeed because pydantic-settings
# can find the variables in the environment.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings # <-- This is the goal
from app.models.role import Role
from app.models.user import User
from app.dependencies import get_password_hasher

# Set up a simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_session() -> Session:
    """Creates a new, independent database session."""
    try:
        # Use the settings object as the Single Source of Truth
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

def seed_data():
    logger.info("Starting data seeding...")
    db = get_db_session()
    
    try:
        # --- 1. SEED ROLES ---
        roles_to_seed = ["user", "creator", "moderator", "superadmin"]
        role_objects = {}

        for role_name in roles_to_seed:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logger.info(f"Creating role: {role_name}")
                role = Role(name=role_name, description=f"The {role_name} role")
                db.add(role)
            role_objects[role_name] = role
        
        db.commit()
        logger.info("Roles seeded successfully.")

        # --- 2. SEED SUPERADMIN FROM SETTINGS ---
        # We read the admin details *directly* from the settings object
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            logger.info(f"Creating superadmin user: {settings.ADMIN_USERNAME}")
            hasher = get_password_hasher()
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                password_hash=hasher.hash(settings.ADMIN_PASSWORD),
                is_verified=True,
                is_otp_verified=True,
                role_id=role_objects["superadmin"].id
            )
            db.add(admin_user)
            db.commit()
            logger.info("Superadmin user created successfully.")
        else:
            logger.info("Superadmin user already exists.")
            
        logger.info("Data seeding complete.")

    except Exception as e:
        logger.error(f"An error occurred during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()