"""
Django settings for catalog project.

Generated by 'django-admin startproject' using Django 2.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

from pathlib import Path
from socket import gethostbyname, gethostname

import sentry_sdk
from decouple import config
from sentry_sdk.integrations.django import DjangoIntegration


# Build paths inside the project like this: BASE_DIR.join('dir', 'subdir'...)
BASE_DIR = Path(__file__).resolve().parent.parent

# Where to collect static files in production/development deployments
STATIC_ROOT = "/var/api_static_content/static"

# Logo uploads
MEDIA_ROOT = "/var/api_media/"
MEDIA_URL = "/media/"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("DJANGO_SECRET_KEY")  # required

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DJANGO_DEBUG_ENABLED", default=False, cast=bool)

ALLOWED_HOSTS = [
    "api-dev.openverse.engineering",
    "api.openverse.engineering",
    gethostname(),
    gethostbyname(gethostname()),
]

if lb_url := config("LOAD_BALANCER_URL", default=""):
    ALLOWED_HOSTS.append(lb_url)

if DEBUG:
    ALLOWED_HOSTS += [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    ]

# Domains that shortened links may point to
SHORT_URL_WHITELIST = {
    "api-dev.openverse.engineering",
    "api.openverse.engineering",
    "localhost:8000",
}
SHORT_URL_PATH_WHITELIST = ["/v1/list", "/v1/images/"]

USE_S3 = config("USE_S3", default=False, cast=bool)

# Application definition

INSTALLED_APPS = [
    "catalog",
    "catalog.api",
    "drf_yasg",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "oauth2_provider",
    "rest_framework",
    "corsheaders",
    "sslserver",
]

if USE_S3:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_STORAGE_BUCKET_NAME = config("LOGOS_BUCKET", default="openverse_api-logos-prod")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    INSTALLED_APPS.append("storages")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
]

SWAGGER_SETTINGS = {"SECURITY_DEFINITIONS": {}}

OAUTH2_PROVIDER = {
    "SCOPES": {
        "read": "Read scope",
        "write": "Write scope",
    }
}

OAUTH2_PROVIDER_APPLICATION_MODEL = "api.ThrottledApplication"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_xml.renderers.XMLRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "catalog.api.utils.throttle.BurstRateThrottle",
        "catalog.api.utils.throttle.SustainedRateThrottle",
        "catalog.api.utils.throttle.OAuth2IdThrottleSustainedRate",
        "catalog.api.utils.throttle.OAuth2IdThrottleBurstRate",
        "catalog.api.utils.throttle.EnhancedOAuth2IdThrottleSustainedRate",
        "catalog.api.utils.throttle.EnhancedOAuth2IdThrottleBurstRate",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon_burst": "60/min",
        "anon_sustained": "5000/day",
        "oauth2_client_credentials_sustained": "10000/day",
        "oauth2_client_credentials_burst": "100/min",
        "enhanced_oauth2_client_credentials_sustained": "20000/day",
        "enhanced_oauth2_client_credentials_burst": "200/min",
    },
    "EXCEPTION_HANDLER": "catalog.api.utils.exceptions.exception_handler",
}

if config("DISABLE_GLOBAL_THROTTLING", default=True, cast=bool):
    del REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    del REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]

REDIS_HOST = config("REDIS_HOST", default="localhost")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)
REDIS_PASSWORD = config("REDIS_PASSWORD", default="")
CACHES = {
    # Site cache writes to 'default'
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    # For rapidly changing stats that we don't want to hammer the database with
    "traffic_stats": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
    # For ensuring consistency among multiple Django workers and servers.
    # Used by Redlock.
    "locks": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

# Produce CC-hosted thumbnails dynamically through a proxy.
THUMBNAIL_PROXY_URL = config("THUMBNAIL_PROXY_URL", default="http://localhost:8222")

THUMBNAIL_WIDTH_PX = 600

AUTHENTICATION_BACKENDS = (
    "oauth2_provider.backends.OAuth2Backend",
    "django.contrib.auth.backends.ModelBackend",
)

ROOT_URLCONF = "catalog.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.joinpath("catalog", "templates")],
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

WSGI_APPLICATION = "catalog.wsgi.application"

# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": config("DJANGO_DATABASE_HOST", default="localhost"),
        "PORT": config("DJANGO_DATABASE_PORT", default=5432, cast=int),
        "USER": config("DJANGO_DATABASE_USER", default="deploy"),
        "PASSWORD": config("DJANGO_DATABASE_PASSWORD", default="deploy"),
        "NAME": config("DJANGO_DATABASE_NAME", default="openledger"),
    },
    "upstream": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": config("UPSTREAM_DATABASE_HOST", default="localhost"),
        "PORT": config("UPSTREAM_DATABASE_PORT", default=5433, cast=int),
        "USER": config("UPSTREAM_DATABASE_USER", default="deploy"),
        "PASSWORD": config("UPSTREAM_DATABASE_PASSWORD", default="deploy"),
        "NAME": config("UPSTREAM_DATABASE_NAME", default="openledger"),
    },
}

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation"
        ".UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation" ".MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation" ".CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation" ".NumericPasswordValidator",
    },
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        # root logger
        "": {
            "level": "INFO",
            "handlers": ["console"],
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = "/static/"

# Allow anybody to access the API from any domain
CORS_ORIGIN_ALLOW_ALL = True

# The version of the API. We follow the semantic version specification.
API_VERSION = config("SEMANTIC_VERSION", default="Version not specified")

# The contact email of the Openverse team
CONTACT_EMAIL = config("CONTACT_EMAIL", default="openverse@wordpress.org")

WATERMARK_ENABLED = config("WATERMARK_ENABLED", default=False, cast=bool)

ELASTICSEARCH_URL = config("ELASTICSEARCH_URL", default="localhost")
ELASTICSEARCH_PORT = config("ELASTICSEARCH_PORT", default=9200, cast=int)
ELASTICSEARCH_AWS_REGION = config("ELASTICSEARCH_AWS_REGION", default="us-east-1")

# Additional settings for dev/prod environments
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")

EMAIL_SENDER = config("EMAIL_SENDER", default="")
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_SUBJECT_PREFIX = "[noreply]"
EMAIL_USE_TLS = True

if EMAIL_HOST_USER or EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Log full Elasticsearch response
VERBOSE_ES_RESPONSE = config("DEBUG_SCORES", default=False, cast=bool)

# Whether to boost results by authority and popularity
USE_RANK_FEATURES = config("USE_RANK_FEATURES", default=True, cast=bool)

SENTRY_DSN = config(
    "SENTRY_DSN",
    default="https://08f4706d16004f57bcd37eb907bfc2e7@o787041.ingest.sentry.io/6107216",
)
SENTRY_SAMPLE_RATE = config("SENTRY_SAMPLE_RATE", default=1.0, cast=float)

if not DEBUG:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=SENTRY_SAMPLE_RATE,
        send_default_pii=False,
    )
