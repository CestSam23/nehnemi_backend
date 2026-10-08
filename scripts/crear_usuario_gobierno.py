import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.models.usuario_gobierno import UsuarioGobierno
from app.services.contrasenas import generar_hash


def main():
    print("Crear usuario gubernamental")

    nombre = input("Nombre: ").strip()
    correo = input("Correo: ").strip().lower()
    rol = input(
        "Rol [ANALISTA/ADMINISTRADOR]: "
    ).strip().upper()

    if not nombre or not correo:
        print("Nombre y correo son obligatorios.")
        return

    if rol not in ("ANALISTA", "ADMINISTRADOR"):
        print("Rol no válido.")
        return

    contrasena = getpass.getpass("Contraseña: ")
    confirmacion = getpass.getpass(
        "Confirmar contraseña: "
    )

    if contrasena != confirmacion:
        print("Las contraseñas no coinciden.")
        return

    if len(contrasena) < 12:
        print("La contraseña debe tener al menos 12 caracteres.")
        return

    with SessionLocal() as db:
        existente = db.execute(
            select(UsuarioGobierno)
            .where(UsuarioGobierno.correo == correo)
        ).scalar_one_or_none()

        if existente:
            print("Ya existe un usuario con ese correo.")
            return

        usuario = UsuarioGobierno(
            nombre=nombre,
            correo=correo,
            contrasena_hash=generar_hash(contrasena),
            rol=rol,
            activo=True,
        )

        db.add(usuario)
        db.commit()
        db.refresh(usuario)

        print(f"Usuario creado: {usuario.id}")
        print(f"Rol: {usuario.rol}")


if __name__ == "__main__":
    main()