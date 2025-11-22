# 🛒 Sistema de Validación Shopify-Intelisis v2.0

Sistema refactorizado para validar órdenes de múltiples plataformas Shopify contra registros de Intelisis ERP.

## 📋 Características

- ✅ **Multi-plataforma**: Soporte para múltiples tiendas Shopify (ROOMI, SPRING, +28 más)
- ✅ **Validación automática**: Compara órdenes contra Intelisis con reglas configurables
- ✅ **Reportes duales**: Excel con formato + Email HTML
- ✅ **Logging robusto**: Logs estructurados con rotación automática
- ✅ **Arquitectura escalable**: Separación de responsabilidades y código testeable
- ✅ **Configuración centralizada**: JSON + variables de entorno

---

## 🏗️ Arquitectura

```
shopify-intelisis-validator/
├── config/                      # Configuración
│   ├── platforms.json          # Plataformas y configuración
│   └── settings.py             # Cargador de configuración
│
├── src/
│   ├── core/                   # Modelos y excepciones
│   │   ├── models.py           # Order, ValidationResult, etc.
│   │   └── exceptions.py       # Excepciones personalizadas
│   │
│   ├── integrations/           # Clientes API
│   │   ├── shopify_client.py  # Cliente Shopify
│   │   └── intelisis_client.py # Cliente Intelisis
│   │
│   ├── services/               # Lógica de negocio
│   │   ├── order_fetcher.py   # Obtención de órdenes
│   │   ├── validator.py       # Validación
│   │   └── orchestrator.py    # Orquestador principal
│   │
│   ├── reports/                # Generación de reportes
│   │   ├── excel_reporter.py  # Generador Excel
│   │   └── email_reporter.py  # Generador Email
│   │
│   └── utils/                  # Utilidades
│       ├── logger.py           # Sistema de logging
│       ├── date_utils.py       # Manejo de fechas
│       └── decorators.py       # Decoradores útiles
│
├── logs/                        # Logs generados (auto)
├── output/                      # Excel generados (auto)
├── main.py                      # Punto de entrada
└── requirements.txt
```

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <repo-url>
cd shopify-intelisis-validator
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

Copiar `.env.example` a `.env` y llenar con las credenciales reales:

```bash
cp .env.example .env
```

Editar `.env`:

```env
# Shopify
SHOPIFY_TOKEN_ROOMI=tu_token_aqui
SHOPIFY_TOKEN_SPRING=tu_token_aqui

# Intelisis
INTELISIS_AUTH_TOKEN=tu_token_aqui
INTELISIS_COOKIE=tu_cookie_aqui

# Email
EMAIL_PASSWORD=tu_password_aqui
```

### 5. Configurar plataformas (opcional)

Editar `config/platforms.json` para ajustar configuración o agregar plataformas.

---

## 💻 Uso

### Ejecución Manual

```bash
python main.py
```

### Configurar Fecha Manual

Editar `config/platforms.json`:

```json
{
  "execution": {
    "date_mode": "manual",
    "manual_date": "2025-10-24"
  }
}
```

### Modo Automático (Ayer + Hoy)

```json
{
  "execution": {
    "date_mode": "automatic"
  }
}
```

### Ejecutar con Task Scheduler (Windows)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Acción: Iniciar programa
   - Programa: `C:\ruta\al\venv\Scripts\python.exe`
   - Argumentos: `C:\ruta\al\main.py`
   - Directorio: `C:\ruta\al\proyecto`
4. Configurar horario (ej: diario a las 8:00 AM)

---

## ⚙️ Configuración

### Agregar Nueva Plataforma

Editar `config/platforms.json`:

```json
{
  "platforms": [
    {
      "name": "NUEVA_PLATAFORMA",
      "enabled": true,
      "shop": "nueva-tienda.myshopify.com",
      "branch_id": 500,
      "api_version": "2024-07"
    }
  ]
}
```

Agregar token al `.env`:

```env
SHOPIFY_TOKEN_NUEVA_PLATAFORMA=shpat_xxxxx
```

### Deshabilitar Plataforma Temporalmente

```json
{
  "name": "SPRING",
  "enabled": false,  // <-- Cambiar a false
  "shop": "spring-air-mx.myshopify.com",
  ...
}
```

### Cambiar Destinatarios de Email

```json
{
  "reports": {
    "email": {
      "enabled": true,
      "recipients": [
        "usuario1@empresa.com",
        "usuario2@empresa.com"
      ]
    }
  }
}
```

### Deshabilitar Reportes

```json
{
  "reports": {
    "excel": {
      "enabled": false  // <-- No genera Excel
    },
    "email": {
      "enabled": false  // <-- No envía email
    }
  }
}
```

---

## 📊 Salidas del Sistema

### 1. Logs

Ubicación: `logs/validation_YYYYMMDD.log`

Contiene registro detallado de toda la ejecución:
- Órdenes consultadas por plataforma
- Resultados de validación
- Errores y warnings
- Métricas de performance

### 2. Excel

Ubicación: `output/consulta_validacion.xlsx`

Contiene:
- Todas las órdenes con sus datos
- Información de Intelisis (si existe)
- Observaciones de validación
- Formato alternado por orden

### 3. Email

Enviado a destinatarios configurados con:
- Resumen ejecutivo por plataforma
- Tabla de órdenes con problemas
- Links directos a Shopify admin

---

## 🔍 Troubleshooting

### Error: "Token no encontrado"

✅ Verificar que el token existe en `.env` con el formato correcto:
```env
SHOPIFY_TOKEN_NOMBREPLATAFORMA=shpat_xxxxx
```

### Error: "Email password no configurado"

✅ Agregar password de app en `.env`:
```env
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

### No se encuentran órdenes

✅ Verificar:
- Fecha configurada es correcta
- Financial status es "paid"
- Las órdenes existen en Shopify

### Órdenes no encontradas en Intelisis

✅ Verificar:
- Campo `Adicional5` en Intelisis contiene el Order ID
- Sucursal (branch_id) es correcta
- Tipo de movimiento es "Pedido"

---

## 📈 Mejoras Futuras (Roadmap)

- [ ] Tests unitarios (pytest)
- [ ] Dashboard web para visualización
- [ ] Base de datos para histórico
- [ ] Notificaciones Slack/Teams
- [ ] API REST para integración
- [ ] Docker container

---

## 👥 Soporte

Para soporte técnico contactar a:
- Email: analistajr@gcatlas.mx
- Departamento: Sistemas GC Atlas

---

## 📝 Changelog

### v2.0.0 (2025-11-05)
- ✨ Refactorización completa con arquitectura modular
- ✨ Soporte multi-plataforma escalable
- ✨ Sistema de logging robusto
- ✨ Configuración centralizada
- ✨ Reportes mejorados (Excel + Email HTML)
- ✨ Manejo de errores mejorado
- ✨ Búsqueda en día siguiente (modo manual)

### v1.0.0
- Versión original con script monolítico
