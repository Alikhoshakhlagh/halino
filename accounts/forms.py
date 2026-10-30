import re

from django import forms

PHONE_RE = re.compile(r"^09\d{9}$")


def normalize_phone(raw):
    """۰۹۱۲... / +98912... / 0912 123 4567 را به یک قالب واحد تبدیل می‌کند."""
    digits = raw.strip()
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    digits = digits.translate(trans)
    digits = re.sub(r"[^\d+]", "", digits)
    if digits.startswith("+98"):
        digits = "0" + digits[3:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits


class PhoneForm(forms.Form):
    phone = forms.CharField(label="شماره موبایل", max_length=20)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not PHONE_RE.match(phone):
            raise forms.ValidationError("شماره موبایل معتبر نیست.")
        return phone


class CodeForm(forms.Form):
    code = forms.CharField(label="کد تأیید", max_length=6, min_length=6)

    def clean_code(self):
        trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        code = self.cleaned_data["code"].strip().translate(trans)
        if not code.isdigit():
            raise forms.ValidationError("کد فقط عدد است.")
        return code
