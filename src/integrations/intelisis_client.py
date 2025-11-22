"""
Cliente para la API de Intelisis.
Obtiene y procesa registros de ventas por día.
"""

from typing import List, Dict, Optional, Set
from config import settings
from src.core.models import IntelisisRecord
from src.core.exceptions import IntelisisAPIError
from src.utils import get_logger, timing
from .base_client import BaseClient


class IntelisisClient(BaseClient):
    """
    Cliente para consultar registros de Intelisis.
    Maneja paginación y filtrado de datos.
    """
    
    def __init__(self):
        """Inicializa el cliente con configuración desde settings"""
        super().__init__("INTELISIS")
        
        if not settings.intelisis.auth_token:
            raise ValueError("Token de Intelisis no configurado")
        
        self.base_url = settings.intelisis.base_url
        self.page_limit = settings.intelisis.page_limit
        
        self.headers = {
            'Authorization': settings.intelisis.auth_token,
            'Cookie': settings.intelisis.cookie
        }
    
    @timing(operation_name="Intelisis: Fetch Data")
    def fetch_data(self, date: str, branch_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Obtiene todos los registros de Intelisis para una fecha.
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            branch_ids: Lista de IDs de sucursales a filtrar (None = todas)
            
        Returns:
            Lista de registros crudos de Intelisis
        """
        self.logger.info(f"Consultando Intelisis para el día: {date}")
        
        if branch_ids:
            self.logger.info(f"Filtrando por sucursales: {branch_ids}")
        
        all_records = []
        page = 1
        
        while True:
            self.logger.debug(f"Consultando página {page}...")
            
            # Obtener datos de la página
            page_records = self._fetch_page(date, page)
            
            if not page_records:
                self.logger.debug(f"Página {page} sin datos")
                break
            
            # Filtrar registros según criterios
            filtered_records = self._filter_records(
                page_records, 
                branch_ids
            )
            
            all_records.extend(filtered_records)
            
            self.logger.info(
                f"Página {page}: {len(filtered_records)}/{len(page_records)} registros válidos"
            )
            
            # Verificar si hay más páginas
            if len(page_records) < self.page_limit:
                break
            
            page += 1
        
        self.logger.info(f"Total registros obtenidos: {len(all_records)}")
        
        # Log de distribución por sucursal
        self._log_branch_distribution(all_records)
        
        return all_records
    
    def _fetch_page(self, date: str, page: int) -> List[Dict]:
        """
        Obtiene una página de registros.
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            page: Número de página
            
        Returns:
            Lista de registros
        """
        url = f"{self.base_url}?dia={date}&limit={self.page_limit}&page={page}"
        
        try:
            response = self._make_request(
                method='GET',
                url=url,
                headers=self.headers,
                timeout=30
            )
            
            data = self._validate_response_json(response)
            
            # Normalizar estructura de respuesta
            # La API puede retornar diferentes formatos
            if isinstance(data, dict):
                if 'data' in data:
                    records = data['data']
                elif 'results' in data:
                    records = data['results']
                elif 'items' in data:
                    records = data['items']
                else:
                    records = []
            elif isinstance(data, list):
                records = data
            else:
                self.logger.warning(f"Formato de respuesta inesperado: {type(data)}")
                records = []
            
            if not isinstance(records, list):
                self.logger.warning(f"Se esperaba lista pero se recibió: {type(records)}")
                return []
            
            return records
            
        except Exception as e:
            self.logger.error(f"Error obteniendo página {page}: {str(e)}", exc_info=True)
            raise IntelisisAPIError(
                status_code=getattr(e, 'status_code', 0),
                message=str(e)
            )
    
    def _filter_records(
        self, 
        records: List[Dict], 
        branch_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Filtra registros según criterios de negocio.
        
        Args:
            records: Lista de registros crudos
            branch_ids: IDs de sucursales permitidas (None = todas)
            
        Returns:
            Lista de registros filtrados
        """
        filtered = []
        
        for record in records:
            if not isinstance(record, dict):
                continue
            
            # Filtro 1: Sucursal
            if branch_ids:
                record_branch = record.get('Sucursal')
                if record_branch not in branch_ids:
                    continue
            
            # Filtro 2: Tipo de movimiento
            movement = str(record.get('Mov', '')).strip()
            if movement not in settings.intelisis.valid_movements:
                continue
            
            # Filtro 3: Total positivo
            if settings.intelisis.filter_positive_totals:
                total_neto = record.get('vtcTotalNeto', 0)
                try:
                    if total_neto is None or float(total_neto) <= 0:
                        continue
                except (ValueError, TypeError):
                    continue
            
            filtered.append(record)
        
        return filtered
    
    def _log_branch_distribution(self, records: List[Dict]):
        """
        Registra la distribución de registros por sucursal.
        
        Args:
            records: Lista de registros
        """
        if not records:
            return
        
        branch_counts = {}
        for record in records:
            branch = record.get('Sucursal')
            branch_counts[branch] = branch_counts.get(branch, 0) + 1
        
        self.logger.subsection("Distribución por Sucursal")
        for branch, count in sorted(branch_counts.items()):
            # Obtener nombre de la plataforma
            platform = self._get_platform_name_by_branch(branch)
            self.logger.info(f"  Sucursal {branch} ({platform}): {count} registros")
    
    def _get_platform_name_by_branch(self, branch_id: int) -> str:
        """
        Obtiene el nombre de la plataforma por ID de sucursal.
        
        Args:
            branch_id: ID de la sucursal
            
        Returns:
            Nombre de la plataforma o "OTRA"
        """
        for platform in settings.platforms:
            if platform.branch_id == branch_id:
                return platform.name
        return "OTRA"
    
    def group_by_order_id(self, records: List[Dict]) -> Dict[tuple, List[Dict]]:
        """
        Agrupa registros por ID de orden y sucursal.
        
        Args:
            records: Lista de registros crudos
            
        Returns:
            Diccionario donde key=(order_id, branch_id) y value=lista de registros
        """
        grouped = {}
        
        for record in records:
            order_id = str(record.get('Adicional5', '')).strip()
            branch_id = record.get('Sucursal')
            
            if not order_id:
                continue
            
            key = (order_id, branch_id)
            
            if key not in grouped:
                grouped[key] = []
            
            grouped[key].append(record)
        
        self.logger.debug(f"Registros agrupados: {len(grouped)} órdenes únicas")
        
        return grouped
    
    def parse_to_intelisis_record(
        self, 
        order_id: str, 
        records: List[Dict]
    ) -> IntelisisRecord:
        """
        Convierte un grupo de registros en un objeto IntelisisRecord.
        
        Args:
            order_id: ID de la orden
            records: Lista de registros de Intelisis para esta orden
            
        Returns:
            Objeto IntelisisRecord con datos agregados
        """
        if not records:
            raise ValueError("No se pueden parsear registros vacíos")
        
        # Tomar datos comunes del primer registro
        first_record = records[0]
        
        customer_name = first_record.get('NombreCliente', '')
        branch_id = first_record.get('Sucursal', 0)
        coordinates = first_record.get('Adicional2', '')
        
        # Agregar cantidades y totales
        total_quantity = 0
        total_amount = 0
        
        for record in records:
            quantity = record.get('Cantidad', 0)
            if quantity is not None:
                total_quantity += float(quantity)
            
            total_neto = record.get('vtcTotalNeto', 0)
            if total_neto is not None:
                total_amount += float(total_neto)
        
        return IntelisisRecord(
            order_id=order_id,
            branch_id=branch_id,
            customer_name=customer_name if customer_name else '',
            quantity=total_quantity,
            records_count=len(records),
            total=total_amount,
            coordinates=coordinates if coordinates else ''
        )
    
    def _handle_error_response(self, response):
        """
        Manejo específico de errores de Intelisis.
        
        Args:
            response: Response con error
        """
        status_code = response.status_code
        
        if status_code == 401:
            error_msg = "Token de autenticación inválido o expirado"
        elif status_code == 403:
            error_msg = "Acceso denegado. Verificar permisos"
        elif status_code == 404:
            error_msg = "Endpoint no encontrado"
        else:
            error_msg = f"HTTP {status_code}: {response.text[:200]}"
        
        self.logger.error(error_msg)
        raise IntelisisAPIError(
            status_code=status_code,
            message=error_msg
        )