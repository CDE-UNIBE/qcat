from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, OpBeatMixin, ProdMixin, \
    SecurityMixin, LogMixin, AuthenticationFeatureSwitch


class DevDefaultSite(DevMixin, AuthenticationFeatureSwitch, BaseSettings):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, OpBeatMixin, SecurityMixin, LogMixin, BaseSettings):
    pass
