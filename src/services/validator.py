"""
Servicio para validar órdenes contra registros de Intelisis.
Implementa reglas de validación y detección de diferencias.
"""

from typing import List, Dict, Optional
from config import settings
from src.core.models import (
    Order,
    IntelisisRecord,
    ValidationResult,
    ValidationSummary,
    Difference,
    DifferenceType
)
from src.integrations import IntelisisClient
from src.utils import get_logger, timing, get_next_day


class ValidatorService:
    """
    Servicio para validar órdenes de Shopify contra registros de Intelisis.
    Detecta diferencias y genera resultados de validación.
    """

    def __init__(self, raw_data_reporter=None):
        self.logger = get_logger('VALIDATOR')
        self.intelisis_client = IntelisisClient()
        self.tolerance = settings.validation.tolerance_amount
        self.raw_data_reporter = raw_data_reporter

    @timing(operation_name="Validate All Orders")
    def validate_orders(
            self,
            orders: List[Order],
            dates: List[str],
            check_next_day: bool = True
    ) -> List[ValidationResult]:
        """
        Valida todas las órdenes contra Intelisis.

        Args:
            orders: Lista de órdenes a validar
            dates: Fechas consultadas (para búsqueda en día siguiente)
            check_next_day: Si True, busca en día siguiente órdenes no encontradas

        Returns:
            Lista de resultados de validación
        """
        if not orders:
            self.logger.warning("No hay órdenes para validar")
            return []

        self.logger.section("VALIDANDO ÓRDENES CONTRA INTELISIS")

        # Paso 1: Obtener datos de Intelisis
        branch_ids = self._get_branch_ids_from_orders(orders)
        intelisis_data = self._fetch_intelisis_data(dates, branch_ids)

        if not intelisis_data:
            self.logger.warning("No se encontraron datos en Intelisis")
            return self._create_not_found_results(orders)

        # Paso 2: Indexar datos de Intelisis por orden
        intelisis_index = self._index_intelisis_data(intelisis_data)

        # Paso 3: Validar cada orden
        results = self._validate_against_index(orders, intelisis_index)

        # Paso 4: Buscar en día siguiente si es necesario
        if check_next_day and len(dates) == 1:  # Solo en modo manual con una fecha
            results = self._check_next_day_for_missing(
                results,
                dates[0],
                branch_ids
            )

        # Paso 5: Log de resumen
        self._log_validation_summary(results)

        return results

    def _get_branch_ids_from_orders(self, orders: List[Order]) -> List[int]:
        """
        Extrae los IDs de sucursal únicos de las órdenes.

        Args:
            orders: Lista de órdenes

        Returns:
            Lista de branch_ids únicos
        """
        platforms = set(order.platform for order in orders)
        branch_ids = []

        for platform_name in platforms:
            platform_config = settings.get_platform_by_name(platform_name)
            if platform_config:
                branch_ids.append(platform_config.branch_id)

        return branch_ids

    def _fetch_intelisis_data(
            self,
            dates: List[str],
            branch_ids: List[int]
    ) -> List[Dict]:
        """
        Obtiene datos de Intelisis para las fechas especificadas.

        Args:
            dates: Lista de fechas
            branch_ids: Lista de branch_ids a filtrar

        Returns:
            Lista de registros crudos
        """
        all_data = []

        for date in dates:
            self.logger.info(f"Consultando Intelisis para: {date}")

            try:
                # Obtener datos filtrados
                data = self.intelisis_client.fetch_data(date, branch_ids)

                # Guardar datos crudos inmediatamente después de obtenerlos
                if self.raw_data_reporter and data:
                    try:
                        self.raw_data_reporter.save_intelisis_raw_data(data, date)
                    except Exception as e:
                        self.logger.error(f"Error guardando datos crudos Intelisis: {str(e)}")

                all_data.extend(data)

            except Exception as e:
                self.logger.error(
                    f"Error consultando Intelisis ({date}): {str(e)}",
                    exc_info=True
                )

        return all_data

    def _index_intelisis_data(
            self,
            raw_data: List[Dict]
    ) -> Dict[tuple, IntelisisRecord]:
        """
        Indexa datos de Intelisis por (order_id, branch_id).

        Args:
            raw_data: Lista de registros crudos

        Returns:
            Diccionario {(order_id, branch_id): IntelisisRecord}
        """
        # Agrupar registros por orden
        grouped = self.intelisis_client.group_by_order_id(raw_data)

        # Convertir a IntelisisRecord
        index = {}
        for (order_id, branch_id), records in grouped.items():
            try:
                intelisis_record = self.intelisis_client.parse_to_intelisis_record(
                    order_id,
                    records
                )
                index[(order_id, branch_id)] = intelisis_record
            except Exception as e:
                self.logger.warning(
                    f"Error parseando registros para orden {order_id}: {str(e)}"
                )

        self.logger.info(f"Índice creado: {len(index)} órdenes únicas en Intelisis")

        return index

    def _validate_against_index(
            self,
            orders: List[Order],
            intelisis_index: Dict[tuple, IntelisisRecord]
    ) -> List[ValidationResult]:
        """
        Valida cada orden contra el índice de Intelisis.

        Args:
            orders: Lista de órdenes
            intelisis_index: Índice de registros de Intelisis

        Returns:
            Lista de resultados de validación
        """
        results = []

        for order in orders:
            result = self._validate_single_order(order, intelisis_index)
            results.append(result)

            # Log individual de validación
            self.logger.validation_result(
                order_id=order.order_id,
                status=result.status.value,
                platform=order.platform
            )

        return results

    def _validate_single_order(
            self,
            order: Order,
            intelisis_index: Dict[tuple, IntelisisRecord]
    ) -> ValidationResult:
        """
        Valida una orden individual.

        Args:
            order: Orden a validar
            intelisis_index: Índice de Intelisis

        Returns:
            Resultado de validación
        """
        # Obtener branch_id de la plataforma
        platform_config = settings.get_platform_by_name(order.platform)
        if not platform_config:
            self.logger.warning(
                f"Plataforma {order.platform} no encontrada en configuración",
                platform=order.platform
            )
            return ValidationResult(order=order)

        branch_id = platform_config.branch_id
        key = (order.order_id, branch_id)

        # Buscar en Intelisis
        intelisis_record = intelisis_index.get(key)

        if not intelisis_record:
            # No encontrado
            return ValidationResult(order=order)

        # Encontrado: comparar y detectar diferencias
        differences = self._detect_differences(order, intelisis_record)

        return ValidationResult(
            order=order,
            intelisis=intelisis_record,
            differences=differences
        )

    def _detect_differences(
            self,
            order: Order,
            intelisis: IntelisisRecord
    ) -> List[Difference]:
        """
        Detecta diferencias entre orden e Intelisis.

        Args:
            order: Orden de Shopify
            intelisis: Registro de Intelisis

        Returns:
            Lista de diferencias encontradas
        """
        differences = []

        # Comparar nombre
        if order.customer_name != intelisis.customer_name:
            differences.append(Difference(
                type=DifferenceType.NAME,
                order_value=order.customer_name,
                intelisis_value=intelisis.customer_name
            ))

        # Comparar cantidad
        if order.quantity != intelisis.quantity:
            differences.append(Difference(
                type=DifferenceType.QUANTITY,
                order_value=order.quantity,
                intelisis_value=intelisis.quantity
            ))

        # Comparar número de registros
        if order.line_items_count != intelisis.records_count:
            differences.append(Difference(
                type=DifferenceType.RECORDS,
                order_value=order.line_items_count,
                intelisis_value=intelisis.records_count
            ))

        # Comparar total (con tolerancia)
        if abs(order.total - intelisis.total) > self.tolerance:
            differences.append(Difference(
                type=DifferenceType.TOTAL,
                order_value=round(order.total, 2),
                intelisis_value=round(intelisis.total, 3)
            ))

        # Comparar coordenadas
        if order.coordinates != intelisis.coordinates:
            differences.append(Difference(
                type=DifferenceType.COORDINATES,
                order_value=order.coordinates,
                intelisis_value=intelisis.coordinates
            ))

        return differences

    def _check_next_day_for_missing(
            self,
            results: List[ValidationResult],
            original_date: str,
            branch_ids: List[int]
    ) -> List[ValidationResult]:
        """
        Busca en el día siguiente las órdenes no encontradas.
        Solo aplica en modo manual con fecha única.

        Args:
            results: Resultados de validación
            original_date: Fecha original consultada
            branch_ids: IDs de sucursales

        Returns:
            Resultados actualizados
        """
        # Filtrar órdenes no encontradas
        not_found = [r for r in results if r.intelisis is None]

        if not not_found:
            self.logger.info("No hay órdenes no encontradas para buscar en día siguiente")
            return results

        self.logger.subsection(
            f"Buscando {len(not_found)} órdenes no encontradas en día siguiente"
        )

        # Obtener día siguiente
        next_date = get_next_day(original_date)
        self.logger.info(f"Consultando: {next_date}")

        # Obtener datos del día siguiente
        try:
            next_day_data = self.intelisis_client.fetch_data(next_date, branch_ids)

            if not next_day_data:
                self.logger.info("No hay datos en el día siguiente")
                return results

            # Indexar datos del día siguiente
            next_day_index = self._index_intelisis_data(next_day_data)

            # Re-validar órdenes no encontradas
            updated_results = []
            found_count = 0

            for result in results:
                if result.intelisis is None:
                    # Re-validar contra día siguiente
                    new_result = self._validate_single_order(
                        result.order,
                        next_day_index
                    )

                    if new_result.intelisis is not None:
                        # Encontrado en día siguiente
                        new_result.found_on_next_day = True
                        new_result.differences.append(Difference(
                            type=DifferenceType.FOUND_NEXT_DAY,
                            order_value=None,
                            intelisis_value=None
                        ))
                        found_count += 1

                        self.logger.info(
                            f"✓ Orden {result.order.order_id} encontrada en día siguiente",
                            platform=result.order.platform,
                            order_id=result.order.order_id
                        )

                    updated_results.append(new_result)
                else:
                    updated_results.append(result)

            self.logger.info(
                f"Encontradas {found_count}/{len(not_found)} órdenes en día siguiente"
            )

            return updated_results

        except Exception as e:
            self.logger.error(
                f"Error consultando día siguiente: {str(e)}",
                exc_info=True
            )
            return results

    def _create_not_found_results(self, orders: List[Order]) -> List[ValidationResult]:
        """
        Crea resultados de validación para órdenes sin datos de Intelisis.

        Args:
            orders: Lista de órdenes

        Returns:
            Lista de resultados marcados como NO_FOUND
        """
        return [ValidationResult(order=order) for order in orders]

    def _log_validation_summary(self, results: List[ValidationResult]):
        """
        Registra resumen de validaciones.

        Args:
            results: Lista de resultados
        """
        summary = ValidationSummary()

        for result in results:
            summary.add_result(result)

        self.logger.subsection("Resumen de Validación")
        self.logger.info(str(summary))

    def get_summary(self, results: List[ValidationResult]) -> ValidationSummary:
        """
        Genera resumen estadístico de validaciones.

        Args:
            results: Lista de resultados

        Returns:
            Objeto ValidationSummary
        """
        summary = ValidationSummary()

        for result in results:
            summary.add_result(result)

        return summary