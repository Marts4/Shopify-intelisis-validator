"""
Módulo de configuración del proyecto.
Exporta el singleton de configuración y clases relacionadas.
"""

from .settings import (
    settings,
    Settings,
    PlatformConfig,
    IntelisisConfig,
    ValidationConfig,
    ExecutionConfig,
    ExcelReportConfig,
    EmailReportConfig,
    LoggingConfig,
    BASE_DIR,
    CONFIG_DIR,
    LOGS_DIR,
    OUTPUT_DIR
)

__all__ = [
    'settings',
    'Settings',
    'PlatformConfig',
    'IntelisisConfig',
    'ValidationConfig',
    'ExecutionConfig',
    'ExcelReportConfig',
    'EmailReportConfig',
    'LoggingConfig',
    'BASE_DIR',
    'CONFIG_DIR',
    'LOGS_DIR',
    'OUTPUT_DIR'
]