from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, \
    OpBeatMixin, ProdMixin, SecurityMixin, LogMixin


class DevDefaultSite(DevMixin, BaseSettings):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, OpBeatMixin, SecurityMixin,
                      BaseSettings):
    pass
