from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, ProdMixin, SecurityMixin, \
    LogMixin, TestMixin, MetricsMixin


class DevDefaultSite(DevMixin, BaseSettings):
    pass


class TestDefaultSite(TestMixin, DevDefaultSite):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin,  LogMixin, BaseSettings):
    """
    Settings for live and demo hosting.
    """
    pass


class ProdDevDefaultSite(ProdDefaultSite):
    """
    Settings for qcat-dev hosting.
    """
    pass
