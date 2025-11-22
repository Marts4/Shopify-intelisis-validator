"""
Clase base abstracta para generadores de reportes.
Implementa el patrón Template Method.
"""

from abc import ABC, abstractmethod
from typing import List
from src.core.models import ValidationResult, ValidationSummary
from src.utils import get_logger


class BaseReporter(ABC):
    """
    Clase base para todos los generadores de reportes.
    Define el flujo común de generación.
    """
    
    def __init__(self, name: str):
        """
        Args:
            name: Nombre del reporter para logging
        """
        self.logger = get_logger(name)
        self.name = name
    
    def generate(
        self, 
        results: List[ValidationResult], 
        summary: ValidationSummary,
        date_description: str
    ) -> bool:
        """
        Genera el reporte siguiendo el patrón Template Method.
        
        Args:
            results: Lista de resultados de validación
            summary: Resumen estadístico
            date_description: Descripción de las fechas procesadas
            
        Returns:
            True si el reporte fue generado exitosamente, False en caso contrario
        """
        try:
            self.logger.info(f"Iniciando generación de reporte: {self.name}")
            
            # Paso 1: Preparación
            self._prepare(results, summary, date_description)
            
            # Paso 2: Creación del reporte (implementado por clases hijas)
            self._create_report(results, summary, date_description)
            
            # Paso 3: Finalización
            self._finalize(results, summary, date_description)
            
            self.logger.info(f"✓ Reporte generado exitosamente: {self.name}")
            return True
            
        except Exception as e:
            self.logger.error(
                f"Error generando reporte {self.name}: {str(e)}",
                exc_info=True
            )
            return False
    
    def _prepare(
        self, 
        results: List[ValidationResult], 
        summary: ValidationSummary,
        date_description: str
    ):
        """
        Preparación antes de generar el reporte.
        Puede ser sobrescrito por clases hijas.
        """
        pass
    
    @abstractmethod
    def _create_report(
        self, 
        results: List[ValidationResult], 
        summary: ValidationSummary,
        date_description: str
    ):
        """
        Método abstracto para crear el reporte.
        Debe ser implementado por clases hijas.
        """
        pass
    
    def _finalize(
        self, 
        results: List[ValidationResult], 
        summary: ValidationSummary,
        date_description: str
    ):
        """
        Finalización después de generar el reporte.
        Puede ser sobrescrito por clases hijas.
        """
        pass