import os

APP_TITLE = os.getenv("APP_TITLE", "PPC Surveyor Database")

DEFAULT_DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Ali@ali@123"),
    "database": os.getenv("DB_NAME", "surveyor_info"),
}

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "StrongPass123")

SURVEYOR_CODE_PREFIX = os.getenv("SURVEYOR_CODE_PREFIX", "PPC")  # PPC-KAB-001
