"""
Módulo de configuración centralizada.
Carga configuraciones desde JSON y variables de entorno.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

# Rutas base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
LOGS_DIR = BASE_DIR / "logs"
OUTPUT_DIR = BASE_DIR / "output"


@dataclass
class PlatformConfig:
    """Configuración de una plataforma de eCommerce"""
    name: str
    enabled: bool
    shop: str
    branch_id: int
    api_version: str
    token: str
    admin_shop_name: str = None  # Nombre personalizado para URLs de admin

    @property
    def token_env_key(self) -> str:
        """Nombre de la variable de entorno para el token"""
        return f"SHOPIFY_TOKEN_{self.name.upper()}"

    @property
    def shopify_admin_name(self) -> str:
        """Nombre para usar en URLs de Shopify admin"""
        if self.admin_shop_name:
            return self.admin_shop_name
        # Extraer automáticamente del shop (ej: "roomi-mexico.myshopify.com" -> "roomi-mexico")
        return self.shop.split('.')[0]

@dataclass
class IntelisisConfig:
    """Configuración del cliente Intelisis"""
    base_url: str
    page_limit: int
    valid_movements: List[str]
    filter_positive_totals: bool
    auth_token: str
    cookie: str


@dataclass
class ValidationConfig:
    """Configuración de reglas de validación"""
    financial_status: str
    order_status: str
    tolerance_amount: float


@dataclass
class ExecutionConfig:
    """Configuración de ejecución"""
    date_mode: str  # "manual" o "automatic"
    manual_date: Optional[str]
    timezone: str

    @property
    def is_manual_mode(self) -> bool:
        return self.date_mode.lower() == "manual"


@dataclass
class ExcelReportConfig:
    """Configuración de reportes Excel"""
    enabled: bool
    output_path: str

    @property
    def full_output_path(self) -> Path:
        """Ruta completa del archivo de salida"""
        if Path(self.output_path).is_absolute():
            return Path(self.output_path)
        return BASE_DIR / self.output_path


@dataclass
class EmailReportConfig:
    """Configuración de reportes por email"""
    enabled: bool
    smtp_server: str
    smtp_port: int
    sender: str
    recipients: List[str]
    password: str


@dataclass
class LoggingConfig:
    """Configuración de logging"""
    level: str
    log_dir: str
    rotation: str
    retention_days: int

    @property
    def full_log_dir(self) -> Path:
        """Ruta completa del directorio de logs"""
        if Path(self.log_dir).is_absolute():
            return Path(self.log_dir)
        return BASE_DIR / self.log_dir


class Settings:
    """
    Clase principal de configuración.
    Singleton que carga y valida todas las configuraciones.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Carga configuración desde JSON y variables de entorno"""
        config_path = CONFIG_DIR / "platforms.json"
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Archivo de configuración no encontrado: {config_path}"
            )

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        # Plataformas
        self.platforms: List[PlatformConfig] = []
        for platform_data in config_data.get("platforms", []):
            token_key = f"SHOPIFY_TOKEN_{platform_data['name'].upper()}"
            token = os.getenv(token_key)
            
            if not token and platform_data.get("enabled", True):
                raise ValueError(
                    f"Token no encontrado para {platform_data['name']}. "
                    f"Variable de entorno requerida: {token_key}"
                )
            
            self.platforms.append(PlatformConfig(
                name=platform_data["name"],
                enabled=platform_data.get("enabled", True),
                shop=platform_data["shop"],
                branch_id=platform_data["branch_id"],
                api_version=platform_data["api_version"],
                token=token or "",
                admin_shop_name=platform_data.get("admin_shop_name")
            ))

        # Intelisis
        intelisis_data = config_data.get("intelisis", {})
        self.intelisis = IntelisisConfig(
            base_url=intelisis_data["base_url"],
            page_limit=intelisis_data.get("page_limit", 10000),
            valid_movements=intelisis_data.get("valid_movements", ["Pedido"]),
            filter_positive_totals=intelisis_data.get("filter_positive_totals", True),
            auth_token=os.getenv("INTELISIS_AUTH_TOKEN", ""),
            cookie=os.getenv("INTELISIS_COOKIE", "")
        )

        if not self.intelisis.auth_token:
            raise ValueError("INTELISIS_AUTH_TOKEN no configurado en .env")

        # Validación
        validation_data = config_data.get("validation", {})
        self.validation = ValidationConfig(
            financial_status=validation_data.get("financial_status", "paid"),
            order_status=validation_data.get("order_status", "any"),
            tolerance_amount=validation_data.get("tolerance_amount", 1.0)
        )

        # Ejecución
        execution_data = config_data.get("execution", {})
        self.execution = ExecutionConfig(
            date_mode=execution_data.get("date_mode", "manual"),
            manual_date=execution_data.get("manual_date"),
            timezone=execution_data.get("timezone", "America/Mexico_City")
        )

        # Reportes
        reports_data = config_data.get("reports", {})
        
        excel_data = reports_data.get("excel", {})
        self.excel_report = ExcelReportConfig(
            enabled=excel_data.get("enabled", True),
            output_path=excel_data.get("output_path", "output/consulta_validacion.xlsx")
        )

        email_data = reports_data.get("email", {})
        self.email_report = EmailReportConfig(
            enabled=email_data.get("enabled", True),
            smtp_server=email_data.get("smtp_server", "smtp.gmail.com"),
            smtp_port=email_data.get("smtp_port", 587),
            sender=email_data.get("sender", ""),
            recipients=email_data.get("recipients", []),
            password=os.getenv("EMAIL_PASSWORD", "")
        )

        if self.email_report.enabled and not self.email_report.password:
            raise ValueError("EMAIL_PASSWORD no configurado en .env")

        # Logging
        logging_data = config_data.get("logging", {})
        self.logging = LoggingConfig(
            level=logging_data.get("level", "INFO"),
            log_dir=logging_data.get("log_dir", "logs"),
            rotation=logging_data.get("rotation", "daily"),
            retention_days=logging_data.get("retention_days", 30)
        )

        # Crear directorios necesarios
        self._create_directories()

    def _create_directories(self):
        """Crea los directorios necesarios si no existen"""
        self.logging.full_log_dir.mkdir(parents=True, exist_ok=True)
        self.excel_report.full_output_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def enabled_platforms(self) -> List[PlatformConfig]:
        """Retorna solo las plataformas habilitadas"""
        return [p for p in self.platforms if p.enabled]

    def get_platform_by_name(self, name: str) -> Optional[PlatformConfig]:
        """Obtiene configuración de una plataforma por nombre"""
        for platform in self.platforms:
            if platform.name.upper() == name.upper():
                return platform
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la configuración a diccionario (para debugging)"""
        return {
            "platforms": [
                {
                    "name": p.name,
                    "enabled": p.enabled,
                    "shop": p.shop,
                    "branch_id": p.branch_id,
                    "has_token": bool(p.token)
                }
                for p in self.platforms
            ],
            "intelisis": {
                "base_url": self.intelisis.base_url,
                "has_auth": bool(self.intelisis.auth_token)
            },
            "execution_mode": self.execution.date_mode,
            "reports_enabled": {
                "excel": self.excel_report.enabled,
                "email": self.email_report.enabled
            }
        }


# Instancia global (singleton)
settings = Settings()