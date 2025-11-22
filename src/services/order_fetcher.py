"""
Servicio para obtener órdenes de múltiples plataformas.
Coordina clientes de Shopify y maneja concurrencia.
"""

from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import settings
from src.core.models import Order
from src.core.exceptions import IntegrationError
from src.integrations import ShopifyClient
from src.utils import get_logger, timing


class OrderFetcherService:
    """
    Servicio para obtener órdenes de todas las plataformas configuradas.
    Soporta consultas paralelas para mejorar performance.
    """

    def __init__(self, raw_data_reporter=None):
        self.logger = get_logger('ORDER_FETCHER')
        self._clients = {}
        self.raw_data_reporter = raw_data_reporter
        self._initialize_clients()

    def _initialize_clients(self):
        """Inicializa clientes para cada plataforma habilitada"""
        for platform_config in settings.enabled_platforms:
            try:
                client = ShopifyClient(platform_config)
                self._clients[platform_config.name] = client
                self.logger.info(
                    f"Cliente inicializado para {platform_config.name}",
                    platform=platform_config.name
                )
            except Exception as e:
                self.logger.error(
                    f"Error inicializando cliente {platform_config.name}: {str(e)}",
                    platform=platform_config.name,
                    exc_info=True
                )
                raise

    @timing(operation_name="Fetch All Orders")
    def fetch_all_orders(
            self,
            dates: List[str],
            financial_status: str = None,
            parallel: bool = False
    ) -> List[Order]:
        """
        Obtiene órdenes de todas las plataformas para las fechas especificadas.

        Args:
            dates: Lista de fechas en formato YYYY-MM-DD
            financial_status: Estado financiero (default: desde settings)
            parallel: Si True, consulta plataformas en paralelo

        Returns:
            Lista consolidada de órdenes de todas las plataformas
        """
        if financial_status is None:
            financial_status = settings.validation.financial_status

        self.logger.section("OBTENIENDO ÓRDENES DE SHOPIFY")
        self.logger.info(f"Fechas a consultar: {', '.join(dates)}")
        self.logger.info(f"Estado financiero: {financial_status}")
        self.logger.info(f"Plataformas: {len(self._clients)}")

        all_orders = []

        if parallel and len(self._clients) > 1:
            # Modo paralelo: más rápido pero más complejo
            all_orders = self._fetch_parallel(dates, financial_status)
        else:
            # Modo secuencial: más simple y predecible
            all_orders = self._fetch_sequential(dates, financial_status)

        self._log_summary(all_orders)

        return all_orders

    def _fetch_sequential(
            self,
            dates: List[str],
            financial_status: str
    ) -> List[Order]:
        """
        Obtiene órdenes secuencialmente por plataforma y fecha.

        Args:
            dates: Lista de fechas
            financial_status: Estado financiero

        Returns:
            Lista de órdenes
        """
        all_orders = []

        for date in dates:
            self.logger.subsection(f"Consultando fecha: {date}")

            date_raw_data = []

            for platform_name, client in self._clients.items():
                try:
                    self.logger.info(
                        f"Consultando {platform_name}...",
                        platform=platform_name
                    )

                    # Obtener órdenes Y datos crudos
                    orders, raw_data = client.get_orders(date, financial_status)
                    all_orders.extend(orders)
                    date_raw_data.extend(raw_data)

                    self.logger.info(
                        f"✓ {platform_name}: {len(orders)} órdenes obtenidas",
                        platform=platform_name
                    )

                except Exception as e:
                    self.logger.error(
                        f"✗ Error en {platform_name}: {str(e)}",
                        platform=platform_name,
                        exc_info=True
                    )
                    # Continuar con otras plataformas aunque falle una
                    continue

            # Guardar datos crudos de esta fecha
            if self.raw_data_reporter and date_raw_data:
                try:
                    self.raw_data_reporter.save_shopify_raw_data(date_raw_data, date)
                except Exception as e:
                    self.logger.error(f"Error guardando datos crudos Shopify: {str(e)}")

        return all_orders

    def _fetch_parallel(
            self,
            dates: List[str],
            financial_status: str
    ) -> List[Order]:
        """
        Obtiene órdenes en paralelo usando ThreadPoolExecutor.
        Más rápido pero requiere manejo cuidadoso de errores.

        Args:
            dates: Lista de fechas
            financial_status: Estado financiero

        Returns:
            Lista de órdenes
        """
        all_orders = []

        # Crear tareas: una por cada combinación (plataforma, fecha)
        tasks = []
        for date in dates:
            for platform_name, client in self._clients.items():
                tasks.append((platform_name, client, date, financial_status))

        self.logger.info(f"Ejecutando {len(tasks)} tareas en paralelo")

        # Ejecutar en paralelo (máximo 4 workers para no saturar APIs)
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as executor:
            # Submit todas las tareas
            future_to_task = {
                executor.submit(
                    self._fetch_single,
                    platform_name,
                    client,
                    date,
                    financial_status
                ): (platform_name, date)
                for platform_name, client, date, financial_status in tasks
            }

            # Procesar resultados conforme completan
            for future in as_completed(future_to_task):
                platform_name, date = future_to_task[future]

                try:
                    orders = future.result()
                    all_orders.extend(orders)

                    self.logger.info(
                        f"✓ {platform_name} ({date}): {len(orders)} órdenes",
                        platform=platform_name
                    )

                except Exception as e:
                    self.logger.error(
                        f"✗ Error en {platform_name} ({date}): {str(e)}",
                        platform=platform_name,
                        exc_info=True
                    )

        return all_orders

    def _fetch_single(
            self,
            platform_name: str,
            client: ShopifyClient,
            date: str,
            financial_status: str
    ) -> List[Order]:
        """
        Obtiene órdenes de una plataforma en una fecha.
        Método auxiliar para ejecución paralela.

        Args:
            platform_name: Nombre de la plataforma
            client: Cliente de Shopify
            date: Fecha a consultar
            financial_status: Estado financiero

        Returns:
            Lista de órdenes
        """
        return client.get_orders(date, financial_status)

    def _log_summary(self, orders: List[Order]):
        """
        Registra resumen de órdenes obtenidas.

        Args:
            orders: Lista de órdenes
        """
        if not orders:
            self.logger.warning("No se obtuvieron órdenes")
            return

        # Contar por plataforma
        platform_counts = {}
        for order in orders:
            platform = order.platform
            platform_counts[platform] = platform_counts.get(platform, 0) + 1

        self.logger.subsection("Resumen de Órdenes Obtenidas")

        for platform, count in sorted(platform_counts.items()):
            self.logger.info(f"  {platform}: {count} órdenes", platform=platform)

        self.logger.info(f"  TOTAL: {len(orders)} órdenes")

    def get_orders_by_platform(self, orders: List[Order]) -> Dict[str, List[Order]]:
        """
        Agrupa órdenes por plataforma.

        Args:
            orders: Lista de órdenes

        Returns:
            Diccionario {platform_name: [orders]}
        """
        grouped = {}

        for order in orders:
            if order.platform not in grouped:
                grouped[order.platform] = []
            grouped[order.platform].append(order)

        return grouped