import os

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