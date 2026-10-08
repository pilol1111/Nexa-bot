import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

DESTINATARIO = GMAIL_USER

mensaje = EmailMessage()

mensaje["Subject"] = "Prueba de correo - Nexa Propiedades"
mensaje["From"] = GMAIL_USER
mensaje["To"] = DESTINATARIO

mensaje.set_content(
    """Hola.

Este es un correo de prueba enviado desde Nexa Propiedades.

Si estás viendo este mensaje, la configuración SMTP de Gmail funciona correctamente.

Nexa Propiedades
"""
)

try:
    print("📧 Conectando con Gmail...")

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()

        print("🔐 Iniciando sesión en Gmail...")

        servidor.login(
            GMAIL_USER,
            GMAIL_APP_PASSWORD
        )

        print("📨 Enviando correo...")

        servidor.send_message(mensaje)

    print("✅ Correo enviado correctamente.")

except Exception as e:
    print("❌ Error enviando el correo:")
    print(e)