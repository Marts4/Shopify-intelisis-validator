"""
Cliente base abstracto para integraciones externas.
Define el contrato que deben cumplir todos los clientes.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import requests
from src.core.models import Order
from src.core.exceptions import IntegrationError
from src.utils import get_logger, retry

logger = get_logger('BASE_CLIENT')


class BaseClient(ABC):
    """
    Clase base abstracta para clientes de integración.
    Proporciona funcionalidad común como retry logic y manejo de errores.
    """

    def __init__(self, name: str):
        """
        Args:
            name: Nombre del cliente para logging
        """
        self.name = name
        self.logger = get_logger(name)

    @retry(max_attempts=3, delay=2.0, exceptions=(requests.RequestException,))
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Realiza una petición HTTP con retry automático.

        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL del endpoint
            **kwargs: Argumentos adicionales para requests

        Returns:
            Response object

        Raises:
            IntegrationError: Si la petición falla después de los reintentos
        """
        try:
            self.logger.api_call(method, url)

            response = requests.request(method, url, **kwargs)

            self.logger.api_call(method, url, response.status_code)

            # Verificar si el status code indica error
            if response.status_code >= 400:
                self._handle_error_response(response)

            return response

        except requests.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}", exc_info=True)
            raise IntegrationError(f"Failed to connect to {self.name}: {str(e)}")

    def _handle_error_response(self, response: requests.Response):
        """
        Maneja respuestas con códigos de error.
        Puede ser sobrescrito por clases hijas para manejo específico.

        Args:
            response: Response con error
        """
        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
        self.logger.error(error_msg)
        raise IntegrationError(error_msg)

    def _validate_response_json(self, response: requests.Response) -> Dict:
        """
        Valida y parsea respuesta JSON.

        Args:
            response: Response a validar

        Returns:
            Diccionario parseado

        Raises:
            IntegrationError: Si el response no es JSON válido
        """
        try:
            return response.json()
        except ValueError as e:
            self.logger.error(f"Invalid JSON response: {str(e)}")
            raise IntegrationError(f"Invalid JSON response from {self.name}")


class BaseEcommerceClient(BaseClient):
    """
    Cliente base específico para plataformas de eCommerce.
    Define el contrato para obtener órdenes.
    """

    @abstractmethod
    def get_orders(self, date: str, financial_status: str):
        """
        Obtiene órdenes de una fecha específica.

        Args:
            date: Fecha en formato YYYY-MM-DD
            financial_status: Estado financiero (ej: 'paid')

        Returns:
            Tuple con (lista de órdenes, lista de datos crudos)
        """
        pass