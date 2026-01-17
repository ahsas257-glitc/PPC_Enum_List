from __future__ import annotations
import re
from typing import Optional, Tuple

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
E164_RE = re.compile(r"^\+[1-9][0-9]{7,14}$")
TAZKIRA_RE = re.compile(r"^[0-9]{4}-[0-9]{4}-[0-9]{5}$")


COUNTRY_CODES = [
    ("Afghanistan (+93)", "+93"),
    ("Pakistan (+92)", "+92"),
    ("Iran (+98)", "+98"),
    ("Tajikistan (+992)", "+992"),
    ("Uzbekistan (+998)", "+998"),
    ("Other", ""),
]


def validate_email(email: str) -> Optional[str]:
    if not email or not EMAIL_RE.match(email.strip()):
        return "ایمیل درست نیست. مثال: name@example.com"
    return None


def validate_tazkira(tazkira: str) -> Optional[str]:
    if not tazkira or not TAZKIRA_RE.match(tazkira.strip()):
        return "فرمت تذکره درست نیست. مثال: 1234-5678-91011"
    return None


def normalize_phone(raw_number: str, selected_code: str) -> Tuple[Optional[str], Optional[str]]:
    """
    خروجی: (شماره نهایی E.164, پیام خطا)
    قوانین:
    - اگر کاربر با + زد، همان را validate می‌کند
    - اگر + نیست، country code انتخابی + digits را می‌سازد
    - صفر اول شماره را حذف می‌کند
    """
    if raw_number is None:
        raw_number = ""
    s = raw_number.strip()

    if s.startswith("+"):
        s2 = "+" + re.sub(r"\D", "", s)
        if E164_RE.match(s2):
            return s2, None
        return None, "شماره باید به شکل بین‌المللی (E.164) باشد مثل +937XXXXXXXX"

    digits = re.sub(r"\D", "", s)
    if digits.startswith("0"):
        digits = digits[1:]

    code = (selected_code or "").strip() or "+93"

    if not digits:
        return None, "شماره تماس را وارد کنید."

    normalized = code + digits

    if not E164_RE.match(normalized):
        return None, "شماره تماس معتبر نیست. مثال: +93731212123"

    if code == "+93":
        after = normalized[3:]
        if len(after) != 9:
            return None, "برای افغانستان (+93)، شماره باید ۹ رقم باشد (بدون صفر ابتدایی)."

    return normalized, None
def validate_payment_fields(payment_type: str, account_number: str, mobile_number: str) -> dict:
    """
    مطابق CHECK در SQL:
    - اگر BANK_ACCOUNT => Account_Number باید پر باشد
    - اگر MOBILE_CREDIT => Mobile_Number باید E.164 باشد و پر باشد
    """
    errs = {}
    if payment_type == "BANK_ACCOUNT":
        if not (account_number or "").strip():
            errs["account_number"] = "برای نوع BANK_ACCOUNT، نمبر حساب الزامی است."
    elif payment_type == "MOBILE_CREDIT":
        if not (mobile_number or "").strip():
            errs["mobile_number"] = "برای نوع MOBILE_CREDIT، نمبر موبایل الزامی است."
        else:
            # استفاده از E164_RE موجود
            if not E164_RE.match(mobile_number.strip()):
                errs["mobile_number"] = "نمبر موبایل باید E.164 باشد مثل +937XXXXXXXX"
    return errs
