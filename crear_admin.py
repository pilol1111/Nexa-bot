from database import obtener_conexion
from auth import generar_hash


def crear_admin():
    nombre = input("Nombre del administrador: ").strip()
    correo = input("Correo electrónico: ").strip().lower()
    password = input("Contraseña: ")

    if not nombre or not correo or not password:
        print("❌ Todos los campos son obligatorios.")
        return

    password_hash = generar_hash(password)

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO usuarios
                (nombre, correo, password_hash, rol)
            VALUES
                (%s, %s, %s, %s)
            """,
            (nombre, correo, password_hash, "administrador")
        )

        conexion.commit()

        print("\n✅ Administrador creado correctamente.")
        print(f"👤 Nombre: {nombre}")
        print(f"📧 Correo: {correo}")
        print("🔐 Contraseña: almacenada mediante Argon2id")
        print("👑 Rol: administrador")

    except Exception as e:
        conexion.rollback()
        print(f"\n❌ No se pudo crear el administrador: {e}")

    finally:
        cursor.close()
        conexion.close()


if __name__ == "__main__":
    crear_admin()