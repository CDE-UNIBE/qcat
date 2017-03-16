from os.path import join

from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, SentryMixin, ProdMixin, \
    SecurityMixin, LogMixin, TestMixin


class DevDefaultSite(DevMixin, BaseSettings):
    EMAIL_BACKEND = 'eml_email_backend.EmailBackend'
    EMAIL_FILE_PATH = join(BaseSettings.BASE_DIR, 'tmp')


class TestDefaultSite(TestMixin, DevDefaultSite):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, SecurityMixin, SentryMixin,
                      LogMixin, BaseSettings):
    pass
