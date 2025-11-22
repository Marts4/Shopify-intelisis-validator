"""
Script de prueba para verificar configuración de email.
Ejecutar: python test_email.py
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Cargar .env
load_dotenv()

# Configuración (cambiar según tu platforms.json)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # Cambiar según configuración (465 o 587)
SENDER = "gca.corporativo1@gmail.com"
PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT = "analistajr@gcatlas.mx"

print("=" * 60)
print("🔧 TEST DE CONFIGURACIÓN DE EMAIL")
print("=" * 60)
print()

# Verificar configuración
print("📋 Configuración:")
print(f"  Servidor: {SMTP_SERVER}")
print(f"  Puerto: {SMTP_PORT}")
print(f"  Remitente: {SENDER}")
print(f"  Destinatario: {RECIPIENT}")
print(f"  Password configurado: {'✓ Sí' if PASSWORD else '✗ NO'}")
print()

if not PASSWORD:
    print("❌ ERROR: EMAIL_PASSWORD no configurado en .env")
    print("   Agrega: EMAIL_PASSWORD=tu_password_aqui")
    exit(1)

# Crear mensaje de prueba
msg = MIMEMultipart()
msg['From'] = SENDER
msg['To'] = RECIPIENT
msg['Subject'] = "🔧 Test de Configuración - Sistema Validación"

body = """
<html>
<body>
    <h2>✅ Test de Email Exitoso</h2>
    <p>Este es un correo de prueba del sistema de validación Shopify-Intelisis.</p>
    <p>Si recibiste este mensaje, la configuración de email está correcta.</p>
    <hr>
    <p><small>Generado automáticamente por test_email.py</small></p>
</body>
</html>
"""

msg.attach(MIMEText(body, 'html', 'utf-8'))

# Intentar enviar
print("=" * 60)
print("📤 INTENTANDO ENVIAR EMAIL...")
print("=" * 60)
print()

try:
    # Opción 1: Puerto 465 (SSL)
    if SMTP_PORT == 465:
        print("1. Conectando con SSL (puerto 465)...")
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        print("   ✓ Conectado")
    
    # Opción 2: Puerto 587 (STARTTLS)
    else:
        print("1. Conectando al servidor SMTP...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        print("   ✓ Conectado")
        
        print("2. Iniciando STARTTLS...")
        server.starttls()
        print("   ✓ TLS iniciado")
    
    # Autenticar
    print("3. Autenticando...")
    server.login(SENDER, PASSWORD)
    print("   ✓ Autenticado")
    
    # Enviar
    print("4. Enviando mensaje...")
    server.send_message(msg)
    print("   ✓ Enviado")
    
    # Cerrar
    server.quit()
    print("   ✓ Conexión cerrada")
    
    print()
    print("=" * 60)
    print("✅ EMAIL ENVIADO EXITOSAMENTE")
    print("=" * 60)
    print()
    print(f"📬 Revisa la bandeja de: {RECIPIENT}")
    print()

except smtplib.SMTPAuthenticationError as e:
    print()
    print("❌ ERROR DE AUTENTICACIÓN")
    print("=" * 60)
    print(f"Detalles: {e}")
    print()
    print("💡 Posibles causas:")
    print("  1. Contraseña incorrecta")
    print("  2. Si usas Gmail, necesitas una 'Contraseña de Aplicación'")
    print("     - Ir a: https://myaccount.google.com/apppasswords")
    print("     - Crear nueva contraseña de aplicación")
    print("     - Copiar al .env: EMAIL_PASSWORD=xxxx xxxx xxxx xxxx")
    print()

except smtplib.SMTPNotSupportedError as e:
    print()
    print("❌ ERROR: STARTTLS NO SOPORTADO")
    print("=" * 60)
    print(f"Detalles: {e}")
    print()
    print("💡 Solución:")
    print("  Cambiar puerto en platforms.json:")
    print('  "smtp_port": 465  // <-- En lugar de 587')
    print()

except smtplib.SMTPException as e:
    print()
    print("❌ ERROR SMTP")
    print("=" * 60)
    print(f"Detalles: {e}")
    print()

except Exception as e:
    print()
    print("❌ ERROR GENERAL")
    print("=" * 60)
    print(f"Tipo: {type(e).__name__}")
    print(f"Detalles: {e}")
    print()
    
    import traceback
    print("Stack trace:")
    traceback.print_exc()
    print()

print("=" * 60)
print("FIN DEL TEST")
print("=" * 60)