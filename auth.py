from argon2 import PasswordHasher

ph = PasswordHasher()


def generar_hash(password):
    return ph.hash(password)


def verificar_password(password, password_hash):
    try:
        ph.verify(password_hash, password)
        return True
    except Exception:
        return False