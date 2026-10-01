import asyncio
import json
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL_INMUEBLES = (
    "https://ov.fincaraiz.com.co/"
    "inmobiliarias/administrar-inmuebles?pagina=1"
)

ARCHIVO_JSON = Path("inmuebles_export.json")

# Carpeta donde Playwright guardará la sesión.
# NO contiene tu contraseña.
PERFIL_NAVEGADOR = Path("fincaraiz_session")


# ============================================================
# EXTRACTOR
# ============================================================

SCRIPT_EXTRACTOR = r"""
() => {

    const resultados = [];
    const vistos = new Set();

    /*
     * Buscamos directamente los elementos que contienen
     * información de inmuebles.
     */
    const elementos = document.querySelectorAll(
        'tr, div[class*="card"], div[class*="item"], div[class*="property"]'
    );

    elementos.forEach((elem, index) => {

        const texto = (elem.innerText || "").trim();

        if (!texto) return;

        const lineas = texto
            .split("\n")
            .map(l => l.trim())
            .filter(l => l.length > 0);

        if (lineas.length < 2) return;

        /*
         * Solo nos interesan bloques que realmente
         * contengan propiedades.
         */
        const contieneInmueble = lineas.some(linea =>
            /^(Apartamento|Casa|Apartaestudio|Local|Oficina|Bodega|Lote|Finca) en /i.test(linea)
        );

        if (!contieneInmueble) return;

        /*
         * Evitar duplicados.
         */
        const clave = texto.substring(0, 200);

        if (vistos.has(clave)) return;

        vistos.add(clave);

        /*
         * Buscar enlace.
         */
        const linkElem = elem.querySelector("a[href]");

        const href = linkElem
            ? linkElem.href
            : "";

        /*
         * Guardar pistas útiles.
         */
        const pistas = [];

        elem.querySelectorAll(
            '[title], [aria-label], [alt], input[type="checkbox"], svg'
        ).forEach(node => {

            const info = {
                tag: node.tagName,
                title: node.getAttribute("title") || undefined,
                ariaLabel: node.getAttribute("aria-label") || undefined,
                alt: node.getAttribute("alt") || undefined,
                clase:
                    typeof node.className === "string"
                        ? node.className
                        : undefined,
                checked:
                    node.tagName === "INPUT"
                        ? node.checked
                        : undefined
            };

            if (
                info.title ||
                info.ariaLabel ||
                info.alt ||
                info.checked !== undefined
            ) {
                pistas.push(info);
            }
        });

        resultados.push({
            index: index,
            texto: texto,
            href: href,
            pistas: pistas,
            puntos_color: [],
            url_pagina: window.location.href
        });
    });

    return resultados;
}
"""


# ============================================================
# AUTOMATIZACIÓN
# ============================================================

async def ejecutar():

    print("=" * 60)
    print("🏠 AUTOMATIZADOR FINCA RAÍZ")
    print("=" * 60)

    async with async_playwright() as p:

        print()
        print("🌐 Abriendo navegador...")

        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PERFIL_NAVEGADOR),
            headless=False,
            viewport={
                "width": 1400,
                "height": 900
            }
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print()
        print("📍 Abriendo Oficina Virtual de Finca Raíz...")

        await page.goto(
            URL_INMUEBLES,
            wait_until="domcontentloaded",
            timeout=120000
        )

        await page.wait_for_timeout(5000)

        print()
        print("🔎 URL actual:")
        print(page.url)

        # ====================================================
        # DETECTAR SI HAY SESIÓN
        # ====================================================

        url_actual = page.url.lower()

        if "login" in url_actual or "iniciar" in url_actual:

            print()
            print("🔐 No hay una sesión guardada.")
            print()
            print("Inicia sesión MANUALMENTE en Finca Raíz.")
            print("Cuando termines, vuelve aquí.")
            print()

            input(
                "👉 Presiona ENTER cuando hayas iniciado sesión..."
            )

            await page.goto(
                URL_INMUEBLES,
                wait_until="domcontentloaded",
                timeout=120000
            )

            await page.wait_for_timeout(5000)

        # ====================================================
        # ESPERAR EL LISTADO
        # ====================================================

        print()
        print("⏳ Esperando que carguen los inmuebles...")

        await page.wait_for_timeout(5000)

        print()
        print("📄 Extrayendo información...")

        resultados = await page.evaluate(
            SCRIPT_EXTRACTOR
        )

        # ====================================================
        # COMPROBAR RESULTADOS
        # ====================================================

        if not resultados:

            print()
            print("❌ No se encontraron inmuebles.")
            print()
            print("URL:")
            print(page.url)

            await context.close()
            return

        print()
        print(
            f"🔍 Elementos encontrados: {len(resultados)}"
        )

        # ====================================================
        # GUARDAR JSON
        # ====================================================

        with open(
            ARCHIVO_JSON,
            "w",
            encoding="utf-8"
        ) as archivo:

            json.dump(
                resultados,
                archivo,
                ensure_ascii=False,
                indent=2
            )

        print()
        print(
            f"💾 JSON guardado: {ARCHIVO_JSON}"
        )

        # ====================================================
        # MOSTRAR ALGUNOS RESULTADOS
        # ====================================================

        print()
        print("-" * 60)

        for elemento in resultados:

            texto = elemento.get("texto", "")

            for linea in texto.splitlines():

                linea = linea.strip()

                if (
                    "Apartamento en " in linea
                    or "Casa en " in linea
                    or "Apartaestudio en " in linea
                    or "Local en " in linea
                    or "Oficina en " in linea
                    or "Bodega en " in linea
                    or "Lote en " in linea
                    or "Finca en " in linea
                ):

                    print("🏠", linea)
                    break

        print("-" * 60)

        # ====================================================
        # CERRAR NAVEGADOR
        # ====================================================

        await context.close()

    # ========================================================
    # EJECUTAR ACTUALIZADOR
    # ========================================================

    print()
    print("🔄 Ejecutando sincronizador PostgreSQL...")
    print()

    actualizador = Path("finca_raiz.py")

    if not actualizador.exists():

        print(
            "⚠️ No se encontró finca_raiz.py"
        )

        print()
        print(
            "El JSON sí fue generado correctamente."
        )

        return

    resultado = subprocess.run(
        ["python", str(actualizador)],
        capture_output=False
    )

    print()

    if resultado.returncode == 0:

        print("=" * 60)
        print("✅ SINCRONIZACIÓN AUTOMÁTICA COMPLETADA")
        print("=" * 60)

    else:

        print("=" * 60)
        print("❌ EL ACTUALIZADOR TERMINÓ CON ERROR")
        print("=" * 60)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    asyncio.run(ejecutar())