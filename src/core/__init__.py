"""
Módulo core con modelos de datos y excepciones.
"""

from .models import (
    Order,
    IntelisisRecord,
    ValidationResult,
    ValidationSummary,
    Difference,
    ValidationStatus,
    DifferenceType
)

from .exceptions import (
    ValidationError,
    ConfigurationError,
    IntegrationError,
    ShopifyAPIError,
    IntelisisAPIError,
    ReportGenerationError,
    EmailSendError,
    DataValidationError
)

__all__ = [
    # Models
    'Order',
    'IntelisisRecord',
    'ValidationResult',
    'ValidationSummary',
    'Difference',
    'ValidationStatus',
    'DifferenceType',
    
    # Exceptions
    'ValidationError',
    'ConfigurationError',
    'IntegrationError',
    'ShopifyAPIError',
    'IntelisisAPIError',
    'ReportGenerationError',
    'EmailSendError',
    'DataValidationError',
]