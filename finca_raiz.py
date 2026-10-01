import json
import os
import re
import sys
import psycopg2


# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME"),
    "user": os.environ.get("DB_USER"),
    "password": os.environ.get("DB_PASSWORD"),
    "host": os.environ.get("DB_HOST"),
    "port": os.environ.get("DB_PORT"),
}


# ID DE LA PLATAFORMA
# 1 = Finca Raíz
PLATAFORMA_ID = 1


RUTA_JSON_POR_DEFECTO = "inmuebles_export.json"


# ============================================================
# PATRONES
# ============================================================

PATRON_PRECIO = re.compile(r"(?:\$|COP)\s*([\d.,]+)")
PATRON_ID_EN_HREF = re.compile(r"/detalle/(\d+)")


# ============================================================
# ESTADOS
# ============================================================

ESTADOS_CONOCIDOS = {
    "activo": "Activo",
    "inactivo": "Inactivo",
    "pausado": "Inactivo",
    "desactivado": "Inactivo",
    "vendido": "Vendido/Arrendado",
    "arrendado": "Vendido/Arrendado",
    "finalizado": "Vendido/Arrendado",
}


# ============================================================
# VISIBILIDAD
# ============================================================

def extraer_visibilidad(puntos_color):

    for punto in puntos_color:

        clase = punto.get("clase", "") or ""
        ancho = punto.get("ancho", 0)

        if "rounded-full" in clase and 15 <= ancho <= 25:

            color = punto.get("color", "")

            match = re.search(
                r"rgb\((\d+),\s*(\d+),\s*(\d+)\)",
                color
            )

            if match:

                r, g, b = (
                    int(x)
                    for x in match.groups()
                )

                if g > r and g > b:
                    return "Visible"

                if r > g and r > b:
                    return "Oculto"

                return "Desconocido"

            return "Desconocido"

    return "Desconocido"


# ============================================================
# DETECTAR BLOQUE DE INMUEBLE
# ============================================================

def es_bloque_de_inmueble(texto):

    return (
        "Publicado el" in texto
        and "$" in texto
    )


# ============================================================
# EXTRAER CÓDIGO
# ============================================================

def extraer_codigo(lineas):

    if (
        lineas
        and lineas[-1].isdigit()
        and len(lineas[-1]) >= 6
    ):
        return lineas[-1]

    candidatos = [
        linea
        for linea in lineas
        if linea.isdigit()
        and len(linea) >= 6
    ]

    if candidatos:

        return max(
            candidatos,
            key=len
        )

    return None


# ============================================================
# EXTRAER TÍTULO
# ============================================================

def extraer_titulo(lineas):

    for i, linea in enumerate(lineas):

        if (
            linea.startswith("Publicado el")
            and i > 0
        ):
            return lineas[i - 1]

    for linea in lineas:

        if not linea.isdigit():

            return linea

    return "Sin título"


# ============================================================
# EXTRAER PRECIO
# ============================================================

def extraer_precio(lineas):

    for linea in lineas:

        if "$" in linea or "COP" in linea:

            match = PATRON_PRECIO.search(linea)

            if match:

                numero = (
                    match.group(1)
                    .replace(".", "")
                    .replace(",", "")
                )

                if numero.isdigit():

                    return float(numero)

    return 0.0


# ============================================================
# EXTRAER ESTADO
# ============================================================

def extraer_estado(lineas):

    for linea in lineas:

        estado = ESTADOS_CONOCIDOS.get(
            linea.strip().lower()
        )

        if estado:

            return estado

    return "Activo"


# ============================================================
# CONSTRUIR MAPA ID -> URL
# ============================================================

def construir_mapa_id_href(elementos):

    mapa = {}

    for elemento in elementos:

        href = elemento.get("href", "")

        match = PATRON_ID_EN_HREF.search(href)

        if match:

            mapa[match.group(1)] = href

    return mapa


# ============================================================
# PROCESAR JSON
# ============================================================

def procesar_json(ruta_json):

    with open(
        ruta_json,
        "r",
        encoding="utf-8"
    ) as archivo:

        elementos = json.load(archivo)


    mapa_id_href = construir_mapa_id_href(
        elementos
    )


    publicaciones = []

    codigos_vistos = set()


    for elemento in elementos:

        texto = elemento.get(
            "texto",
            ""
        )

        url_pagina = elemento.get(
            "url_pagina",
            ""
        )


        if not es_bloque_de_inmueble(texto):

            continue


        lineas = [
            linea.strip()
            for linea in texto.split("\n")
            if linea.strip()
        ]


        codigo_id = extraer_codigo(
            lineas
        )


        if not codigo_id:

            print(
                "⚠️ No se pudo determinar "
                "el ID de un inmueble."
            )

            continue


        if codigo_id in codigos_vistos:

            continue


        codigos_vistos.add(
            codigo_id
        )


        titulo = extraer_titulo(
            lineas
        )

        precio = extraer_precio(
            lineas
        )

        estado = extraer_estado(
            lineas
        )

        visibilidad = extraer_visibilidad(
            elemento.get(
                "puntos_color",
                []
            )
        )


        url = mapa_id_href.get(
            codigo_id,
            url_pagina
        )


        publicaciones.append({

            "codigo_externo": codigo_id,

            "titulo": titulo,

            "precio": precio,

            "moneda": "COP",

            "estado": estado,

            "visibilidad": visibilidad,

            "url": url,

        })


    return publicaciones


# ============================================================
# SINCRONIZAR CON POSTGRESQL
# ============================================================

def sincronizar_base_datos(publicaciones):

    try:

        conexion = psycopg2.connect(
            **DB_CONFIG
        )

    except psycopg2.OperationalError as error:

        print(
            "❌ No se pudo conectar a PostgreSQL:"
        )

        print(error)

        return False


    try:

        cursor = conexion.cursor()


        # ----------------------------------------------------
        # Códigos encontrados en la captura actual
        # ----------------------------------------------------

        codigos_actuales = {
            pub["codigo_externo"]
            for pub in publicaciones
        }


        # ----------------------------------------------------
        # INSERTAR / ACTUALIZAR
        # ----------------------------------------------------

        nuevos = 0
        actualizados = 0


        for pub in publicaciones:

            codigo = pub["codigo_externo"]


            # Comprobar si ya existe
            cursor.execute(
                """
                SELECT id_publicacion
                FROM publicaciones
                WHERE codigo_externo = %s
                  AND id_plataforma = %s;
                """,
                (
                    codigo,
                    PLATAFORMA_ID
                )
            )


            existe = cursor.fetchone()


            if existe:

                # ------------------------------------------
                # ACTUALIZAR
                # ------------------------------------------

                cursor.execute(
                    """
                    UPDATE publicaciones
                    SET
                        titulo = %s,
                        precio = %s,
                        moneda = %s,
                        estado = %s,
                        visibilidad = %s,
                        url_anuncio = %s,
                        fecha_ultima_captura = NOW()
                    WHERE codigo_externo = %s
                      AND id_plataforma = %s;
                    """,
                    (
                        pub["titulo"],
                        pub["precio"],
                        pub["moneda"],
                        pub["estado"],
                        pub["visibilidad"],
                        pub["url"],
                        codigo,
                        PLATAFORMA_ID
                    )
                )

                actualizados += 1


            else:

                # ------------------------------------------
                # INSERTAR
                # ------------------------------------------

                cursor.execute(
                    """
                    INSERT INTO publicaciones
                    (
                        id_plataforma,
                        codigo_externo,
                        titulo,
                        precio,
                        moneda,
                        estado,
                        visibilidad,
                        url_anuncio,
                        fecha_ultima_captura
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW()
                    );
                    """,
                    (
                        PLATAFORMA_ID,
                        codigo,
                        pub["titulo"],
                        pub["precio"],
                        pub["moneda"],
                        pub["estado"],
                        pub["visibilidad"],
                        pub["url"]
                    )
                )

                nuevos += 1


        # ----------------------------------------------------
        # MARCAR COMO INACTIVOS LOS QUE YA NO APARECEN
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT codigo_externo
            FROM publicaciones
            WHERE id_plataforma = %s;
            """,
            (PLATAFORMA_ID,)
        )


        codigos_db = {
            fila[0]
            for fila in cursor.fetchall()
        }


        desaparecidos = (
            codigos_db
            - codigos_actuales
        )


        for codigo in desaparecidos:

            cursor.execute(
                """
                UPDATE publicaciones
                SET
                    estado = 'Inactivo',
                    visibilidad = 'Oculto',
                    fecha_ultima_captura = NOW()
                WHERE codigo_externo = %s
                  AND id_plataforma = %s
                  AND estado = 'Activo';
                """,
                (
                    codigo,
                    PLATAFORMA_ID
                )
            )


        conexion.commit()


        print()
        print("=" * 60)
        print("✅ SINCRONIZACIÓN COMPLETADA")
        print("=" * 60)

        print(
            f"📥 Nuevos: {nuevos}"
        )

        print(
            f"🔄 Actualizados: {actualizados}"
        )

        print(
            f"🚫 Ya no aparecen: {len(desaparecidos)}"
        )

        print(
            f"📊 Total procesados: {len(publicaciones)}"
        )

        print("=" * 60)


        return True


    except Exception as error:

        conexion.rollback()

        print(
            "❌ Error durante la sincronización:"
        )

        print(error)

        return False


    finally:

        cursor.close()

        conexion.close()


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def main():

    if len(sys.argv) > 1:

        ruta_json = sys.argv[1]

    else:

        ruta_json = RUTA_JSON_POR_DEFECTO


    if not os.path.exists(ruta_json):

        print(
            f"❌ No se encontró el archivo:"
            f" '{ruta_json}'"
        )

        print()

        print(
            "Debes colocar "
            "inmuebles_export.json "
            "en la carpeta desde donde ejecutas "
            "el script."
        )

        return


    print()
    print("=" * 60)
    print("🏠 ACTUALIZADOR FINCA RAÍZ")
    print("=" * 60)

    print(
        f"📂 Archivo: {ruta_json}"
    )


    # --------------------------------------------------------
    # PROCESAR JSON
    # --------------------------------------------------------

    publicaciones = procesar_json(
        ruta_json
    )


    if not publicaciones:

        print()
        print(
            "⚠️ No se encontraron inmuebles."
        )

        print(
            "Revisa el archivo JSON."
        )

        return


    print()
    print(
        f"🔍 Inmuebles detectados: "
        f"{len(publicaciones)}"
    )


    # --------------------------------------------------------
    # SINCRONIZAR
    # --------------------------------------------------------

    sincronizar_base_datos(
        publicaciones
    )


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    main()