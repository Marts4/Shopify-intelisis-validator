"""
Sistema de logging centralizado con rotación automática.
Proporciona logs estructurados con contexto (plataforma, operación, etc.)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional
from config import settings


class ColoredFormatter(logging.Formatter):
    """
    Formatter con colores para consola.
    Mejora la legibilidad en desarrollo.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Agregar color al nivel
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


class ContextFilter(logging.Filter):
    """
    Filtro que agrega contexto adicional a los logs.
    Permite agregar información como plataforma, orden_id, etc.
    """
    
    def filter(self, record):
        # Agregar atributos por defecto si no existen
        if not hasattr(record, 'platform'):
            record.platform = '-'
        if not hasattr(record, 'order_id'):
            record.order_id = '-'
        if not hasattr(record, 'operation'):
            record.operation = '-'
        return True


class AppLogger:
    """
    Logger principal de la aplicación.
    Singleton que configura logging a archivo y consola.
    """
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self):
        """Configura el sistema de logging"""
        
        # Crear directorio de logs si no existe
        log_dir = settings.logging.full_log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar nivel de logging
        log_level = getattr(logging, settings.logging.level.upper(), logging.INFO)
        
        # Configurar logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Limpiar handlers existentes
        root_logger.handlers.clear()
        
        # === HANDLER PARA ARCHIVO ===
        log_file = log_dir / f"validation_{datetime.now().strftime('%Y%m%d')}.log"
        
        if settings.logging.rotation == "daily":
            file_handler = TimedRotatingFileHandler(
                filename=log_file,
                when='midnight',
                interval=1,
                backupCount=settings.logging.retention_days,
                encoding='utf-8'
            )
        else:
            # Rotación por tamaño (10MB por archivo)
            file_handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=10*1024*1024,
                backupCount=settings.logging.retention_days,
                encoding='utf-8'
            )
        
        file_handler.setLevel(log_level)
        
        # Formato detallado para archivo
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(platform)-8s | %(operation)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(ContextFilter())
        
        # === HANDLER PARA CONSOLA ===
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        
        # Formato más simple y con colores para consola
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(platform)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(ContextFilter())
        
        # Agregar handlers al logger raíz
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Silenciar logs verbosos de librerías externas
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        
        self._log_startup_info()
    
    def _log_startup_info(self):
        """Registra información inicial del sistema"""
        logger = self.get_logger('SYSTEM')
        logger.info("=" * 70)
        logger.info("Sistema de Validación Shopify-Intelisis iniciado")
        logger.info(f"Nivel de logging: {settings.logging.level}")
        logger.info(f"Directorio de logs: {settings.logging.full_log_dir}")
        logger.info(f"Plataformas habilitadas: {len(settings.enabled_platforms)}")
        for platform in settings.enabled_platforms:
            logger.info(f"  - {platform.name} (Branch: {platform.branch_id})")
        logger.info("=" * 70)
    
    def get_logger(self, name: str = 'APP') -> 'ContextLogger':
        """
        Obtiene un logger con contexto.
        
        Args:
            name: Nombre del logger (ej: 'SHOPIFY', 'INTELISIS', 'VALIDATOR')
        
        Returns:
            ContextLogger con métodos mejorados
        """
        if name not in self._loggers:
            self._loggers[name] = ContextLogger(name)
        return self._loggers[name]


class ContextLogger:
    """
    Logger con soporte para contexto adicional.
    Permite agregar plataforma, orden, operación, etc.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _log(self, level: int, msg: str, platform: Optional[str] = None, 
             order_id: Optional[str] = None, operation: Optional[str] = None,
             exc_info: bool = False):
        """Método interno para logging con contexto"""
        extra = {
            'platform': platform or '-',
            'order_id': order_id or '-',
            'operation': operation or self.name
        }
        self.logger.log(level, msg, extra=extra, exc_info=exc_info)
    
    def debug(self, msg: str, platform: Optional[str] = None, 
              order_id: Optional[str] = None, operation: Optional[str] = None):
        """Log nivel DEBUG"""
        self._log(logging.DEBUG, msg, platform, order_id, operation)
    
    def info(self, msg: str, platform: Optional[str] = None, 
             order_id: Optional[str] = None, operation: Optional[str] = None):
        """Log nivel INFO"""
        self._log(logging.INFO, msg, platform, order_id, operation)
    
    def warning(self, msg: str, platform: Optional[str] = None, 
                order_id: Optional[str] = None, operation: Optional[str] = None):
        """Log nivel WARNING"""
        self._log(logging.WARNING, msg, platform, order_id, operation)
    
    def error(self, msg: str, platform: Optional[str] = None, 
              order_id: Optional[str] = None, operation: Optional[str] = None,
              exc_info: bool = False):
        """Log nivel ERROR"""
        self._log(logging.ERROR, msg, platform, order_id, operation, exc_info)
    
    def critical(self, msg: str, platform: Optional[str] = None, 
                 order_id: Optional[str] = None, operation: Optional[str] = None,
                 exc_info: bool = False):
        """Log nivel CRITICAL"""
        self._log(logging.CRITICAL, msg, platform, order_id, operation, exc_info)
    
    def exception(self, msg: str, platform: Optional[str] = None, 
                  order_id: Optional[str] = None, operation: Optional[str] = None):
        """Log de excepción con stack trace"""
        self._log(logging.ERROR, msg, platform, order_id, operation, exc_info=True)
    
    def section(self, title: str):
        """Crea una sección visual en los logs"""
        separator = "=" * 70
        self.info(separator)
        self.info(f"  {title}")
        self.info(separator)
    
    def subsection(self, title: str):
        """Crea una subsección visual en los logs"""
        separator = "-" * 70
        self.info(separator)
        self.info(f"  {title}")
        self.info(separator)
    
    def progress(self, current: int, total: int, item_name: str = "items",
                 platform: Optional[str] = None):
        """Log de progreso"""
        percentage = (current / total * 100) if total > 0 else 0
        self.info(
            f"Progreso: {current}/{total} {item_name} ({percentage:.1f}%)",
            platform=platform
        )
    
    def api_call(self, method: str, url: str, status_code: Optional[int] = None,
                 platform: Optional[str] = None):
        """Log específico para llamadas API"""
        if status_code:
            self.debug(
                f"API {method} {url} → {status_code}",
                platform=platform,
                operation="API_CALL"
            )
        else:
            self.debug(
                f"API {method} {url}",
                platform=platform,
                operation="API_CALL"
            )
    
    def validation_result(self, order_id: str, status: str, platform: str):
        """Log específico para resultados de validación"""
        if status == "OK":
            self.debug(
                f"Order {order_id}: ✓ Validación exitosa",
                platform=platform,
                order_id=order_id,
                operation="VALIDATION"
            )
        elif status == "NOT_FOUND":
            self.warning(
                f"Order {order_id}: ⚠ No encontrado en Intelisis",
                platform=platform,
                order_id=order_id,
                operation="VALIDATION"
            )
        else:
            self.warning(
                f"Order {order_id}: ⚠ Diferencias detectadas",
                platform=platform,
                order_id=order_id,
                operation="VALIDATION"
            )
    
    def summary(self, summary_dict: dict, platform: Optional[str] = None):
        """Log de resumen con formato estructurado"""
        self.subsection("Resumen de Ejecución")
        for key, value in summary_dict.items():
            self.info(f"  {key}: {value}", platform=platform)


# Instancia global del sistema de logging
app_logger = AppLogger()


# Funciones de conveniencia para acceso rápido
def get_logger(name: str = 'APP') -> ContextLogger:
    """
    Obtiene un logger con contexto.
    
    Uso:
        from src.utils.logger import get_logger
        logger = get_logger('SHOPIFY')
        logger.info("Mensaje", platform="ROOMI")
    """
    return app_logger.get_logger(name)