from .config.common import BaseSettings
from .config.mixins import CompressMixin, DevMixin, OpBeatMixin, ProdMixin, \
    SecurityMixin


class DevDefaultSite(DevMixin, BaseSettings):
    pass


class ProdDefaultSite(ProdMixin, CompressMixin, OpBeatMixin, SecurityMixin,
                      BaseSettings):
    pass
