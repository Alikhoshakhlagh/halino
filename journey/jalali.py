"""
تبدیل تاریخ میلادی و شمسی — بدون هیچ وابستگی بیرونی.

تاریخ‌ها در دیتابیس میلادی ذخیره می‌شوند (استاندارد جنگو) و فقط موقع نمایش
به شمسی تبدیل می‌شوند. الگوریتم، پیاده‌سازی متعارف تقویم جلالی است.
"""

MONTH_NAMES = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

# تقویم ایرانی هفته را از شنبه شروع می‌کند
WEEKDAY_NAMES = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_farsi_digits(value):
    return str(value).translate(_FA_DIGITS)


def gregorian_to_jalali(gy, gm, gd):
    g_days_in_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621

    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_days_in_month[gm - 1]
    )

    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365

    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy, jm, jd):
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621

    days = (
        365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )

    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1

    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    month_days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    for length in month_days:
        if gd <= length:
            break
        gd -= length
        gm += 1
    return gy, gm, gd


def is_jalali_leap(jy):
    """اگر ۳۰ اسفند آن سال وجود داشته باشد، سال کبیسه است."""
    return gregorian_to_jalali(*jalali_to_gregorian(jy, 12, 30)) == (jy, 12, 30)


def jalali_month_length(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def to_jalali(date):
    """datetime.date -> (jy, jm, jd)"""
    return gregorian_to_jalali(date.year, date.month, date.day)


def format_jalali(date, with_weekday=False):
    jy, jm, jd = to_jalali(date)
    text = f"{to_farsi_digits(jd)} {MONTH_NAMES[jm - 1]} {to_farsi_digits(jy)}"
    if with_weekday:
        text = f"{WEEKDAY_NAMES[jalali_weekday(date)]}، {text}"
    return text


def jalali_weekday(date):
    """۰ = شنبه … ۶ = جمعه (بر خلاف پایتون که دوشنبه را صفر می‌گیرد)."""
    return (date.weekday() + 2) % 7
