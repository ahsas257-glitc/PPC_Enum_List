import os

# اگر streamlit نصب نبود (مثلاً در بعضی اسکریپت‌ها)، خطا ندهد
try:
    import streamlit as st
except Exception:
    st = None


APP_TITLE = os.getenv("APP_TITLE", "PPC Surveyor Database")


def _secret(path, default=None):
    """
    Reads from st.secrets if available, otherwise returns default.
    path format: "db.host" or "users.admin.password" etc.
    """
    if st is None:
        return default
    try:
        cur = st.secrets
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur
    except Exception:
        return default


# ---- Database Config (اگر هنوز دیتابیس استفاده می‌کنی) ----
DEFAULT_DB = {
    "host": os.getenv("DB_HOST", _secret("db.host", "localhost")),
    "port": int(os.getenv("DB_PORT", _secret("db.port", 3306))),
    "user": os.getenv("DB_USER", _secret("db.user", "root")),
    "password": os.getenv("DB_PASSWORD", _secret("db.password", "")),
    "database": os.getenv("DB_NAME", _secret("db.database", "surveyor_info")),
}

# ---- Auth ----
# اگر لاگین را از secrets.toml می‌خوانی، این‌ها دیگر لازم نیست.
# نگه داشتیم فقط برای backward compatibility (اگر جایی استفاده شده باشد)
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# ---- Other ----
SURVEYOR_CODE_PREFIX = os.getenv("SURVEYOR_CODE_PREFIX", _secret("app.surveyor_code_prefix", "PPC"))
