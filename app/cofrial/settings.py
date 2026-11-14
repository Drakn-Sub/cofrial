"""Configuración de Cofrial.

Todo valor sensible o dependiente del entorno se lee desde variables de entorno,
que en AWS se generan a partir de Secrets Manager. Nada secreto vive en el código.
"""
import os
from pathlib import Path

from oscar.defaults import *  # noqa: F401,F403  (configuración base de django-oscar)

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(nombre, defecto="0"):
    return os.environ.get(nombre, defecto).lower() in {"1", "true", "si", "yes"}


SECRET_KEY = os.environ["SECRET_KEY"]  # nunca en el código: viene de Secrets Manager
DEBUG = env_bool("DEBUG")
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

# Un nombre de host por canal (Tabla 6 del informe). Si están vacíos (desarrollo local),
# todas las rutas se sirven en cualquier host.
HOST_TIENDA = os.environ.get("HOST_TIENDA", "")
HOST_CRM = os.environ.get("HOST_CRM", "")
HOST_OPS = os.environ.get("HOST_OPS", "")
REQUIERE_2FA = env_bool("REQUIERE_2FA", "1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.flatpages",
    "django.contrib.humanize",
    # Tienda: django-oscar (BSD). La app "partner" está bifurcada para los precios B2B.
    "oscar.config.Shop",
    "oscar.apps.analytics.apps.AnalyticsConfig",
    "oscar.apps.checkout.apps.CheckoutConfig",
    "oscar.apps.address.apps.AddressConfig",
    "oscar.apps.shipping.apps.ShippingConfig",
    "oscar.apps.catalogue.apps.CatalogueConfig",
    "oscar.apps.catalogue.reviews.apps.CatalogueReviewsConfig",
    "oscar.apps.communication.apps.CommunicationConfig",
    "apps.partner.apps.PartnerConfig",
    "oscar.apps.basket.apps.BasketConfig",
    "oscar.apps.payment.apps.PaymentConfig",
    "oscar.apps.offer.apps.OfferConfig",
    "oscar.apps.order.apps.OrderConfig",
    "oscar.apps.customer.apps.CustomerConfig",
    "oscar.apps.search.apps.SearchConfig",
    "oscar.apps.voucher.apps.VoucherConfig",
    "oscar.apps.wishlists.apps.WishlistsConfig",
    "oscar.apps.dashboard.apps.DashboardConfig",
    "oscar.apps.dashboard.reports.apps.ReportsDashboardConfig",
    "oscar.apps.dashboard.users.apps.UsersDashboardConfig",
    "oscar.apps.dashboard.orders.apps.OrdersDashboardConfig",
    "oscar.apps.dashboard.catalogue.apps.CatalogueDashboardConfig",
    "oscar.apps.dashboard.offers.apps.OffersDashboardConfig",
    "oscar.apps.dashboard.partners.apps.PartnersDashboardConfig",
    "oscar.apps.dashboard.pages.apps.PagesDashboardConfig",
    "oscar.apps.dashboard.ranges.apps.RangesDashboardConfig",
    "oscar.apps.dashboard.reviews.apps.ReviewsDashboardConfig",
    "oscar.apps.dashboard.vouchers.apps.VouchersDashboardConfig",
    "oscar.apps.dashboard.communications.apps.CommunicationsDashboardConfig",
    "oscar.apps.dashboard.shipping.apps.ShippingDashboardConfig",
    "widget_tweaks",
    "haystack",
    "treebeard",
    "sorl.thumbnail",
    "django_tables2",
    # Seguridad
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Desarrollo propio
    "cuentas",
    "crm",
    "logistica",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "cuentas.middleware.EnrutamientoPorHostMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "cuentas.middleware.Requiere2FAMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "cuentas.middleware.AccesoPorRolMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oscar.apps.basket.middleware.BasketMiddleware",
    "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "cofrial.urls"

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
                "oscar.apps.search.context_processors.search_form",
                "oscar.apps.checkout.context_processors.checkout",
                "oscar.apps.communication.notifications.context_processors.notifications",
                "oscar.core.context_processors.metadata",
                "cuentas.roles.contexto",
            ],
        },
    },
]

WSGI_APPLICATION = "cofrial.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "NAME": os.environ.get("DB_NAME", "cofrial"),
        "USER": os.environ.get("DB_USER", "cofrial_app"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "ATOMIC_REQUESTS": True,  # cada solicitud es una transacción (ACID)
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,  # reconecta tras una conmutación Multi-AZ
        "OPTIONS": {
            # Las tablas de Django y Oscar viven en el esquema "comercial".
            "options": "-c search_path=comercial,public",
            # En AWS: verify-full con el certificado de la autoridad de RDS.
            "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
            **({"sslrootcert": os.environ["DB_SSLROOTCERT"]} if os.environ.get("DB_SSLROOTCERT") else {}),
        },
    }
}

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # bloqueo por intentos fallidos
    "oscar.apps.customer.auth_backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Argon2id: hash lento y con sal (recomendación de OWASP)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Fuerza bruta: 5 intentos fallidos por usuario + IP bloquean 1 hora (estado compartido en PostgreSQL)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_CLIENT_IP_CALLABLE = "cuentas.utils.ip_cliente"
AXES_RESET_ON_SUCCESS = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8
CSRF_COOKIE_SAMESITE = "Lax"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
SITE_ID = 1
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
if os.environ.get("MEDIA_BUCKET"):
    # Imágenes en S3 privado; el navegador las recibe con URL firmadas y temporales.
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["MEDIA_BUCKET"],
            "region_name": os.environ.get("AWS_REGION", "us-east-1"),
            "querystring_expire": 3600,
            "file_overwrite": False,
        },
    }
    # sorl-thumbnail (miniaturas de Oscar) instancia la clase de almacenamiento sin OPTIONS:
    # lee la misma configuración desde estas variables globales de django-storages.
    AWS_STORAGE_BUCKET_NAME = os.environ["MEDIA_BUCKET"]
    AWS_S3_REGION_NAME = os.environ.get("AWS_REGION", "us-east-1")
    AWS_QUERYSTRING_EXPIRE = 3600
    AWS_S3_FILE_OVERWRITE = False

HAYSTACK_CONNECTIONS = {"default": {"ENGINE": "haystack.backends.simple_backend.SimpleEngine"}}

# --- django-oscar ---
OSCAR_SHOP_NAME = "Cofrial"
OSCAR_SHOP_TAGLINE = "Cadena de frío de La Araucanía"
OSCAR_DEFAULT_CURRENCY = "CLP"
OSCAR_REQUIRED_ADDRESS_FIELDS = ("first_name", "last_name", "line1", "line4", "country")
OSCAR_ALLOW_ANON_CHECKOUT = False  # todo pedido queda asociado a un cliente identificado
OSCAR_FROM_EMAIL = "no-responder@cofrial.cl"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Estados del pedido (Figura 11 del informe). Oscar rechaza toda transición no listada.
OSCAR_INITIAL_ORDER_STATUS = "Recibido"
OSCAR_INITIAL_LINE_STATUS = "Recibido"
OSCAR_ORDER_STATUS_PIPELINE = {
    "Recibido": ("Pagado", "Anulado"),
    "Pagado": ("En preparación", "Anulado"),
    "En preparación": ("Asignado",),
    "Asignado": ("En ruta",),
    "En ruta": ("Entregado", "En ruta con alerta"),
    "En ruta con alerta": ("En ruta", "Entregado", "Rechazado"),
    "Entregado": (),
    "Rechazado": (),
    "Anulado": (),
}
OSCAR_LINE_STATUS_PIPELINE = OSCAR_ORDER_STATUS_PIPELINE

# --- Seguridad en producción (lo que revisa `manage.py check --deploy`) ---
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # el TLS lo termina el balanceador
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^salud/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if "." in h]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False}},
}

# --- Integración de IA (Fase 10) ---
IA_API_KEY = os.environ.get("IA_API_KEY", "")
IA_MODELO = os.environ.get("IA_MODELO", "gemini-flash-lite-latest")  # liviano y disponible en el plan gratuito
IA_TIMEOUT_SEG = int(os.environ.get("IA_TIMEOUT_SEG", "10"))
# Mapa 3D de la torre de control. Es un token público (pk.) restringido por URL en la cuenta de Mapbox.
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")
