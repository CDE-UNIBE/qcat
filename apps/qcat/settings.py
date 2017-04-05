from os.path import join

from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, SentryMixin, ProdMixin, \
    SecurityMixin, LogMixin, TestMixin


class DevDefaultSite(DevMixin, BaseSettings):
    pass


class TestDefaultSite(TestMixin, DevDefaultSite):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, SecurityMixin, SentryMixin,
                      LogMixin, BaseSettings):
    pass
