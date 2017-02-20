from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, SentryMixin, ProdMixin, \
    SecurityMixin, LogMixin, TestMixin, AuthenticationFeatureSwitch


class DevDefaultSite(DevMixin, AuthenticationFeatureSwitch, BaseSettings):
    pass


class TestDefaultSite(TestMixin, DevDefaultSite):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, SecurityMixin, SentryMixin,
                      LogMixin, BaseSettings):
    pass
