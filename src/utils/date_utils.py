"""
Utilidades para manejo de fechas.
Centraliza la lógica de fechas manuales vs automáticas.
"""

from datetime import datetime, timedelta
from typing import List, Tuple
from config import settings
from .logger import get_logger

logger = get_logger('DATE_UTILS')


def get_target_dates() -> Tuple[List[str], str]:
    """
    Obtiene las fechas objetivo según la configuración.
    
    Returns:
        Tuple con:
        - Lista de fechas a consultar (formato YYYY-MM-DD)
        - String descriptivo para logs/reportes
    
    Ejemplos:
        Modo manual: (["2025-10-24"], "2025-10-24")
        Modo auto: (["2025-11-04", "2025-11-05"], "2025-11-04 / 2025-11-05")
    """
    
    if settings.execution.is_manual_mode:
        # Modo manual: fecha específica
        if not settings.execution.manual_date:
            raise ValueError("Modo manual activado pero no se especificó manual_date")
        
        dates = [settings.execution.manual_date]
        description = settings.execution.manual_date
        
        logger.info(f"Modo MANUAL: {description}")
    
    else:
        # Modo automático: ayer + hoy
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        dates = [
            yesterday.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        ]
        description = f"{dates[0]} / {dates[1]}"
        
        logger.info(f"Modo AUTOMÁTICO: {description}")
    
    return dates, description


def get_next_day(date_str: str) -> str:
    """
    Obtiene el día siguiente a una fecha.
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
    
    Returns:
        Fecha del día siguiente en formato YYYY-MM-DD
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    next_day = date_obj + timedelta(days=1)
    return next_day.strftime("%Y-%m-%d")


def format_shopify_datetime(date_str: str, time: str = "00:00:00") -> str:
    """
    Formatea una fecha para consultas de Shopify API.
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
        time: Hora en formato HH:MM:SS (default: 00:00:00)
    
    Returns:
        Fecha formateada con timezone: YYYY-MM-DDTHH:MM:SS-06:00
    """
    return f"{date_str}T{time}-06:00"


def get_shopify_date_range(date_str: str) -> Tuple[str, str]:
    """
    Obtiene el rango completo de un día para consultas Shopify.
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
    
    Returns:
        Tuple (start_datetime, end_datetime) formateados para Shopify
    """
    start = format_shopify_datetime(date_str, "00:00:00")
    end = format_shopify_datetime(date_str, "23:59:59")
    return start, end


def format_display_datetime(iso_datetime: str) -> str:
    """
    Formatea un datetime ISO para mostrar de forma legible.
    
    Args:
        iso_datetime: Fecha en formato ISO 8601
    
    Returns:
        Fecha formateada: YYYY-MM-DD HH:MM:SS
    """
    try:
        # Parsear datetime ISO con timezone
        if 'T' in iso_datetime:
            # Remover timezone info para simplificar
            dt_str = iso_datetime.split('+')[0].split('-06:00')[0]
            dt = datetime.fromisoformat(dt_str.replace('Z', ''))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return iso_datetime
    except Exception:
        return iso_datetime


def get_current_timestamp() -> str:
    """
    Obtiene timestamp actual formateado.
    
    Returns:
        Timestamp: YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")