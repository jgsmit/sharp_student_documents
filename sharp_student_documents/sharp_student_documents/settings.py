import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
import stripe
import paypalrestsdk
from decimal import Decimal
import cloudinary as cloudinary_lib

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env variables (explicit path so it works regardless of CWD)
load_dotenv(BASE_DIR / ".env")

# --- Security ---
def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value.strip())
    except Exception:
        return default

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("SECRET_KEY")
DEBUG = _env_bool("DEBUG", default=False)
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '.onrender.com',
    '.pythonanywhere.com',
    'sharpstudentdoc.com',
    'www.sharpstudentdoc.com',
    '.vercel.app',
]
# --- Marketplace commission ---
# Seller gets (1 - PLATFORM_COMMISSION_RATE). Default: seller 60% / site 40%.
PLATFORM_COMMISSION_RATE = Decimal(os.getenv("PLATFORM_COMMISSION_RATE", "0.40"))
SELLER_SHARE = Decimal("1.00") - PLATFORM_COMMISSION_RATE

# --- Withdrawals security flags ---
# Keep these disabled during early testing; enable later in production.
WITHDRAWALS_REQUIRE_2FA_FOR_PAYOUT_METHOD = _env_bool("WITHDRAWALS_REQUIRE_2FA_FOR_PAYOUT_METHOD", default=False)
WITHDRAWALS_REQUIRE_2FA_FOR_WITHDRAWALS = _env_bool("WITHDRAWALS_REQUIRE_2FA_FOR_WITHDRAWALS", default=False)
WITHDRAWALS_HOLD_DAYS = _env_int("WITHDRAWALS_HOLD_DAYS", default=14)
# Testing-only: lets you exercise payout flows immediately without waiting for the 14th/28th.
WITHDRAWALS_TEST_FORCE_PAYOUT_DAY = _env_bool("WITHDRAWALS_TEST_FORCE_PAYOUT_DAY", default=False)

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-secret-key"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is required when DEBUG=0")

# --- CSRF Trusted Origins ---
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:14560",
    "https://*.pythonanywhere.com",
    "https://*.vercel.app",
]

# --- Applications ---
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "cloudinary",
    "cloudinary_storage",
    "widget_tweaks",
    "pwa",

    # Local apps
    "accounts",
    "documents", 
    "payments",
    "reviews",
    "sales",
    "security",
    "education",
    "withdrawals",
    "notifications",
    "sharp_student_documents",
]

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # ✅ For static files on Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sharp_student_documents.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "sharp_student_documents.wsgi.application"

# --- Database ---
DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL or DEFAULT_SQLITE_URL,
        conn_max_age=600,
        # Only attach SSL parameters for external databases that support them.
        ssl_require=bool(DATABASE_URL and not DATABASE_URL.startswith("sqlite") and not DEBUG),
    )
}

# --- Authentication ---
AUTH_USER_MODEL = "accounts.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# --- Static & Media ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- Media files (local storage) ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
# Keep Django's upload handlers happy with large numeric limits instead of None.
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 1024  # 1 GB

# --- Cloudinary (media file storage) ---
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY"),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET"),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Configure cloudinary library globally
cloudinary_lib.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

# --- Auth redirects ---
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
LOGIN_URL = "/accounts/login/"  # Use direct URL path
CSRF_FAILURE_VIEW = "sharp_student_documents.views.csrf_failure"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")

# --- Email ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")  # Your personal Gmail address
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  # Your 16-character app password
DEFAULT_FROM_EMAIL = f"SharpDocs <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "SharpDocs <noreply@sharpdocs.com>"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", EMAIL_HOST_USER or "admin@sharpdocs.com")

# For testing, make email fail silently if not configured
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- Stripe ---
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
stripe.api_key = STRIPE_SECRET_KEY

# --- PayPal ---
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # change to "live" in production
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")

# PayPal API Endpoints
PAYPAL_SANDBOX_REST_API = "https://api.sandbox.paypal.com"
PAYPAL_REST_API = "https://api.paypal.com"

# PayPal Payouts Configuration
PAYPAL_PAYOUTS_ENABLED = True
PAYPAL_SANDBOX_PAYOUTS_API = "https://api.sandbox.paypal.com/v1/payments/payouts"
PAYPAL_PAYOUTS_API = "https://api.paypal.com/v1/payments/payouts"

if PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET:
    paypalrestsdk.configure({
        "mode": PAYPAL_MODE,
        "client_id": PAYPAL_CLIENT_ID,
        "client_secret": PAYPAL_CLIENT_SECRET,
    })

# --- Jazzmin Admin ---
JAZZMIN_SETTINGS = {
    "site_title": "SharpDocs Admin",
    "site_header": "SharpDocs Admin",
    "site_brand": "SharpDocs",
    "welcome_sign": "Welcome to SharpDocs Admin",
    "copyright": "SharpDocs 2025",
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index"},
        {"name": "Security Dashboard", "url": "/security/dashboard/", "icon": "fas fa-shield-alt"},
        {"name": "Go to Site", "url": "/", "new_window": True, "icon": "fas fa-home"},
    ],
    "theme": "cyborg",
    "dark_mode_theme": "darkly",
}

# --- PWA Settings (django-pwa reads flat PWA_APP_* settings) ---
PWA_APP_NAME = "SharpDocs"
PWA_APP_DESCRIPTION = "Professional document marketplace with educational tools"
PWA_APP_THEME_COLOR = "#667eea"
PWA_APP_BACKGROUND_COLOR = "#ffffff"
PWA_APP_DISPLAY = "standalone"
PWA_APP_SCOPE = "/"
PWA_APP_ORIENTATION = "portrait-primary"
PWA_APP_START_URL = "/"
PWA_APP_STATUS_BAR_COLOR = "#667eea"
PWA_APP_DEBUG_MODE = DEBUG
PWA_APP_ICONS = [
    {"src": "/static/sharp.png", "sizes": "72x72", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "96x96", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "128x128", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "144x144", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "152x152", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "384x384", "type": "image/png"},
    {"src": "/static/sharp.png", "sizes": "512x512", "type": "image/png"},
]
PWA_APP_ICONS_APPLE = PWA_APP_ICONS
PWA_APP_SHORTCUTS = [
    {
        "name": "Study Planner",
        "short_name": "Planner",
        "description": "Access your study planner",
        "url": "/education/planner/",
        "icons": [{"src": "/static/images/icons/planner-96x96.png", "sizes": "96x96"}],
    },
    {
        "name": "My Documents",
        "short_name": "Docs",
        "description": "View your purchased documents",
        "url": "/documents/my-purchases/",
        "icons": [{"src": "/static/images/icons/docs-96x96.png", "sizes": "96x96"}],
    },
]
PWA_APP_SPLASH_SCREEN = [
    {
        "src": "/static/images/icons/splash-640x1136.png",
        "media": "(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)",
    },
    {
        "src": "/static/images/icons/splash-750x1334.png",
        "media": "(device-width: 375px) and (device-height: 667px) and (-webkit-device-pixel-ratio: 2)",
    },
    {
        "src": "/static/images/icons/splash-1242x2208.png",
        "media": "(device-width: 414px) and (device-height: 736px) and (-webkit-device-pixel-ratio: 3)",
    },
    {
        "src": "/static/images/icons/splash-1125x2436.png",
        "media": "(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)",
    },
]
