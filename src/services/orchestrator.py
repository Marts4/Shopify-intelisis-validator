"""
Servicio orquestador que coordina el flujo completo de validación.
Este es el punto de entrada principal para ejecutar el proceso.
"""

from typing import List, Optional
from pathlib import Path
from config import settings
from src.core.models import ValidationResult, ValidationSummary
from src.utils import get_logger, timing, get_target_dates, get_current_timestamp
from .order_fetcher import OrderFetcherService
from .validator import ValidatorService


class OrchestratorService:
    """
    Orquestador principal del sistema de validación.
    Coordina todos los servicios y el flujo de ejecución.
    """

    def __init__(self):
        self.logger = get_logger('ORCHESTRATOR')

        # Importar RawDataReporter aquí para evitar imports circulares
        from src.reports import RawDataReporter
        self.raw_data_reporter = RawDataReporter()

        # Pasar el reporter a los servicios
        self.order_fetcher = OrderFetcherService(raw_data_reporter=self.raw_data_reporter)
        self.validator = ValidatorService(raw_data_reporter=self.raw_data_reporter)

    @timing(operation_name="Complete Validation Process")
    def run(
            self,
            dates: Optional[List[str]] = None,
            financial_status: Optional[str] = None
    ) -> tuple[List[ValidationResult], ValidationSummary, str]:
        """
        Ejecuta el proceso completo de validación.

        Args:
            dates: Lista de fechas a consultar (None = desde configuración)
            financial_status: Estado financiero (None = desde configuración)

        Returns:
            Tuple con:
            - Lista de ValidationResult
            - ValidationSummary con estadísticas
            - String descriptivo de las fechas procesadas
        """
        try:
            # Inicializar proceso
            self._log_startup()

            # Paso 1: Determinar fechas
            if dates is None:
                dates, date_description = get_target_dates()
            else:
                date_description = ", ".join(dates)

            self.logger.info(f"Fechas objetivo: {date_description}")

            # Paso 2: Obtener órdenes de Shopify
            self.logger.section("PASO 1: OBTENIENDO ÓRDENES DE SHOPIFY")
            orders = self.order_fetcher.fetch_all_orders(
                dates=dates,
                financial_status=financial_status,
                parallel=False  # Cambiar a True para modo paralelo
            )

            if not orders:
                self.logger.warning("No se encontraron órdenes en ninguna plataforma")
                return [], ValidationSummary(), date_description

            self.logger.info(f"✓ Total órdenes obtenidas: {len(orders)}")

            # Paso 3: Validar contra Intelisis
            self.logger.section("PASO 2: VALIDANDO CONTRA INTELISIS")

            # Determinar si buscar en día siguiente (solo modo manual)
            check_next_day = settings.execution.is_manual_mode and len(dates) == 1

            results = self.validator.validate_orders(
                orders=orders,
                dates=dates,
                check_next_day=check_next_day
            )

            # Paso 4: Generar resumen
            summary = self.validator.get_summary(results)

            # Log final
            self._log_completion(summary)

            # Log de archivos de datos crudos generados
            self._log_raw_data_files()

            return results, summary, date_description

        except Exception as e:
            self.logger.critical(
                f"Error crítico en proceso de validación: {str(e)}",
                exc_info=True
            )
            raise

    def _log_startup(self):
        """Registra información inicial del proceso"""
        self.logger.section("INICIO DE VALIDACIÓN SHOPIFY-INTELISIS")

        info = {
            'Timestamp': get_current_timestamp(),
            'Modo': 'MANUAL' if settings.execution.is_manual_mode else 'AUTOMÁTICO',
            'Plataformas habilitadas': len(settings.enabled_platforms),
            'Estado financiero': settings.validation.financial_status,
            'Tolerancia en totales': f"${settings.validation.tolerance_amount}"
        }

        for key, value in info.items():
            self.logger.info(f"{key}: {value}")

        # Listar plataformas
        self.logger.info("Plataformas:")
        for platform in settings.enabled_platforms:
            self.logger.info(
                f"  - {platform.name} (Sucursal: {platform.branch_id})",
                platform=platform.name
            )

    def _log_completion(self, summary: ValidationSummary):
        """
        Registra información final del proceso.

        Args:
            summary: Resumen de validaciones
        """
        self.logger.section("PROCESO COMPLETADO")

        self.logger.info(f"Total órdenes procesadas: {summary.total_orders}")
        self.logger.info(f"✅ Validaciones OK: {summary.ok_count}")
        self.logger.info(f"⚠️  Con diferencias: {summary.differences_count}")
        self.logger.info(f"❌ No encontradas: {summary.not_found_count}")

        if summary.found_next_day_count > 0:
            self.logger.info(
                f"📅 Encontradas día siguiente: {summary.found_next_day_count}"
            )

        self.logger.info(f"Tasa de éxito: {summary.success_rate:.1f}%")

        # Detalle por plataforma
        if summary.platform_stats:
            self.logger.subsection("Detalle por Plataforma")
            for platform, stats in summary.platform_stats.items():
                self.logger.info(
                    f"{platform}: {stats['ok']}/{stats['total']} OK "
                    f"({stats['differences']} dif, {stats['not_found']} no encontrados)",
                    platform=platform
                )

    def _log_raw_data_files(self):
        """Registra información sobre los archivos de datos crudos generados"""
        try:
            summary = self.raw_data_reporter.get_summary()

            # Verificar que summary tenga datos
            if not summary or (not summary.get('shopify') and not summary.get('intelisis')):
                return

            self.logger.subsection("Archivos de Datos Crudos Generados")

            # Shopify files
            shopify_files = summary.get('shopify', [])
            if shopify_files and isinstance(shopify_files, list):
                self.logger.info(f"📄 Archivos Shopify generados: {len(shopify_files)}")
                for file_info in shopify_files:
                    if isinstance(file_info, dict):
                        filename = Path(file_info.get('path', '')).name
                        records = file_info.get('records', 0)
                        date = file_info.get('date', '')
                        self.logger.info(
                            f"   - {filename}: {records} órdenes (Fecha: {date})"
                        )

            # Intelisis files
            intelisis_files = summary.get('intelisis', [])
            if intelisis_files and isinstance(intelisis_files, list):
                self.logger.info(f"📄 Archivos Intelisis generados: {len(intelisis_files)}")
                for file_info in intelisis_files:
                    if isinstance(file_info, dict):
                        filename = Path(file_info.get('path', '')).name
                        records = file_info.get('records', 0)
                        date = file_info.get('date', '')
                        self.logger.info(
                            f"   - {filename}: {records} registros (Fecha: {date})"
                        )

        except Exception as e:
            self.logger.warning(f"No se pudo generar resumen de archivos crudos: {str(e)}")

    def get_execution_info(self) -> dict:
        """
        Obtiene información sobre la configuración de ejecución.

        Returns:
            Diccionario con información de configuración
        """
        dates, date_description = get_target_dates()

        return {
            'dates': dates,
            'date_description': date_description,
            'mode': 'manual' if settings.execution.is_manual_mode else 'automatic',
            'platforms': [p.name for p in settings.enabled_platforms],
            'financial_status': settings.validation.financial_status,
            'reports_enabled': {
                'excel': settings.excel_report.enabled,
                'email': settings.email_report.enabled
            }
        }