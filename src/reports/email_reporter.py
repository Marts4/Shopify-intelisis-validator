"""
Generador de reportes por correo electrónico.
Envía emails HTML con resumen y tabla de problemas.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from datetime import datetime
from config import settings
from src.core.models import ValidationResult, ValidationSummary
from src.core.exceptions import EmailSendError
from src.utils import get_current_timestamp
from .base_reporter import BaseReporter


class EmailReporter(BaseReporter):
    """
    Genera y envía reportes por correo electrónico.
    Incluye resumen ejecutivo y detalle de problemas.
    """

    def __init__(self):
        super().__init__('EMAIL_REPORTER')
        self.config = settings.email_report

        if not self.config.enabled:
            self.logger.info("Email reporter deshabilitado en configuración")

        # Validar configuración
        if self.config.enabled:
            self._validate_config()

    def _validate_config(self):
        """Valida que la configuración de email sea correcta"""
        if not self.config.sender:
            raise EmailSendError("Email sender no configurado")

        if not self.config.password:
            raise EmailSendError("Email password no configurado")

        if not self.config.recipients:
            raise EmailSendError("No hay destinatarios configurados")

        self.logger.debug("Configuración de email validada")

    def _create_report(
            self,
            results: List[ValidationResult],
            summary: ValidationSummary,
            date_description: str
    ):
        """
        Genera y envía el email con el reporte.

        Args:
            results: Lista de resultados
            summary: Resumen estadístico
            date_description: Descripción de fechas
        """
        if not self.config.enabled:
            self.logger.info("Envío de email omitido (deshabilitado)")
            return

        self.logger.info(f"Preparando email para: {', '.join(self.config.recipients)}")

        # Crear mensaje
        msg = self._create_message(results, summary, date_description)

        # Enviar
        self._send_email(msg)

    def _create_message(
            self,
            results: List[ValidationResult],
            summary: ValidationSummary,
            date_description: str
    ) -> MIMEMultipart:
        """
        Crea el mensaje de email con formato HTML.

        Args:
            results: Lista de resultados
            summary: Resumen estadístico
            date_description: Descripción de fechas

        Returns:
            Mensaje MIME completo
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = self.config.sender
        msg['To'] = ', '.join(self.config.recipients)
        msg['Subject'] = self._create_subject(summary, date_description)

        # Generar HTML
        html_body = self._generate_html(results, summary, date_description)

        # Adjuntar HTML
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        return msg

    def _create_subject(self, summary: ValidationSummary, date_description: str) -> str:
        """
        Crea el asunto del email.

        Args:
            summary: Resumen estadístico
            date_description: Descripción de fechas

        Returns:
            String con el asunto
        """
        return (
            f"📊 Validación Shopify-Intelisis | {date_description} | "
            f"{summary.total_orders} órdenes"
        )

    def _generate_html(
            self,
            results: List[ValidationResult],
            summary: ValidationSummary,
            date_description: str
    ) -> str:
        """
        Genera el HTML del reporte.

        Args:
            results: Lista de resultados
            summary: Resumen estadístico
            date_description: Descripción de fechas

        Returns:
            String con HTML completo
        """
        # Calcular estadísticas por plataforma
        platform_stats = self._calculate_platform_stats(summary)

        # Filtrar registros con problemas
        problematic_results = [r for r in results if not r.is_ok]

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: left;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 28px;
        }}
        .header p {{
            margin: 5px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .summary-section {{
            margin-bottom: 30px;
        }}
        .summary-section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: center;
            font-size: 14px;
            font-weight: 600;
        }}
        .summary-table td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid #e0e0e0;
            font-size: 14px;
        }}
        .summary-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .metric-label {{
            font-weight: 600;
            color: #333;
        }}
        .metric-value {{
            font-size: 20px;
            font-weight: 700;
        }}
        .value-ok {{ color: #28a745; }}
        .value-warning {{ color: #ffc107; }}
        .value-danger {{ color: #dc3545; }}
        .value-info {{ color: #667eea; }}
        .problems-section {{
            margin: 30px 0;
            padding: 20px;
            background: #fff3cd;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }}
        .problems-section h2 {{
            color: #856404;
            margin: 0 0 15px 0;
        }}
        .problems-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
        }}
        .problems-table th {{
            background: #ffc107;
            color: #333;
            padding: 10px;
            text-align: left;
            font-size: 12px;
        }}
        .problems-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
            font-size: 11px;
        }}
        .problems-table tr:hover {{
            background-color: #fffaeb;
        }}
        .problems-table a {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }}
        .problems-table a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }}
        .no-problems {{
            text-align: center;
            padding: 20px;
            color: #28a745;
            font-size: 18px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Reporte de Validación Shopify vs Intelisis</h1>
            <p><strong>Fecha:</strong> {date_description}</p>
            <p><strong>Generado:</strong> {get_current_timestamp()}</p>
        </div>

        <div class="content">
            <div class="summary-section">
                <h2>Resumen General</h2>
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>📊 MÉTRICA</th>
                            {platform_stats['headers']}
                            <th>📈 TOTAL</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="metric-label">Total Órdenes</td>
                            {platform_stats['totals']}
                            <td class="metric-value value-info">{summary.total_orders}</td>
                        </tr>
                        <tr>
                            <td class="metric-label">✅ Validaciones OK</td>
                            {platform_stats['ok']}
                            <td class="metric-value value-ok">{summary.ok_count}</td>
                        </tr>
                        <tr>
                            <td class="metric-label">⚠️ Con Diferencias</td>
                            {platform_stats['differences']}
                            <td class="metric-value value-warning">{summary.differences_count}</td>
                        </tr>
                        <tr>
                            <td class="metric-label">❌ No Encontrados</td>
                            {platform_stats['not_found']}
                            <td class="metric-value value-danger">{summary.not_found_count}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
"""

        # Sección de problemas
        if problematic_results:
            html += f"""
            <div class="problems-section">
                <h2>⚠️ Registros con Diferencias o No Encontrados ({len(problematic_results)})</h2>
                <table class="problems-table">
                    <thead>
                        <tr>
                            <th>Plataforma</th>
                            <th>Order #</th>
                            <th>Cliente</th>
                            <th>Total Shopify</th>
                            <th>Total Intelisis</th>
                            <th>Observaciones</th>
                        </tr>
                    </thead>
                    <tbody>
"""

            for result in problematic_results:
                order = result.order
                shopify_url = self._get_shopify_url(order)

                total_intelisis = (
                    f"${result.intelisis.total:.2f}"
                    if result.intelisis else "N/A"
                )

                html += f"""
                        <tr>
                            <td>{order.platform}</td>
                            <td><a href="{shopify_url}" target="_blank">{order.order_number}</a></td>
                            <td>{order.customer_name}</td>
                            <td>${order.total:.2f}</td>
                            <td>{total_intelisis}</td>
                            <td>{result.observations}</td>
                        </tr>
"""

            html += """
                    </tbody>
                </table>
            </div>
"""
        else:
            html += """
            <div class="no-problems">
                ✅ ¡Todas las órdenes validadas correctamente! No hay diferencias.
            </div>
"""

        html += """
        </div>

        <div class="footer">
            <p>Este correo fue generado automáticamente por el sistema de validación Shopify-Intelisis</p>
            <p>GC Atlas IT - Sistema de Validación v2.0</p>
        </div>
    </div>
</body>
</html>
"""

        return html

    def _calculate_platform_stats(self, summary: ValidationSummary) -> dict:
        """
        Calcula estadísticas HTML por plataforma.

        Args:
            summary: Resumen estadístico

        Returns:
            Diccionario con HTML de estadísticas
        """
        platforms = sorted(summary.platform_stats.keys())

        headers = ''.join([f'<th>🛒 {p}</th>' for p in platforms])

        totals = ''.join([
            f'<td class="metric-value value-info">{summary.platform_stats[p]["total"]}</td>'
            for p in platforms
        ])

        ok = ''.join([
            f'<td class="metric-value value-ok">{summary.platform_stats[p]["ok"]}</td>'
            for p in platforms
        ])

        differences = ''.join([
            f'<td class="metric-value value-warning">{summary.platform_stats[p]["differences"]}</td>'
            for p in platforms
        ])

        not_found = ''.join([
            f'<td class="metric-value value-danger">{summary.platform_stats[p]["not_found"]}</td>'
            for p in platforms
        ])

        return {
            'headers': headers,
            'totals': totals,
            'ok': ok,
            'differences': differences,
            'not_found': not_found
        }

    def _get_shopify_url(self, order) -> str:
        """
        Genera la URL de administración de Shopify para una orden.

        Args:
            order: Objeto Order

        Returns:
            URL de Shopify admin
        """
        platform_config = settings.get_platform_by_name(order.platform)

        if not platform_config:
            return "#"

        # Usar la nueva propiedad shopify_admin_name
        return f"https://admin.shopify.com/store/{platform_config.shopify_admin_name}/orders/{order.order_id}"

    def _send_email(self, msg: MIMEMultipart):
        """
        Envía el email a través de SMTP.

        Args:
            msg: Mensaje MIME a enviar
        """
        server = None
        try:
            self.logger.info("Conectando al servidor SMTP...")
            self.logger.debug(f"Servidor: {self.config.smtp_server}:{self.config.smtp_port}")

            # Detectar si es puerto SSL (465) o STARTTLS (587)
            if self.config.smtp_port == 465:
                # SSL directo (puerto 465)
                self.logger.debug("Usando SSL directo (puerto 465)")
                server = smtplib.SMTP_SSL(self.config.smtp_server, self.config.smtp_port, timeout=30)
            else:
                # STARTTLS (puerto 587)
                self.logger.debug("Usando STARTTLS (puerto 587)")
                server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port, timeout=30)
                self.logger.debug("Iniciando TLS...")
                try:
                    server.starttls()
                except smtplib.SMTPNotSupportedError:
                    # Algunos servidores no requieren STARTTLS
                    self.logger.warning("STARTTLS no soportado, continuando sin TLS")

            # Autenticar
            self.logger.debug("Autenticando...")
            server.login(self.config.sender, self.config.password)

            # Enviar mensaje
            self.logger.info(f"Enviando email a: {', '.join(self.config.recipients)}")
            server.send_message(msg)

            self.logger.info("✓ Email enviado exitosamente")

        except smtplib.SMTPAuthenticationError as e:
            raise EmailSendError(
                f"Error de autenticación SMTP: {str(e)}",
                self.config.recipients
            )
        except smtplib.SMTPRecipientsRefused as e:
            raise EmailSendError(
                f"Destinatarios rechazados: {str(e)}",
                self.config.recipients
            )
        except smtplib.SMTPException as e:
            raise EmailSendError(
                f"Error SMTP: {str(e)}",
                self.config.recipients
            )
        except Exception as e:
            raise EmailSendError(
                f"Error enviando email: {str(e)}",
                self.config.recipients
            )
        finally:
            if server:
                try:
                    server.quit()
                    self.logger.debug("Conexión SMTP cerrada")
                except:
                    pass