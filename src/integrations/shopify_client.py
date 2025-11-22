"""
Cliente para la API de Shopify.
Maneja paginación, rate limiting y conversión de datos a modelos.
"""

from typing import List, Dict, Optional
import time
from config import settings, PlatformConfig
from src.core.models import Order
from src.core.exceptions import ShopifyAPIError
from src.utils import get_logger, timing, get_shopify_date_range
from .base_client import BaseEcommerceClient


class ShopifyClient(BaseEcommerceClient):
    """
    Cliente para consultar órdenes de Shopify.
    Soporta paginación basada en cursores y manejo de rate limits.
    """

    # Configuración de rate limiting
    MAX_REQUESTS_PER_SECOND = 2
    ORDERS_PER_PAGE = 250

    def __init__(self, platform_config: PlatformConfig):
        """
        Args:
            platform_config: Configuración de la plataforma desde settings
        """
        super().__init__(f"SHOPIFY_{platform_config.name}")
        self.config = platform_config
        self.logger = get_logger(f"SHOPIFY")

        if not self.config.token:
            raise ValueError(f"Token no configurado para {self.config.name}")

        self.base_url = f"https://{self.config.shop}/admin/api/{self.config.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.config.token
        }

        # Control de rate limiting
        self._last_request_time = 0

    @timing(operation_name="Shopify: Fetch Orders")
    def get_orders(self, date: str, financial_status: str = None) -> tuple[List[Order], List[Dict]]:
        """
        Obtiene todas las órdenes de una fecha específica.
        Maneja paginación automáticamente.

        Args:
            date: Fecha en formato YYYY-MM-DD
            financial_status: Estado financiero (default: desde settings)

        Returns:
            Tuple con:
            - Lista de órdenes parseadas como objetos Order
            - Lista de datos crudos (diccionarios originales de la API)
        """
        if financial_status is None:
            financial_status = settings.validation.financial_status

        start_date, end_date = get_shopify_date_range(date)

        self.logger.info(
            f"Consultando órdenes del {date}",
            platform=self.config.name
        )

        all_orders = []
        all_raw_data = []
        page_info = None
        page = 1

        while True:
            self.logger.debug(
                f"Consultando página {page}...",
                platform=self.config.name,
                operation="PAGINATION"
            )

            # Obtener órdenes de la página actual
            orders_data, next_page_info = self._fetch_orders_page(
                start_date=start_date,
                end_date=end_date,
                financial_status=financial_status,
                page_info=page_info
            )

            if not orders_data:
                self.logger.debug(
                    f"Página {page} sin datos",
                    platform=self.config.name
                )
                break

            # Guardar datos crudos
            all_raw_data.extend(orders_data)

            # Convertir datos crudos a objetos Order
            parsed_orders = [
                self._parse_order(order_data)
                for order_data in orders_data
            ]

            all_orders.extend(parsed_orders)

            self.logger.info(
                f"Página {page}: {len(parsed_orders)} órdenes obtenidas",
                platform=self.config.name
            )

            # Verificar si hay más páginas
            if not next_page_info:
                break

            page_info = next_page_info
            page += 1

            # Rate limiting: esperar entre páginas
            self._respect_rate_limit()

        self.logger.info(
            f"Total obtenido: {len(all_orders)} órdenes",
            platform=self.config.name
        )

        return all_orders, all_raw_data

    def fetch_data(self, *args, **kwargs):
        """
        Método requerido por BaseClient (no usado directamente).
        ShopifyClient usa get_orders() en su lugar.
        """
        raise NotImplementedError("Use get_orders() instead of fetch_data()")

    def _fetch_orders_page(
            self,
            start_date: str,
            end_date: str,
            financial_status: str,
            page_info: Optional[str] = None
    ) -> tuple[List[Dict], Optional[str]]:
        """
        Obtiene una página de órdenes.

        Args:
            start_date: Fecha inicio (formato ISO)
            end_date: Fecha fin (formato ISO)
            financial_status: Estado financiero
            page_info: Token de paginación (None para primera página)

        Returns:
            Tuple con (lista de órdenes, page_info para siguiente página)
        """
        url = f"{self.base_url}/orders.json"

        # ⭐⭐⭐ CORRECCIÓN IMPORTANTE ⭐⭐⭐
        # Cuando Shopify regresa page_info, NO puedes enviar financial_status, status ni fechas.
        if page_info:
            params = {
                "limit": self.ORDERS_PER_PAGE,
                "page_info": page_info
            }
        else:
            params = {
                "financial_status": financial_status,
                "status": settings.validation.order_status,
                "limit": self.ORDERS_PER_PAGE,
                "created_at_min": start_date,
                "created_at_max": end_date
            }

        try:
            response = self._make_request(
                method='GET',
                url=url,
                headers=self.headers,
                params=params,
                timeout=30
            )

            data = self._validate_response_json(response)
            orders = data.get('orders', [])

            # Extraer page_info del header Link para siguiente página
            next_page_info = self._extract_next_page_info(response)

            return orders, next_page_info

        except Exception as e:
            self.logger.error(
                f"Error obteniendo página: {str(e)}",
                platform=self.config.name,
                exc_info=True
            )
            raise ShopifyAPIError(
                platform=self.config.name,
                status_code=getattr(e, 'status_code', 0),
                message=str(e)
            )

    def _extract_next_page_info(self, response) -> Optional[str]:
        """
        Extrae el page_info del header Link para paginación.

        Args:
            response: Response de Shopify

        Returns:
            page_info string o None si no hay más páginas
        """
        link_header = response.headers.get('Link', '')

        if 'rel="next"' not in link_header:
            return None

        try:
            # Parsear el header Link
            links = [link.strip() for link in link_header.split(',')]
            next_link = [link for link in links if 'rel="next"' in link][0]

            page_info = next_link.split('page_info=')[1].split('>')[0]
            return page_info

        except (IndexError, AttributeError) as e:
            self.logger.warning(
                f"No se pudo extraer page_info del header Link: {str(e)}",
                platform=self.config.name
            )
            return None

    def _parse_order(self, order_data: Dict) -> Order:
        """
        Convierte datos crudos de Shopify a objeto Order.
        """
        customer = order_data.get('customer', {})
        if customer:
            first_name = customer.get('first_name', '').strip()
            last_name = customer.get('last_name', '').strip()
            customer_name = f"{first_name} {last_name}".strip().upper()
        else:
            customer_name = ''

        shipping_address = order_data.get('shipping_address', {})
        coordinates = ''
        if shipping_address:
            lat = str(shipping_address.get('latitude', '')).strip()
            lon = str(shipping_address.get('longitude', '')).strip()
            if lat and lon:
                coordinates = f"{lat},{lon}".replace(" ", "")

        line_items = order_data.get('line_items', [])
        total_quantity = sum(float(item.get('quantity', 0)) for item in line_items)

        return Order(
            platform=self.config.name,
            order_id=str(order_data.get('id', '')),
            order_number=str(order_data.get('order_number', '')),
            created_at=order_data.get('created_at', ''),
            financial_status=order_data.get('financial_status', ''),
            customer_name=customer_name,
            quantity=total_quantity,
            line_items_count=len(line_items),
            total=float(order_data.get('total_price', 0)),
            coordinates=coordinates
        )

    def _respect_rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        min_interval = 1.0 / self.MAX_REQUESTS_PER_SECOND

        if time_since_last_request < min_interval:
            sleep_time = min_interval - time_since_last_request
            self.logger.debug(
                f"Rate limiting: esperando {sleep_time:.2f}s",
                platform=self.config.name
            )
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _handle_error_response(self, response):
        status_code = response.status_code

        if status_code == 429:
            retry_after = response.headers.get('Retry-After', '5')
            self.logger.warning(
                f"Rate limit excedido. Reintentando después de {retry_after}s",
                platform=self.config.name
            )
            time.sleep(int(retry_after))
            return

        elif status_code == 401:
            error_msg = "Token de autenticación inválido"

        elif status_code == 404:
            error_msg = "Endpoint no encontrado"

        else:
            error_msg = f"HTTP {status_code}: {response.text[:200]}"

        self.logger.error(error_msg, platform=self.config.name)
        raise ShopifyAPIError(
            platform=self.config.name,
            status_code=status_code,
            message=error_msg
        )
