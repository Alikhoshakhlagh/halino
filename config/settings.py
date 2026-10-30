"""تنظیمات پروژه حالینو — نسخه دانشگاهی، ساده و بدون وابستگی بیرونی."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# در نسخه واقعی از متغیر محیطی خوانده شود
SECRET_KEY = "django-insecure-halino-dev-key-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "content",
    "journey",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ساده‌سازی دانشگاهی: SQLite. برای PostgreSQL فقط همین بلوک عوض می‌شود.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/auth/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/auth/login/"

# --- تنظیمات خود حالینو -------------------------------------------------
# در حالت توسعه کد OTP به‌جای پیامک در کنسول چاپ می‌شود.
HALINO_OTP_CONSOLE = True
HALINO_OTP_TTL_SECONDS = 120
HALINO_OTP_MAX_ATTEMPTS = 5

# چند پیشنهاد در هر لایه‌ی صفحه امروز
HALINO_PROFILE_SLOTS = 3
HALINO_MOOD_SLOTS = 3
# تا این تعداد روز، یک آیتم دوباره پیشنهاد نمی‌شود
HALINO_REPEAT_COOLDOWN_DAYS = 30
