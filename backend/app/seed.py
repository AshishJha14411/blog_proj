import os
import sys
import logging
from dotenv import load_dotenv

# 1. Load Env variables first
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.role import Role
from app.models.user import User
from app.dependencies import get_password_hasher

# --- ALEMBIC IMPORTS ---
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_url():
    # Prefer the Direct URL for setup tasks (Migrations & Seeding)
    return os.getenv("MIGRATION_DATABASE_URL") or settings.DATABASE_URL

def run_migrations():
    """Runs Alembic migrations programmatically."""
    logger.info("🚀 Starting Database Migrations...")
    try:
        # Create Alembic configuration object
        # We point it to the alembic.ini file in the backend root
        alembic_cfg = Config("alembic.ini")
        
        # FORCE the connection string. This overrides alembic.ini and env.py
        # This guarantees we use the Direct Connection.
        db_url = get_db_url()
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        # Run the upgrade
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations applied successfully.")
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)

def get_db_session() -> Session:
    """Creates a new database session."""
    try:
        # Use the same Direct URL for seeding
        engine = create_engine(get_db_url())
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        sys.exit(1)

def seed_data():
    logger.info("🌱 Starting data seeding...")
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

        # --- 2. SEED SUPERADMIN ---
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
            
        logger.info("✅ Data seeding complete.")

    except Exception as e:
        logger.error(f"❌ An error occurred during seeding: {e}")
        db.rollback()
        sys.exit(1) # Fail hard if seeding fails
    finally:
        db.close()

if __name__ == "__main__":
    # Run Migrations FIRST
    run_migrations()
    # THEN Run Seeds
    seed_data()


