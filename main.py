import os
import re
import smtplib
import itertools
from auth import verificar_password, generar_hash   
import hashlib
from email.message import EmailMessage
from fastapi import FastAPI, Request,Query
from urllib.parse import quote
from fastapi.responses import (
    PlainTextResponse,
    FileResponse,
    RedirectResponse
)
from starlette.middleware.sessions import SessionMiddleware
import requests

from dotenv import load_dotenv

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

from database import (
    obtener_inmuebles,
    obtener_modo_cliente,
    activar_asesor,
    activar_bot,
    guardar_mensaje,
    obtener_conversaciones,
    obtener_historial,
    enviar_mensaje_asesor,
    obtener_usuario_por_correo,
    guardar_token_recuperacion,
    obtener_token_recuperacion,
    marcar_token_usado,
    actualizar_password,
    crear_asesor,
    obtener_asesores,
    cambiar_estado_asesor,

    # CLIENTES
    agregar_cliente,
    obtener_clientes,
    obtener_cliente,
    buscar_clientes,
    editar_cliente,
    eliminar_cliente,
    cambiar_estado_cliente

    
)

from auth import verificar_password
import secrets
import time

# ============================================================
# APLICACIÓN
# ============================================================

app = FastAPI(title="Nexa Propiedades Bot")


# ============================================================
# CONFIGURACIÓN DE SESIONES
# ============================================================

# IMPORTANTE:
# Cambia este valor por una cadena larga y aleatoria.
# NO compartas esta clave públicamente.

SESSION_SECRET = secrets.token_urlsafe(64)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="nexa_session",
    max_age=None,
    same_site="lax",
    https_only=False
)

# ============================================================
# CONFIGURACIÓN WHATSAPP
# ============================================================

VERIFY_TOKEN = "nexa123"

ACCESS_TOKEN = "EAAdI6Dj1yV0BSgD7nZBjqOwTKZA4JXIXr111QGf64IROehaXdwB5eerzZBO6xUsZBydqTcel7uao4GVlzinYXg4dhvZA0DZAZBrCyXeqfMZBfq6aFXNjzZBgUUbhJAQau6EZBHIPVlfnNkMAI1crQJRV7ru3n2g7jLCsZCFaBtCMv17Rm5yaQIrntITuXdRBnYwzvLTogZDZD"

PHONE_NUMBER_ID = "1344424105422449"


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

MENU = """
🏠 *NEXA PROPIEDADES*

¡Hola! 👋 Bienvenido a Nexa Propiedades.

¿En qué podemos ayudarte?

1️⃣ Ver inmuebles en arriendo
2️⃣ Ver inmuebles en venta
3️⃣ Publicar mi inmueble
4️⃣ Hablar con un asesor
5️⃣ Me interesa un inmueble específico

Escribe el número de la opción que deseas.
"""


# ============================================================
# FUNCIONES DE AUTENTICACIÓN
# ============================================================

def usuario_autenticado(request: Request):
    """
    Comprueba si existe una sesión de usuario válida.
    """

    return request.session.get("usuario")

TIEMPO_INACTIVIDAD = 30 * 60 #30 minutos

def proteger_panel(request: Request):

    usuario = usuario_autenticado(request)

    if not usuario:
        return False

    ahora = time.time()

    ultima_actividad = request.session.get("ultima_actividad")

    # Si no existe la actividad registrada, la creamos
    if ultima_actividad is None:
        request.session["ultima_actividad"] = ahora
        return True

    # Comprobar cuánto tiempo lleva inactivo
    tiempo_inactivo = ahora - ultima_actividad

    if tiempo_inactivo >= TIEMPO_INACTIVIDAD:
        request.session.clear()
        print("🔒 Sesión cerrada por inactividad.")
        return False

    # Renovar actividad
    request.session["ultima_actividad"] = ahora

    return True

#-------------------------------------------
# CORREO RECUPERACION
#-------------------------------------------

def enviar_correo_recuperacion(destinatario, enlace):
    mensaje = EmailMessage()

    mensaje["Subject"] = "Recuperación de contraseña - Nexa Propiedades"
    mensaje["From"] = GMAIL_USER
    mensaje["To"] = destinatario

    mensaje.set_content(
        f"""Hola,

Recibimos una solicitud para recuperar la contraseña de tu cuenta de Nexa Propiedades.

Puedes establecer una nueva contraseña desde el siguiente enlace:

{enlace}

Este enlace es temporal y solo puede utilizarse una vez.

Si tú no solicitaste este cambio, puedes ignorar este correo.

Nexa Propiedades
"""
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()

        servidor.login(
            GMAIL_USER,
            GMAIL_APP_PASSWORD
        )

        servidor.send_message(mensaje)
# ============================================================
# INICIO
# ============================================================

@app.get("/")
def inicio():
    return {
        "message": "Bienvenido al Bot de Nexa Propiedades"
    }
# ========================================================
# RECUPERAR CONTRASEÑA
# ======================================================== 

@app.get("/recuperar-password")
def mostrar_recuperacion():
    return FileResponse("panel/recuperar.html")

@app.post("/recuperar-password")
async def solicitar_recuperacion(request: Request):
    datos = await request.form()

    correo = datos.get("correo")

    if not correo:
        return RedirectResponse(
            url="/recuperar-password?error=Debes%20ingresar%20un%20correo",
            status_code=303
        )

    correo = correo.strip().lower()

    from database import obtener_usuario_por_correo

    usuario = obtener_usuario_por_correo(correo)

    # Por seguridad, no revelamos si el correo existe o no.
    if not usuario:
        return RedirectResponse(
            url="/recuperar-password?mensaje=Solicitud%20recibida",
            status_code=303
        )

    usuario_id = usuario["id"]

    # Token seguro
    token = secrets.token_urlsafe(32)

    # Guardamos únicamente el hash
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    # Importamos la función que guardará el token
    from database import guardar_token_recuperacion

    guardar_token_recuperacion(
        usuario_id,
        token_hash
    )

    # En desarrollo local
    enlace = f"http://127.0.0.1:8000/restablecer-password?token={token}"

    try:
        enviar_correo_recuperacion(
            correo,
            enlace
        )

        print(f"📧 Correo de recuperación enviado a {correo}")

    except Exception as e:
        print("❌ Error enviando correo:")
        print(e)

    return RedirectResponse(
        url="/recuperar-password?mensaje=Solicitud%20recibida",
        status_code=303
    )

#------------------------------------------------------------
# RESTABLECER CONTRASEÑA
#------------------------------------------------------------

@app.get("/restablecer-password")
def mostrar_restablecer():
    return FileResponse("panel/restablecer.html")

@app.post("/restablecer-password")
async def procesar_restablecer(request: Request):
    datos = await request.form()

    token = datos.get("token")
    password = datos.get("password")
    confirmar_password = datos.get("confirmar_password")

    # Validar datos
    if not token or not password or not confirmar_password:
        return RedirectResponse(
            url="/restablecer-password?error=Todos%20los%20campos%20son%20obligatorios",
            status_code=303
        )

    # Confirmar que las contraseñas coincidan
    if password != confirmar_password:
        return RedirectResponse(
            url=f"/restablecer-password?token={quote(token)}&error=Las%20contraseñas%20no%20coinciden",
            status_code=303
        )

    # Longitud mínima
    if len(password) < 8:
        return RedirectResponse(
            url=f"/restablecer-password?token={quote(token)}&error=La%20contraseña%20debe%20tener%20al%20menos%208%20caracteres",
            status_code=303
        )

    # Convertir token a hash
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    # Buscar token
    recuperacion = obtener_token_recuperacion(token_hash)

    if not recuperacion:
        return RedirectResponse(
            url="/login?error=El%20enlace%20de%20recuperación%20no%20es%20válido",
            status_code=303
        )

    # Verificar si ya fue utilizado
    if recuperacion["usado"]:
        return RedirectResponse(
            url="/login?error=Este%20enlace%20ya%20fue%20utilizado",
            status_code=303
        )

    # Verificar expiración
    from datetime import datetime

    if datetime.now() >= recuperacion["fecha_expiracion"]:
        return RedirectResponse(
            url="/login?error=El%20enlace%20de%20recuperación%20ha%20expirado",
            status_code=303
        )

    # Generar nuevo hash Argon2id
    nuevo_password_hash = generar_hash(password)

    # Actualizar contraseña
    actualizar_password(
        recuperacion["usuario_id"],
        nuevo_password_hash
    )

    # Invalidar token
    marcar_token_usado(
        recuperacion["id"]
    )

    print(
        f"🔐 Contraseña actualizada para usuario "
        f"{recuperacion['usuario_id']}"
    )

    return RedirectResponse(
        url="/login?mensaje=Contraseña%20actualizada%20correctamente",
        status_code=303
    )




# ============================================================
# LOGIN - MOSTRAR FORMULARIO
# ============================================================

@app.get("/login")
def mostrar_login(request: Request):

    usuario = usuario_autenticado(request)

    if usuario:
        return RedirectResponse(
            url="/panel",
            status_code=303
        )

    return FileResponse("panel/login.html")


# ============================================================
# LOGIN - PROCESAR
# ============================================================

@app.post("/login")
async def procesar_login(request: Request):

    datos = await request.form()

    correo = datos.get("correo")
    password = datos.get("password")

    if not correo or not password:

        return FileResponse(
            "panel/login.html",
            status_code=400
        )

    correo = correo.strip().lower()

 # ========================================================
    # CONSULTAR USUARIO EN POSTGRESQL
    # ========================================================

    from database import obtener_usuario_por_correo

    usuario = obtener_usuario_por_correo(correo)

    if not usuario:
        mensaje = quote ("Correo o contraseña incorrectos.")
        return RedirectResponse(
            url=f"/login?error={mensaje}",
            status_code=303
        )

    # ========================================================
    # DATOS DEL USUARIO
    # ========================================================

    usuario_id = usuario["id"]  
    nombre = usuario["nombre"]
    password_hash = usuario["password_hash"]
    rol = usuario["rol"]
    activo = usuario["activo"]

    # ========================================================
    # COMPROBAR ESTADO
    # ========================================================

    if not activo:

        return FileResponse(
            "panel/login.html",
            status_code=403
        )

    # ========================================================
    # VERIFICAR CONTRASEÑA ARGON2
    # ========================================================

    password_correcta = verificar_password(
        password,
        password_hash
    )

    if not password_correcta:
        mensaje = quote ("Correo o contraseña incorrectos.")
        return RedirectResponse(
            url=f"/login?error={mensaje}",
            status_code=303
        )

    # ========================================================
    # CREAR SESIÓN
    # ========================================================

    request.session["usuario"] = {
        "id": usuario_id,
        "nombre": nombre,
        "correo": correo,
        "rol": rol
    }

    request.session["ultima_actividad"] = time.time()

    print(
        f"🔐 Inicio de sesión: {correo} "
        f"({rol})"
    )

    return RedirectResponse(
        url="/panel",
        status_code=303
    )



    # ========================================================
    #  PANEL DE ADMINISTRACION DE ASESORES
    # ========================================================
@app.get("/panel/asesores")
def panel_asesores(request: Request):

    if not proteger_panel(request):
        return RedirectResponse(url="/login", status_code=303)

    usuario = usuario_autenticado(request)

    # Solo administradores
    if usuario["rol"] != "administrador":
        return RedirectResponse(url="/panel", status_code=303)

    return FileResponse("panel/asesores.html")
    # ========================================================
    # API LISTAR ASESORES 
    # ========================================================
@app.get("/panel/api/asesores")
def listar_asesores(request: Request):

    if not proteger_panel(request):
        return {"error": "No autenticado"}

    usuario = usuario_autenticado(request)

    if usuario["rol"] != "administrador":
        return {"error": "No tienes permisos para realizar esta acción"}

    return {
        "asesores": obtener_asesores()
    }
    # ========================================================
    # API CREAR ASESORES 
    # ========================================================
@app.post("/panel/api/asesores")
async def registrar_asesor(request: Request):

    if not proteger_panel(request):
        return {"error": "No autenticado"}

    usuario = usuario_autenticado(request)

    if usuario["rol"] != "administrador":
        return {"error": "No tienes permisos para realizar esta acción"}

    datos = await request.json()

    nombre = datos.get("nombre")
    correo = datos.get("correo")
    password = datos.get("password")

    if not nombre or not correo or not password:
        return {
            "error": "Todos los campos son obligatorios"
        }

    nombre = nombre.strip()
    correo = correo.strip().lower()

    password_valida, mensaje_password = validar_password(password)

    if not password_valida:
        return {"error": mensaje_password}

    usuario_existente = obtener_usuario_por_correo(correo)

    if usuario_existente:
        return {
            "error": "Ya existe un usuario con ese correo"
        }

    password_hash = generar_hash(password)

    asesor_id = crear_asesor(
        nombre,
        correo,
        password_hash
    )

    print(
        f"👨‍💼 Nuevo asesor creado: "
        f"{nombre} ({correo})"
    )

    return {
        "ok": True,
        "mensaje": "Asesor creado correctamente",
        "id": asesor_id
    }
    # ========================================================
    # API-ACTIVAR/DESACTIVAR ASESORES
    # ========================================================
@app.put("/panel/api/asesores/{asesor_id}/estado")
async def cambiar_estado_asesor_panel(
    asesor_id: int,
    request: Request
):

    if not proteger_panel(request):
        return {
            "error": "No autenticado"
        }

    usuario = usuario_autenticado(request)

    if usuario["rol"] != "administrador":
        return {
            "error": "No tienes permisos para realizar esta acción"
        }

    datos = await request.json()

    activo = datos.get("activo")

    if activo is None:
        return {
            "error": "Debes indicar el estado"
        }

    cambiar_estado_asesor(
        asesor_id,
        bool(activo)
    )

    return {
        "ok": True,
        "mensaje": "Estado del asesor actualizado"
    }
# ============================================================
# CLIENTES - LISTAR
# ============================================================
@app.get("/panel/api/clientes")
def listar_clientes(request: Request):
    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    clientes = obtener_clientes()

    return {
        "ok": True,
        "clientes": clientes
    }


# ============================================================
# CLIENTES - BUSCAR
# ============================================================
@app.get("/panel/api/clientes/buscar")
def buscar_clientes_panel(
    request: Request,
    q: str = ""
):
    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    q = q.strip()

    if not q:
        clientes = obtener_clientes()
    else:
        clientes = buscar_clientes(q)

    return {
        "ok": True,
        "clientes": clientes
    }


# ============================================================
# CLIENTES - OBTENER UNO
# ============================================================
@app.get("/panel/api/clientes/{cliente_id}")
def obtener_cliente_panel(
    cliente_id: int,
    request: Request
):
    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    cliente = obtener_cliente(cliente_id)

    if not cliente:
        return {
            "ok": False,
            "error": "Cliente no encontrado"
        }

    return {
        "ok": True,
        "cliente": cliente
    }


# ============================================================
# CLIENTES - AGREGAR
# ============================================================
@app.post("/panel/api/clientes")
async def registrar_cliente(request: Request):

    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    datos = await request.json()

    nombre = datos.get("nombre")
    telefono = datos.get("telefono")
    correo = datos.get("correo")
    tipo_cliente = datos.get("tipo_cliente")
    notas = datos.get("notas")

    if not nombre or not telefono:
        return {
            "ok": False,
            "error": "El nombre y el teléfono son obligatorios"
        }

    nombre = nombre.strip()
    telefono = telefono.strip()

    if correo:
        correo = correo.strip().lower()

    if tipo_cliente:
        tipo_cliente = tipo_cliente.strip()

    if notas:
        notas = notas.strip()

    cliente_id = agregar_cliente(
        nombre,
        telefono,
        correo,
        tipo_cliente,
        notas
    )

    if cliente_id is None:
        return {
            "ok": False,
            "error": "No se pudo agregar el cliente. "
                     "Verifica que el teléfono no esté registrado."
        }

    return {
        "ok": True,
        "mensaje": "Cliente agregado correctamente",
        "id": cliente_id
    }


# ============================================================
# CLIENTES - EDITAR
# ============================================================
@app.put("/panel/api/clientes/{cliente_id}")
async def actualizar_cliente_panel(
    cliente_id: int,
    request: Request
):

    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    datos = await request.json()

    nombre = datos.get("nombre")
    telefono = datos.get("telefono")
    correo = datos.get("correo")
    tipo_cliente = datos.get("tipo_cliente")
    notas = datos.get("notas")
    estado = datos.get("estado", "Activo")

    if not nombre or not telefono:
        return {
            "ok": False,
            "error": "El nombre y el teléfono son obligatorios"
        }

    resultado = editar_cliente(
        cliente_id,
        nombre.strip(),
        telefono.strip(),
        correo.strip().lower() if correo else None,
        tipo_cliente.strip() if tipo_cliente else None,
        notas.strip() if notas else None,
        estado
    )

    if not resultado:
        return {
            "ok": False,
            "error": "No se pudo actualizar el cliente"
        }

    return {
        "ok": True,
        "mensaje": "Cliente actualizado correctamente"
    }


# ============================================================
# CLIENTES - ELIMINAR
# ============================================================
@app.delete("/panel/api/clientes/{cliente_id}")
def borrar_cliente_panel(
    cliente_id: int,
    request: Request
):

    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    resultado = eliminar_cliente(cliente_id)

    if not resultado:
        return {
            "ok": False,
            "error": "No se pudo eliminar el cliente"
        }

    return {
        "ok": True,
        "mensaje": "Cliente eliminado correctamente"
    }


# ============================================================
# CLIENTES - CAMBIAR ESTADO
# ============================================================
@app.put("/panel/api/clientes/{cliente_id}/estado")
async def estado_cliente_panel(
    cliente_id: int,
    request: Request
):

    if not proteger_panel(request):
        return {"ok": False, "error": "No autenticado"}

    datos = await request.json()

    estado = datos.get("estado")

    if not estado:
        return {
            "ok": False,
            "error": "Debes indicar el estado"
        }

    resultado = cambiar_estado_cliente(
        cliente_id,
        estado
    )

    if not resultado:
        return {
            "ok": False,
            "error": "No se pudo cambiar el estado del cliente"
        }

    return {
        "ok": True,
        "mensaje": "Estado del cliente actualizado"
    }
# ============================================================
# CERRAR SESIÓN
# ============================================================

@app.get("/logout")
def cerrar_sesion(request: Request):

    usuario = request.session.get("usuario")

    if usuario:
        print(
            f"🚪 Sesión cerrada: "
            f"{usuario.get('correo')}"
        )

    request.session.clear()

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# ============================================================
# PANEL
# ============================================================

@app.get("/panel")
def panel(request: Request):

    if not proteger_panel(request):

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return FileResponse("panel/index.html")


# ============================================================
# PANEL - CONVERSACIONES
# ============================================================

@app.get("/panel/conversaciones")
def panel_conversaciones(request: Request):

    if not proteger_panel(request):

        return {
            "ok": False,
            "error": "No autenticado"
        }

    conversaciones = obtener_conversaciones()

    return {
        "conversaciones": conversaciones
    }


# ============================================================
# PANEL - HISTORIAL
# ============================================================

@app.get("/panel/conversaciones/{numero}")
def panel_historial(
    request: Request,
    numero: str
):

    if not proteger_panel(request):

        return {
            "ok": False,
            "error": "No autenticado"
        }

    historial = obtener_historial(numero)
    modo = obtener_modo_cliente(numero)

    return {
        "numero_cliente": numero,
        "modo": modo,
        "mensajes": historial
    }


# ============================================================
# PANEL - ENVIAR MENSAJE
# ============================================================

@app.post("/panel/enviar")
async def panel_enviar_mensaje(
    request: Request
):

    if not proteger_panel(request):

        return {
            "ok": False,
            "error": "No autenticado"
        }

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


# ============================================================
# PANEL - TOMAR CONVERSACIÓN
# ============================================================

@app.post("/panel/tomar")
async def panel_tomar(request: Request):

    if not proteger_panel(request):

        return {
            "ok": False,
            "error": "No autenticado"
        }

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


# ============================================================
# PANEL - DEVOLVER AL BOT
# ============================================================

@app.post("/panel/devolver-bot")
async def panel_devolver_bot(request: Request):

    if not proteger_panel(request):

        return {
            "ok": False,
            "error": "No autenticado"
        }

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
# ============================================================
# OCULTAR PANEL ASESORES
# ===========================================================
@app.get("/panel/api/sesion")
def obtener_sesion_panel(request: Request):

    if not proteger_panel(request):
        return {
            "autenticado": False
        }

    usuario = usuario_autenticado(request)

    if not usuario:
        return {
            "autenticado": False
        }

    return {
        "autenticado": True,
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "rol": usuario["rol"]
    }
# ============================================================
# VERIFICACIÓN DEL WEBHOOK
# ============================================================
@app.get("/webhook")
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)

    return PlainTextResponse("Token inválido", status_code=403)



# ============================================================
# RECIBIR MENSAJES
# ============================================================

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

        if numero in ASESORES:
            if tipo == "text":
                manejar_mensaje_asesor(numero, mensaje["text"]["body"])
            return {"status": "ok"}

        if tipo == "text":

            texto_recibido = mensaje["text"]["body"]

            guardar_mensaje(
                numero,
                "cliente",
                texto_recibido
            )

        modo_cliente = obtener_modo_cliente(numero)

        print("Modo del cliente:", modo_cliente)

        # ====================================================
        # CLIENTE EN ATENCIÓN CON ASESOR
        # ====================================================

        if modo_cliente == "ASESOR":

            print(
                f"👨‍💼 {numero} está en atención con un asesor."
            )

            return {"status": "ok"}

        # ====================================================
        # SOLO MENSAJES DE TEXTO
        # ====================================================

        if tipo != "text":

            print(
                "⚠️ Mensaje recibido que no es texto."
            )

            return {"status": "ok"}

        texto = mensaje["text"]["body"].strip().lower()

        print("Número:", numero)
        print("Texto:", texto)
        print("Estado actual:", estado_usuario.get(numero))

        if procesar_estado(numero, texto, texto_recibido):
            return {"status": "ok"}

        # ====================================================
        # MENÚ PRINCIPAL
        # ====================================================


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

        # ====================================================
        # OPCIÓN 1 - ARRIENDO
        # ====================================================

        elif texto == "1":

            mostrar_inmuebles(
                numero,
                "arriendo"
            )

        # ====================================================
        # OPCIÓN 2 - VENTA
        # ====================================================

        elif texto == "2":

            mostrar_inmuebles(
                numero,
                "venta"
            )

        # ====================================================
        # OPCIÓN 3 - PUBLICAR
        # ====================================================

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

        # ====================================================
        # OPCIÓN 4 - ASESOR
        # ====================================================

        elif texto == "4":

            notificar_asesores(numero)
            estado_usuario[numero] = "esperando_asesor"

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
        # ====================================================
                # OPCIÓN 5 - ASESOR
        # ====================================================

        elif texto == "5":
            estado_usuario[numero] = "menu_asesor"

            enviar_mensaje(
                numero,
                MENU_ASESOR
            )

        # ====================================================
        # VOLVER AL MENÚ
        # ====================================================

        elif texto == "0":

            enviar_mensaje(
                numero,
                MENU
            )

        # ====================================================
        # OPCIÓN DESCONOCIDA
        # ====================================================

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

        print(
            "❌ Error procesando mensaje:"
        )

        print(e)

    return {"status": "ok"}

# ============================================================
# SUBMENU OPCION 5  
# ============================================================
estado_usuario = {}

ASESORES = {
    "573003506602": "Mabel",
    "573229600482": "Cristian",
    "573118868664": "Andres",
}

solicitudes = {}                 # id -> {"cliente": numero, "asesor": None}
_contador = itertools.count(1)


def notificar_asesores(cliente):
    # Si ya tiene una solicitud pendiente, no duplicar
    for s in solicitudes.values():
        if s["cliente"] == cliente and s["asesor"] is None:
            return

    sid = next(_contador)
    solicitudes[sid] = {"cliente": cliente, "asesor": None}

    aviso = (
        f"🔔 *Nueva solicitud #{sid}*\n\n"
        f"Un cliente quiere hablar con un asesor.\n"
        f"📱 +{cliente}\n\n"
        f"Responde *TOMAR {sid}* para atenderlo."
    )
    for num in ASESORES:
        enviar_mensaje(num, aviso, guardar_como_bot=False)


def manejar_mensaje_asesor(asesor, texto):
    partes = texto.strip().lower().split()

    if not partes or partes[0] != "tomar":
        enviar_mensaje(asesor, "Para atender una solicitud responde: TOMAR <número>",
                       guardar_como_bot=False)
        return

    pendientes = [i for i, s in solicitudes.items() if s["asesor"] is None]

    if len(partes) > 1 and partes[1].isdigit():
        sid = int(partes[1])
    elif pendientes:
        sid = pendientes[0]
    else:
        enviar_mensaje(asesor, "No hay solicitudes pendientes.", guardar_como_bot=False)
        return

    sol = solicitudes.get(sid)

    if not sol:
        enviar_mensaje(asesor, "Esa solicitud no existe.", guardar_como_bot=False)
        return

    if sol["asesor"] is not None:
        enviar_mensaje(asesor, "😅 Otro asesor ya tomó esta solicitud.", guardar_como_bot=False)
        return

    # ✅ El primero que llega se la queda
    sol["asesor"] = asesor
    cliente = sol["cliente"]
    nombre = ASESORES[asesor]

    estado_usuario.pop(cliente, None)
    activar_asesor(cliente)      # el bot deja de responderle al cliente

    enviar_mensaje(
        asesor,
        f"✅ La solicitud #{sid} es tuya.\n\nCliente: +{cliente}\nChat directo: https://wa.me/{cliente}",
        guardar_como_bot=False
    )

    for num in ASESORES:
        if num != asesor:
            enviar_mensaje(num, f"ℹ️ La solicitud #{sid} ya fue tomada por {nombre}.",
                           guardar_como_bot=False)

    enviar_mensaje(cliente, f"👨‍💼 ¡Listo! {nombre} te atenderá en un momento.")

MENU_ASESOR = (
    "¿En qué te ayudamos?\n\n"
    "1️⃣ Enviar link del inmueble\n"
    "2️⃣ Agendar visita\n"
    "3️⃣ Volver al menú principal"
)

def procesar_estado(numero, texto, texto_original=None):
    """Devuelve True si el mensaje lo atendió el submenú del asesor."""
    estado = estado_usuario.get(numero)
    if not estado:
        return False

    # "0" siempre vuelve al menú principal
    if texto == "0":
        estado_usuario.pop(numero, None)
        enviar_mensaje(numero, MENU)
        return True

    if estado == "menu_asesor":
        if texto == "1":
            estado_usuario[numero] = "esperando_link"
            enviar_mensaje(numero, "Envíanos el link del inmueble que te interesa para poder ayudarte mejor.")
        elif texto == "2":
            estado_usuario[numero] = "esperando_visita"
            enviar_mensaje(numero, "¿qué día y hora te queda bien?")
        elif texto == "3":
            estado_usuario.pop(numero, None)
            enviar_mensaje(numero, MENU)
        else:
            enviar_mensaje(numero, "Opción no válida 😅\n\n" + MENU_ASESOR)
        return True

    if estado == "esperando_asesor":
        enviar_mensaje(
            numero,
            "⏳ Estamos buscando un asesor disponible, te atenderán en breve.\n\nSi quieres volver al menú escribe 0."
        )
        return True

    if estado == "esperando_link":
        estado_usuario[numero] = "menu_asesor"   # vuelve al submenú
        enviar_mensaje(
            numero,
            "¡Gracias! para agendar tu visita ingresa la opcion 2.\n\n" + MENU_ASESOR
        )
        return True

    if estado == "esperando_visita":
        estado_usuario[numero] = "menu_asesor"   # vuelve al submenú
        enviar_mensaje(
            numero,
            "Listo, registramos tu solicitud. Un asesor te confirmará la visita.\n\n" + MENU_ASESOR
        )
        return True

    return False


# ============================================================
# MOSTRAR INMUEBLES
# ============================================================

def mostrar_inmuebles(
    numero,
    tipo_operacion
):

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

        # ====================================================
        # MOSTRAR CADA INMUEBLE
        # ====================================================

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

        print(
            "❌ Error consultando inmuebles:"
        )

        print(e)

        enviar_mensaje(
            numero,
            """
⚠️ Ocurrió un problema consultando los inmuebles.

Por favor intenta nuevamente más tarde.

0️⃣ Volver al menú
"""
        )

# ============================================================
# ENVIAR MENSAJE A WHATSAPP
# ============================================================

def enviar_mensaje(
    numero,
    mensaje,
    guardar_como_bot=True
):

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

    print("ENVIANDO:", mensaje[:50])

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

# ============================================================
# VALIDAR CONTRASEÑA
# ============================================================

def validar_password(password):
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."

    if not re.search(r"[A-Z]", password):
        return False, "La contraseña debe contener al menos una letra mayúscula."

    if not re.search(r"[a-z]", password):
        return False, "La contraseña debe contener al menos una letra minúscula."

    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "La contraseña debe contener al menos un carácter especial."

    if re.search(r"\s", password):
        return False, "La contraseña no puede contener espacios."

    return True, None
