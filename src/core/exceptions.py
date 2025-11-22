"""
Excepciones personalizadas del sistema.
Facilitan el manejo de errores y mejoran la observabilidad.
"""


class ValidationError(Exception):
    """Error base del sistema de validación"""
    pass


class ConfigurationError(ValidationError):
    """Error en la configuración del sistema"""
    pass


class IntegrationError(ValidationError):
    """Error base para integraciones externas"""
    pass


class ShopifyAPIError(IntegrationError):
    """Error al comunicarse con la API de Shopify"""
    def __init__(self, platform: str, status_code: int, message: str):
        self.platform = platform
        self.status_code = status_code
        self.message = message
        super().__init__(
            f"Shopify API Error [{platform}] - Status {status_code}: {message}"
        )


class IntelisisAPIError(IntegrationError):
    """Error al comunicarse con la API de Intelisis"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(
            f"Intelisis API Error - Status {status_code}: {message}"
        )


class ReportGenerationError(ValidationError):
    """Error al generar reportes"""
    pass


class EmailSendError(ValidationError):
    """Error al enviar correo electrónico"""
    def __init__(self, message: str, recipients: list = None):
        self.recipients = recipients or []
        super().__init__(f"Email Send Error: {message}")


class DataValidationError(ValidationError):
    """Error en la validación de datos"""
    pass