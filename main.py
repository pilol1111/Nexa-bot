from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, FileResponse
import requests

from database import (
    obtener_inmuebles,
    obtener_modo_cliente,
    activar_asesor,
    activar_bot,
    guardar_mensaje,
    obtener_conversaciones,
    obtener_historial,
    enviar_mensaje_asesor
)


app = FastAPI(title="Nexa Propiedades Bot")


# ==========================================
# CONFIGURACIÓN WHATSAPP
# ==========================================

VERIFY_TOKEN = "nexa123"

ACCESS_TOKEN = "EAAdI6Dj1yV0BSgD7nZBjqOwTKZA4JXIXr111QGf64IROehaXdwB5eerzZBO6xUsZBydqTcel7uao4GVlzinYXg4dhvZA0DZAZBrCyXeqfMZBfq6aFXNjzZBgUUbhJAQau6EZBHIPVlfnNkMAI1crQJRV7ru3n2g7jLCsZCFaBtCMv17Rm5yaQIrntITuXdRBnYwzvLTogZDZD"

PHONE_NUMBER_ID = "1344424105422449"


# ==========================================
# MENÚ PRINCIPAL
# ==========================================

MENU = """
🏠 *NEXA PROPIEDADES*

¡Hola! 👋 Bienvenido a Nexa Propiedades.

¿En qué podemos ayudarte?

1️⃣ Ver inmuebles en arriendo
2️⃣ Ver inmuebles en venta
3️⃣ Publicar mi inmueble
4️⃣ Hablar con un asesor

Escribe el número de la opción que deseas.
"""


# ==========================================
# INICIO
# ==========================================

@app.get("/")
def inicio():
    return {
        "message": "Bienvenido al Bot de Nexa Propiedades"
    }

@app.get("/panel")
def panel():
    return FileResponse("panel/index.html")

# ==========================================
# PANEL - CONVERSACIONES
# ==========================================

@app.get("/panel/conversaciones")
def panel_conversaciones():

    conversaciones = obtener_conversaciones()

    return {
        "conversaciones": conversaciones
    }


# ==========================================
# PANEL - HISTORIAL
# ==========================================

@app.get("/panel/conversaciones/{numero}")
def panel_historial(numero):

    historial = obtener_historial(numero)
    modo = obtener_modo_cliente(numero)

    return {
        "numero_cliente": numero,
        "modo": modo,
        "mensajes": historial
        
    }

@app.post("/panel/enviar")
async def panel_enviar_mensaje(request: Request):

    datos = await request.json()

    numero = datos.get("numero")
    mensaje = datos.get("mensaje")

    if not numero or not mensaje:
        return {
            "ok": False,
            "error": "Faltan datos"
        }

    # Enviar mensaje por WhatsApp
    enviado = enviar_mensaje(
        numero,
        mensaje,
        guardar_como_bot=False
    )

    if not enviado:
        return {
            "ok": False,
            "error": "No se pudo enviar el mensaje por WhatsApp"
        }

    # Guardarlo como mensaje del asesor
    guardado = enviar_mensaje_asesor(
        numero,
        mensaje
    )

    if not guardado:
        return {
            "ok": False,
            "error": "El mensaje fue enviado pero no se pudo guardar"
        }

    return {
        "ok": True,
        "mensaje": "Mensaje enviado correctamente"
    }
@app.post("/panel/tomar")
async def panel_tomar(request: Request):

    datos = await request.json()

    numero = datos.get("numero")

    if not numero:
        return {
            "ok": False,
            "error": "Falta el número del cliente"
        }

    resultado = activar_asesor(numero)

    if not resultado:
        return {
            "ok": False,
            "error": "No se pudo activar el modo asesor"
        }

    return {
        "ok": True,
        "mensaje": "Conversación tomada por el asesor"
    }


@app.post("/panel/devolver-bot")
async def panel_devolver_bot(request: Request):

    datos = await request.json()

    numero = datos.get("numero")

    if not numero:
        return {
            "ok": False,
            "error": "Falta el número del cliente"
        }

    resultado = activar_bot(numero)

    if not resultado:
        return {
            "ok": False,
            "error": "No se pudo devolver la conversación al bot"
        }

    return {
        "ok": True,
        "mensaje": "Conversación devuelta al bot"
    }



# ==========================================
# VERIFICACIÓN DEL WEBHOOK
# ==========================================

@app.get("/webhook")
async def verificar_webhook(request: Request):

    params = request.query_params

    modo = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if modo == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse(
        "Token incorrecto",
        status_code=403
    )


# ==========================================
# RECIBIR MENSAJES
# ==========================================

@app.post("/webhook")
async def recibir_mensaje(request: Request):

    data = await request.json()

    print("\n==============================")
    print("MENSAJE RECIBIDO")
    print("==============================")
    print(data)

    try:

        entrada = data["entry"][0]
        cambios = entrada["changes"][0]
        valor = cambios["value"]

        mensajes = valor.get("messages", [])

        if not mensajes:
            return {"status": "ok"}

        mensaje = mensajes[0]

        numero = mensaje["from"]
        tipo = mensaje["type"]

        if tipo == "text":

            texto_recibido = mensaje["text"]["body"]

            guardar_mensaje(
                numero,
                "cliente",
                texto_recibido
            )

        modo_cliente = obtener_modo_cliente(numero)

        print("Modo del cliente:", modo_cliente)

        # ==========================================
        # CLIENTE EN ATENCIÓN CON ASESOR
        # ==========================================

        if modo_cliente == "ASESOR":

            print(
                f"👨‍💼 {numero} está en atención con un asesor."
            )

            return {"status": "ok"}

        # ==========================================
        # SOLO MENSAJES DE TEXTO
        # ==========================================

        if tipo != "text":

            print("⚠️ Mensaje recibido que no es texto.")

            return {"status": "ok"}

        texto = mensaje["text"]["body"].strip().lower()

        print("Número:", numero)
        print("Texto:", texto)

        # ==========================================
        # MENÚ PRINCIPAL
        # ==========================================

        if texto in [
            "hola",
            "menu",
            "menú",
            "inicio",
            "buenas"
        ]:

            enviar_mensaje(
                numero,
                MENU
            )

        # ==========================================
        # OPCIÓN 1 - ARRIENDO
        # ==========================================

        elif texto == "1":

            mostrar_inmuebles(
                numero,
                "arriendo"
            )

        # ==========================================
        # OPCIÓN 2 - VENTA
        # ==========================================

        elif texto == "2":

            mostrar_inmuebles(
                numero,
                "venta"
            )

        # ==========================================
        # OPCIÓN 3 - PUBLICAR
        # ==========================================

        elif texto == "3":

            mensaje_publicar = """
🏠 *PUBLICAR MI INMUEBLE*

¡Excelente! Podemos ayudarte a publicar tu inmueble.

Un asesor de Nexa Propiedades se pondrá en contacto contigo para conocer los detalles del inmueble.

📞 En breve te atenderemos.
"""

            enviar_mensaje(
                numero,
                mensaje_publicar
            )

        # ==========================================
        # OPCIÓN 4 - ASESOR
        # ==========================================

        elif texto == "4":

            mensaje_asesor = """
👨‍💼 *HABLAR CON UN ASESOR*

Perfecto.

Hemos recibido tu solicitud para hablar con un asesor de Nexa Propiedades.

📞 En breve te contactaremos.
"""

            enviar_mensaje(
                numero,
                mensaje_asesor
            )

        # ==========================================
        # VOLVER AL MENÚ
        # ==========================================

        elif texto == "0":

            enviar_mensaje(
                numero,
                MENU
            )

        # ==========================================
        # OPCIÓN DESCONOCIDA
        # ==========================================

        else:

            mensaje_error = """
❌ No reconocí esa opción.

Por favor escribe un número del menú:

1️⃣ Arriendos
2️⃣ Ventas
3️⃣ Publicar mi inmueble
4️⃣ Hablar con un asesor

0️⃣ Volver al menú
"""

            enviar_mensaje(
                numero,
                mensaje_error
            )

    except Exception as e:

        print("❌ Error procesando mensaje:")
        print(e)

    return {"status": "ok"}


# ==========================================
# MOSTRAR INMUEBLES
# ==========================================

def mostrar_inmuebles(numero, tipo_operacion):

    try:

        inmuebles = obtener_inmuebles(
            tipo_operacion
        )

        if not inmuebles:

            enviar_mensaje(
                numero,
                f"""
😔 Actualmente no encontramos inmuebles disponibles en {tipo_operacion}.

Puedes intentar nuevamente más adelante.

0️⃣ Volver al menú
"""
            )

            return

        encabezado = ""

        if tipo_operacion == "arriendo":

            encabezado = """
🏠 *INMUEBLES EN ARRIENDO*

Estos son algunos de los inmuebles disponibles:

"""

        elif tipo_operacion == "venta":

            encabezado = """
🏠 *INMUEBLES EN VENTA*

Estos son algunos de los inmuebles disponibles:

"""

        enviar_mensaje(
            numero,
            encabezado
        )

        # ==========================================
        # MOSTRAR CADA INMUEBLE
        # ==========================================

        for inmueble in inmuebles:

            (
                id_publicacion,
                titulo,
                precio,
                moneda,
                estado,
                url
            ) = inmueble

            precio_formateado = (
                f"${precio:,.0f}".replace(",", ".")
            )

            mensaje_inmueble = f"""
🏠 *{titulo}*

💰 Precio: {precio_formateado} {moneda}

📌 Estado: {estado}

🔗 Ver inmueble:
{url}

━━━━━━━━━━━━━━
"""

            enviar_mensaje(
                numero,
                mensaje_inmueble
            )

        enviar_mensaje(
            numero,
            """
¿Quieres consultar otra opción?

1️⃣ Ver arriendos
2️⃣ Ver ventas
0️⃣ Volver al menú
"""
        )

    except Exception as e:

        print("❌ Error consultando inmuebles:")
        print(e)

        enviar_mensaje(
            numero,
            """
⚠️ Ocurrió un problema consultando los inmuebles.

Por favor intenta nuevamente más tarde.

0️⃣ Volver al menú
"""
        )


# ==========================================
# ENVIAR MENSAJE A WHATSAPP
# ==========================================

def enviar_mensaje(numero, mensaje, guardar_como_bot=True):

    url = (
        f"https://graph.facebook.com/v23.0/"
        f"{PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {
            "body": mensaje
        }
    }

    respuesta = requests.post(
        url,
        headers=headers,
        json=payload
    )

    print("WhatsApp API:")
    print(respuesta.status_code)
    print(respuesta.text)

    if respuesta.ok and guardar_como_bot:
        guardar_mensaje(
            numero,
            "BOT",
            mensaje
        )

    return respuesta.ok