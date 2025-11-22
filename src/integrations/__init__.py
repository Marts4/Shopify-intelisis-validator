"""
Módulo de integraciones con sistemas externos.
"""

from .base_client import BaseClient, BaseEcommerceClient
from .shopify_client import ShopifyClient
from .intelisis_client import IntelisisClient

__all__ = [
    'BaseClient',
    'BaseEcommerceClient',
    'ShopifyClient',
    'IntelisisClient',
]