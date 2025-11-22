"""
Punto de entrada principal del sistema de validación.
Orquesta el flujo completo: consulta, validación y reportes.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from src.services import OrchestratorService
from src.reports import ExcelReporter, EmailReporter
from src.utils import get_logger

logger = get_logger('MAIN')


def main():
    """
    Función principal que ejecuta el proceso completo.
    """
    try:
        logger.info("=" * 70)
        logger.info("SISTEMA DE VALIDACIÓN SHOPIFY-INTELISIS v2.0")
        logger.info("=" * 70)
        
        # Paso 1: Ejecutar proceso de validación
        orchestrator = OrchestratorService()
        results, summary, date_description = orchestrator.run()
        
        if not results:
            logger.warning("No hay resultados para reportar")
            logger.info("Proceso finalizado sin generar reportes")
            return
        
        # Paso 2: Generar reporte Excel
        logger.section("PASO 3: GENERANDO REPORTES")
        
        if settings.excel_report.enabled:
            excel_reporter = ExcelReporter()
            excel_success = excel_reporter.generate(results, summary, date_description)
            
            if excel_success:
                logger.info(f"✓ Excel guardado en: {excel_reporter.get_output_path()}")
            else:
                logger.error("✗ Error generando Excel")
        else:
            logger.info("Generación de Excel deshabilitada")
        
        # Paso 3: Enviar reporte por email
        if settings.email_report.enabled:
            email_reporter = EmailReporter()
            email_success = email_reporter.generate(results, summary, date_description)
            
            if email_success:
                logger.info(f"✓ Email enviado a: {', '.join(settings.email_report.recipients)}")
            else:
                logger.error("✗ Error enviando email")
        else:
            logger.info("Envío de email deshabilitado")
        
        # Resumen final
        logger.section("RESUMEN FINAL")
        logger.info(f"📅 Fecha(s): {date_description}")
        logger.info(f"📊 Total órdenes: {summary.total_orders}")
        logger.info(f"✅ Validaciones OK: {summary.ok_count}")
        logger.info(f"⚠️  Con diferencias: {summary.differences_count}")
        logger.info(f"❌ No encontradas: {summary.not_found_count}")
        logger.info(f"📈 Tasa de éxito: {summary.success_rate:.1f}%")
        
        if summary.found_next_day_count > 0:
            logger.info(f"📅 Encontradas día siguiente: {summary.found_next_day_count}")
        
        logger.info("")
        logger.info("Por plataforma:")
        for platform, stats in summary.platform_stats.items():
            logger.info(
                f"  {platform}: {stats['ok']}/{stats['total']} OK "
                f"({stats['differences']} dif, {stats['not_found']} no encontrados)"
            )
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ PROCESO COMPLETADO EXITOSAMENTE")
        logger.info("=" * 70)
        
    except KeyboardInterrupt:
        logger.warning("Proceso interrumpido por el usuario")
        sys.exit(1)
        
    except Exception as e:
        logger.critical(
            f"Error crítico en el proceso principal: {str(e)}",
            exc_info=True
        )
        logger.info("=" * 70)
        logger.info("❌ PROCESO FINALIZADO CON ERRORES")
        logger.info("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()