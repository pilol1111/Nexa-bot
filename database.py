import os
from datetime import datetime, timedelta
import psycopg2


# ==========================================
# CONFIGURACIÓN BASE DE DATOS
# ==========================================

DATABASE_URL = os.getenv("DATABASE_URL")


# ==========================================
# CONEXIÓN
# ==========================================

def obtener_conexion():

    #Railway
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)

    # Local
    return psycopg2.connect(
        dbname="inmuebles_db",
        user="postgres",
        password="1221",
        host="localhost",
        port="5432"




    )    


# ==========================================
# OBTENER INMUEBLES
# ==========================================

def obtener_inmuebles(tipo_operacion):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        if tipo_operacion.lower() == "arriendo":
            filtro = "%Arriendo%"

        elif tipo_operacion.lower() == "venta":
            filtro = "%Venta%"

        else:
            return []

        consulta = """
            SELECT
                id_publicacion,
                titulo,
                precio,
                moneda,
                estado,
                url_anuncio
            FROM publicaciones
            WHERE estado = 'Activo'
              AND visibilidad <> 'Oculto'
              AND titulo ILIKE %s
            ORDER BY id_publicacion DESC;
        """

        cursor.execute(
            consulta,
            (filtro,)
        )

        resultados = cursor.fetchall()

        return resultados

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# OBTENER MODO DEL CLIENTE
# ==========================================

def obtener_modo_cliente(numero):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT modo
            FROM conversaciones
            WHERE numero_cliente = %s;
        """

        cursor.execute(
            consulta,
            (numero,)
        )

        resultado = cursor.fetchone()

        # Cliente nuevo
        if resultado is None:

            consulta_insertar = """
                INSERT INTO conversaciones
                (
                    numero_cliente,
                    modo
                )
                VALUES (%s, 'BOT')
                ON CONFLICT (numero_cliente)
                DO NOTHING;
            """

            cursor.execute(
                consulta_insertar,
                (numero,)
            )

            conexion.commit()

            return "BOT"

        return resultado[0]

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# ACTIVAR MODO ASESOR
# ==========================================

def activar_asesor(numero):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            INSERT INTO conversaciones
            (
                numero_cliente,
                modo
            )
            VALUES (%s, 'ASESOR')

            ON CONFLICT (numero_cliente)
            DO UPDATE SET
                modo = 'ASESOR',
                fecha_ultima_actualizacion = NOW();
        """

        cursor.execute(
            consulta,
            (numero,)
        )

        conexion.commit()

        print(
            f"👨‍💼 Cliente {numero} pasó a modo ASESOR"
        )

        return True

    except Exception as e:

        conexion.rollback()

        print(
            "❌ Error activando modo asesor:"
        )

        print(e)

        return False

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# ACTIVAR MODO BOT
# ==========================================

def activar_bot(numero):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            INSERT INTO conversaciones
            (
                numero_cliente,
                modo
            )
            VALUES (%s, 'BOT')

            ON CONFLICT (numero_cliente)
            DO UPDATE SET
                modo = 'BOT',
                fecha_ultima_actualizacion = NOW();
        """

        cursor.execute(
            consulta,
            (numero,)
        )

        conexion.commit()

        print(
            f"🤖 Cliente {numero} volvió a modo BOT"
        )

        return True

    except Exception as e:

        conexion.rollback()

        print(
            "❌ Error activando modo bot:"
        )

        print(e)

        return False

    finally:

        cursor.close()
        conexion.close()

# ==========================================
# GUARDAR MENSAJE
# ==========================================

def guardar_mensaje(numero, remitente, mensaje, asesor_id=None):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            INSERT INTO mensajes
            (
                numero_cliente,
                remitente,
                mensaje,
                asesor_id
            )
            VALUES (%s, %s, %s, %s);
        """

        cursor.execute(
            consulta,
            (
                numero,
                remitente,
                mensaje,
                asesor_id
            )
        )

        conexion.commit()

        print ("Mensaje guardado exitosamente en la base de datos.")

    except Exception as e:

        conexion.rollback()

        print("❌ Error guardando mensaje:")
        print(e)

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# OBTENER MENSAJES DE UNA CONVERSACIÓN
# ==========================================

def obtener_mensajes(numero):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                id_mensaje,
                numero_cliente,
                remitente,
                mensaje,
                fecha_hora,
                asesor_id
            FROM mensajes
            WHERE numero_cliente = %s
            ORDER BY fecha_hora ASC;
        """

        cursor.execute(
            consulta,
            (numero,)
        )

        return cursor.fetchall()

    finally:

        cursor.close()
        conexion.close()

# ==========================================
# OBTENER CONVERSACIONES
# ==========================================

def obtener_conversaciones():

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                c.numero_cliente,
                c.modo,
                c.fecha_ultima_actualizacion,
                (
                    SELECT m.id_mensaje
                    FROM mensajes m
                    WHERE m.numero_cliente = c.numero_cliente
                    ORDER BY m.fecha_hora DESC
                    LIMIT 1
                ) AS ultimo_mensaje
            FROM conversaciones c
            ORDER BY c.fecha_ultima_actualizacion DESC;
        """

        cursor.execute(consulta)

        return cursor.fetchall()

    finally:

        cursor.close()
        conexion.close()

# ==========================================
# OBTENER HISTORIAL DE MENSAJES
# ==========================================

def obtener_historial(numero):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                id_mensaje,
                numero_cliente,
                remitente,
                mensaje,
                fecha_hora,
                asesor_id
            FROM mensajes
            WHERE numero_cliente = %s
            ORDER BY fecha_hora ASC;
        """

        cursor.execute(
            consulta,
            (numero,)
        )

        return cursor.fetchall()

    finally:

        cursor.close()
        conexion.close()


def obtener_usuario_por_correo(correo):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            """
            SELECT
                id,
                nombre,
                correo,
                password_hash,
                rol,
                activo
            FROM usuarios
            WHERE correo = %s
            LIMIT 1
            """,
            (correo,)
        )

        fila = cursor.fetchone()

        if not fila:
            return None

        return {
            "id": fila[0],
            "nombre": fila[1],
            "correo": fila[2],
            "password_hash": fila[3],
            "rol": fila[4],
            "activo": fila[5]
        }

    finally:
        cursor.close()
        conexion.close()

def enviar_mensaje_asesor(numero, mensaje, asesor_id=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        consulta = """
            INSERT INTO mensajes
            (
                numero_cliente,
                remitente,
                mensaje,
                asesor_id
            )
            VALUES (%s, 'ASESOR', %s, %s);
        """

        cursor.execute(
            consulta,
            (numero, mensaje, asesor_id)
        )
        

        conexion.commit()

        print(f"👨‍💼 Mensaje del asesor guardado para {numero}")

        return True

    except Exception as e:
        conexion.rollback()
        print("❌ Error guardando mensaje del asesor:")
        print(e)
        return False

    finally:
        cursor.close()
        conexion.close()

def guardar_token_recuperacion(usuario_id, token_hash):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        # Invalidar tokens anteriores del mismo usuario
        cursor.execute(
            """
            UPDATE recuperacion_password
            SET usado = TRUE
            WHERE usuario_id = %s
              AND usado = FALSE
            """,
            (usuario_id,)
        )

        # Nuevo token válido durante 30 minutos
        fecha_expiracion = datetime.now() + timedelta(minutes=30)

        cursor.execute(
            """
            INSERT INTO recuperacion_password
            (
                usuario_id,
                token_hash,
                fecha_expiracion
            )
            VALUES (%s, %s, %s)
            """,
            (
                usuario_id,
                token_hash,
                fecha_expiracion
            )
        )

        conexion.commit()

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()

def obtener_token_recuperacion(token_hash):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT
                id,
                usuario_id,
                fecha_expiracion,
                usado
            FROM recuperacion_password
            WHERE token_hash = %s
            """,
            (token_hash,)
        )

        resultado = cursor.fetchone()

        if not resultado:
            return None

        return {
            "id": resultado[0],
            "usuario_id": resultado[1],
            "fecha_expiracion": resultado[2],
            "usado": resultado[3]
        }

    finally:
        cursor.close()
        conexion.close()


def marcar_token_usado(token_id):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            UPDATE recuperacion_password
            SET usado = TRUE
            WHERE id = %s
            """,
            (token_id,)
        )

        conexion.commit()

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()


def actualizar_password(usuario_id, password_hash):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            UPDATE usuarios
            SET password_hash = %s
            WHERE id = %s
            """,
            (password_hash, usuario_id)
        )

        conexion.commit()

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()
def crear_asesor(nombre, correo, password_hash):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            INSERT INTO usuarios
            (
                nombre,
                correo,
                password_hash,
                rol,
                activo
            )
            VALUES (%s, %s, %s, 'asesor', TRUE)
            RETURNING id
            """,
            (
                nombre,
                correo,
                password_hash
            )
        )

        asesor_id = cursor.fetchone()[0]

        conexion.commit()

        return asesor_id

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()


def obtener_asesores():
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            SELECT
                id,
                nombre,
                correo,
                rol,
                activo,
                fecha_creacion
            FROM usuarios
            WHERE rol = 'asesor'
            ORDER BY nombre ASC
            """
        )

        resultados = cursor.fetchall()

        asesores = []

        for fila in resultados:
            asesores.append({
                "id": fila[0],
                "nombre": fila[1],
                "correo": fila[2],
                "rol": fila[3],
                "activo": fila[4],
                "fecha_creacion": fila[5]
            })

        return asesores

    finally:
        cursor.close()
        conexion.close()


def cambiar_estado_asesor(asesor_id, activo):
    conexion = obtener_conexion()

    try:
        cursor = conexion.cursor()

        cursor.execute(
            """
            UPDATE usuarios
            SET activo = %s
            WHERE id = %s
              AND rol = 'asesor'
            """,
            (
                activo,
                asesor_id
            )
        )

        conexion.commit()

    except Exception:
        conexion.rollback()
        raise

    finally:
        cursor.close()
        conexion.close()
# ==========================================
# CLIENTES
# ==========================================

def agregar_cliente(nombre, telefono, correo=None, tipo_cliente=None, notas=None):
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        consulta = """
            INSERT INTO clientes
            (
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """

        cursor.execute(
            consulta,
            (
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas
            )
        )

        cliente_id = cursor.fetchone()[0]

        conexion.commit()

        print(f"👤 Cliente {nombre} agregado correctamente")

        return cliente_id

    except Exception as e:
        conexion.rollback()

        print("❌ Error agregando cliente:")
        print(e)

        return None

    finally:
        cursor.close()
        conexion.close()


# ==========================================
# OBTENER TODOS LOS CLIENTES
# ==========================================

def obtener_clientes():

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                id,
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas,
                estado,
                fecha_registro
            FROM clientes
            ORDER BY fecha_registro DESC;
        """

        cursor.execute(consulta)

        resultados = cursor.fetchall()

        clientes = []

        for fila in resultados:

            clientes.append({
                "id": fila[0],
                "nombre": fila[1],
                "telefono": fila[2],
                "correo": fila[3],
                "tipo_cliente": fila[4],
                "notas": fila[5],
                "estado": fila[6],
                "fecha_registro": fila[7]
            })

        return clientes

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# OBTENER UN CLIENTE
# ==========================================

def obtener_cliente(cliente_id):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                id,
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas,
                estado,
                fecha_registro
            FROM clientes
            WHERE id = %s
            LIMIT 1;
        """

        cursor.execute(
            consulta,
            (cliente_id,)
        )

        fila = cursor.fetchone()

        if not fila:
            return None

        return {
            "id": fila[0],
            "nombre": fila[1],
            "telefono": fila[2],
            "correo": fila[3],
            "tipo_cliente": fila[4],
            "notas": fila[5],
            "estado": fila[6],
            "fecha_registro": fila[7]
        }

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# BUSCAR CLIENTES
# ==========================================

def buscar_clientes(texto):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            SELECT
                id,
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas,
                estado,
                fecha_registro
            FROM clientes
            WHERE
                nombre ILIKE %s
                OR telefono ILIKE %s
                OR correo ILIKE %s
            ORDER BY nombre ASC;
        """

        filtro = f"%{texto}%"

        cursor.execute(
            consulta,
            (
                filtro,
                filtro,
                filtro
            )
        )

        resultados = cursor.fetchall()

        clientes = []

        for fila in resultados:

            clientes.append({
                "id": fila[0],
                "nombre": fila[1],
                "telefono": fila[2],
                "correo": fila[3],
                "tipo_cliente": fila[4],
                "notas": fila[5],
                "estado": fila[6],
                "fecha_registro": fila[7]
            })

        return clientes

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# EDITAR CLIENTE
# ==========================================

def editar_cliente(
    cliente_id,
    nombre,
    telefono,
    correo=None,
    tipo_cliente=None,
    notas=None,
    estado="Activo"
):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            UPDATE clientes
            SET
                nombre = %s,
                telefono = %s,
                correo = %s,
                tipo_cliente = %s,
                notas = %s,
                estado = %s
            WHERE id = %s;
        """

        cursor.execute(
            consulta,
            (
                nombre,
                telefono,
                correo,
                tipo_cliente,
                notas,
                estado,
                cliente_id
            )
        )

        conexion.commit()

        return True

    except Exception as e:

        conexion.rollback()

        print("❌ Error editando cliente:")
        print(e)

        return False

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# ELIMINAR CLIENTE
# ==========================================

def eliminar_cliente(cliente_id):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            DELETE FROM clientes
            WHERE id = %s;
        """

        cursor.execute(
            consulta,
            (cliente_id,)
        )

        conexion.commit()

        return True

    except Exception as e:

        conexion.rollback()

        print("❌ Error eliminando cliente:")
        print(e)

        return False

    finally:

        cursor.close()
        conexion.close()


# ==========================================
# CAMBIAR ESTADO DEL CLIENTE
# ==========================================

def cambiar_estado_cliente(cliente_id, estado):

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:

        consulta = """
            UPDATE clientes
            SET estado = %s
            WHERE id = %s;
        """

        cursor.execute(
            consulta,
            (
                estado,
                cliente_id
            )
        )

        conexion.commit()

        return True

    except Exception as e:

        conexion.rollback()

        print("❌ Error cambiando estado del cliente:")
        print(e)

        return False

    finally:

        cursor.close()
        conexion.close()