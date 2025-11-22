"""
Modelos de datos inmutables para órdenes, registros y validaciones.
Usa dataclasses para garantizar consistencia y facilitar testing.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    """Estados posibles de una validación"""
    OK = "OK"
    DIFFERENCES = "DIFFERENCES"
    NOT_FOUND = "NOT_FOUND"


class DifferenceType(Enum):
    """Tipos de diferencias detectadas"""
    NAME = "Nombre dif"
    QUANTITY = "Cantidad dif"
    RECORDS = "Registros dif"
    TOTAL = "Total dif"
    COORDINATES = "Coord dif"
    FOUND_NEXT_DAY = "ENCONTRADO DÍA SIGUIENTE"


@dataclass(frozen=True)
class Order:
    """
    Representa una orden de una plataforma eCommerce.
    Inmutable para garantizar integridad de datos.
    """
    platform: str
    order_id: str
    order_number: str
    created_at: str
    financial_status: str
    customer_name: str
    quantity: float
    line_items_count: int
    total: float
    coordinates: str

    def __post_init__(self):
        """Validaciones básicas al crear la orden"""
        if not self.platform:
            raise ValueError("Platform cannot be empty")
        if not self.order_id:
            raise ValueError("Order ID cannot be empty")
        if self.total < 0:
            raise ValueError("Total cannot be negative")

    @property
    def quantity_int(self) -> int:
        """Cantidad como entero si no tiene decimales"""
        return int(self.quantity) if self.quantity == int(self.quantity) else self.quantity

    def to_dict(self) -> dict:
        """Convierte a diccionario para Excel/JSON"""
        return {
            'plataforma': self.platform,
            'id': self.order_id,
            'order_number': self.order_number,
            'created_at': self.created_at,
            'financial_status': self.financial_status,
            'customer_name': self.customer_name,
            'quantity': self.quantity_int,
            'registros': self.line_items_count,
            'total_final': round(self.total, 2),
            'coordinates': self.coordinates
        }


@dataclass(frozen=True)
class IntelisisRecord:
    """
    Representa un registro (o conjunto de registros) de Intelisis
    correspondiente a una orden.
    """
    order_id: str
    branch_id: int
    customer_name: str
    quantity: float
    records_count: int
    total: float
    coordinates: str

    @property
    def quantity_int(self) -> int:
        """Cantidad como entero si no tiene decimales"""
        return int(self.quantity) if self.quantity == int(self.quantity) else self.quantity

    def to_dict(self) -> dict:
        """Convierte a diccionario para Excel/JSON"""
        return {
            'nombre_intelisis': self.customer_name,
            'cantidad_intelisis': self.quantity_int,
            'registros_intelisis': self.records_count,
            'total_intelisis': round(self.total, 3),
            'coordenadas_intelisis': self.coordinates
        }


@dataclass
class Difference:
    """Representa una diferencia específica entre orden e Intelisis"""
    type: DifferenceType
    order_value: any
    intelisis_value: any

    def __str__(self) -> str:
        """Formato legible de la diferencia"""
        if self.type == DifferenceType.FOUND_NEXT_DAY:
            return self.type.value
        
        if self.order_value and self.intelisis_value:
            return f"{self.type.value} ({self.order_value} vs {self.intelisis_value})"
        return self.type.value


@dataclass
class ValidationResult:
    """
    Resultado de validar una orden contra Intelisis.
    Contiene la orden original, el registro de Intelisis (si existe),
    y las diferencias encontradas.
    """
    order: Order
    intelisis: Optional[IntelisisRecord] = None
    differences: List[Difference] = field(default_factory=list)
    found_on_next_day: bool = False

    @property
    def status(self) -> ValidationStatus:
        """Determina el estado basado en las diferencias"""
        if self.intelisis is None:
            return ValidationStatus.NOT_FOUND
        if not self.differences:
            return ValidationStatus.OK
        return ValidationStatus.DIFFERENCES

    @property
    def is_ok(self) -> bool:
        """True si la validación es exitosa"""
        return self.status == ValidationStatus.OK

    @property
    def observations(self) -> str:
        """String con todas las observaciones concatenadas"""
        if self.status == ValidationStatus.NOT_FOUND:
            return "NO ENCONTRADO EN INTELISIS"
        if self.is_ok:
            return "OK"
        return " | ".join(str(diff) for diff in self.differences)

    def to_dict(self) -> dict:
        """
        Convierte a diccionario combinando datos de orden e Intelisis.
        Formato compatible con el Excel original.
        """
        result = self.order.to_dict()
        
        if self.intelisis:
            result.update(self.intelisis.to_dict())
        else:
            result.update({
                'nombre_intelisis': '',
                'cantidad_intelisis': '',
                'registros_intelisis': '',
                'total_intelisis': '',
                'coordenadas_intelisis': ''
            })
        
        result['observaciones'] = self.observations
        
        return result

    def has_difference_type(self, diff_type: DifferenceType) -> bool:
        """Verifica si tiene un tipo específico de diferencia"""
        return any(diff.type == diff_type for diff in self.differences)


@dataclass
class ValidationSummary:
    """
    Resumen estadístico de un conjunto de validaciones.
    Útil para reportes y logging.
    """
    total_orders: int = 0
    ok_count: int = 0
    differences_count: int = 0
    not_found_count: int = 0
    found_next_day_count: int = 0
    
    # Por plataforma
    platform_stats: dict = field(default_factory=dict)

    def add_result(self, result: ValidationResult):
        """Agrega un resultado al resumen"""
        self.total_orders += 1
        
        if result.status == ValidationStatus.OK:
            self.ok_count += 1
        elif result.status == ValidationStatus.NOT_FOUND:
            self.not_found_count += 1
        else:
            self.differences_count += 1
        
        if result.found_on_next_day:
            self.found_next_day_count += 1
        
        # Estadísticas por plataforma
        platform = result.order.platform
        if platform not in self.platform_stats:
            self.platform_stats[platform] = {
                'total': 0,
                'ok': 0,
                'differences': 0,
                'not_found': 0
            }
        
        stats = self.platform_stats[platform]
        stats['total'] += 1
        
        if result.status == ValidationStatus.OK:
            stats['ok'] += 1
        elif result.status == ValidationStatus.NOT_FOUND:
            stats['not_found'] += 1
        else:
            stats['differences'] += 1

    @property
    def success_rate(self) -> float:
        """Porcentaje de validaciones exitosas"""
        if self.total_orders == 0:
            return 0.0
        return (self.ok_count / self.total_orders) * 100

    def to_dict(self) -> dict:
        """Convierte a diccionario para reportes"""
        return {
            'total_orders': self.total_orders,
            'ok_count': self.ok_count,
            'differences_count': self.differences_count,
            'not_found_count': self.not_found_count,
            'found_next_day_count': self.found_next_day_count,
            'success_rate': round(self.success_rate, 2),
            'platform_stats': self.platform_stats
        }

    def __str__(self) -> str:
        """Formato legible del resumen"""
        lines = [
            f"Total órdenes: {self.total_orders}",
            f"✅ OK: {self.ok_count}",
            f"⚠️ Con diferencias: {self.differences_count}",
            f"❌ No encontrados: {self.not_found_count}",
            f"📅 Encontrados día siguiente: {self.found_next_day_count}",
            f"Tasa de éxito: {self.success_rate:.1f}%"
        ]
        
        if self.platform_stats:
            lines.append("\nPor plataforma:")
            for platform, stats in self.platform_stats.items():
                lines.append(
                    f"  {platform}: {stats['total']} total "
                    f"({stats['ok']} OK, {stats['differences']} dif, "
                    f"{stats['not_found']} no encontrados)"
                )
        
        return "\n".join(lines)