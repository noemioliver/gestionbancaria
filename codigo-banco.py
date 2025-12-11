import json
import os
from datetime import datetime, timedelta

BD = "usuarios.json"

def cargar_bd():
    if not os.path.exists(BD):
        with open(BD, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
    with open(BD, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_bd(data):
    with open(BD, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def crear_usuario():
    data = cargar_bd()
    nombre = input("Nombre: ")
    dni = input("DNI: ")
    contraseña = input("Contraseña: ")

    for u in data:
        if u["dni"] == dni:
            print("Ese DNI ya está registrado.")
            return

    hoy = datetime.now().strftime("%Y-%m-%d")

    nuevo = {
        "nombre": nombre,
        "dni": dni,
        "password": contraseña,
        "saldo": 0,
        "historial": [],
        "pendientes": [],
        "cobradores": [],
        "bloqueado_hasta": "",
        "creado": hoy
    }

    data.append(nuevo)
    guardar_bd(data)
    print("Cuenta creada correctamente.")

def verificar_bloqueo(usuario):
    if usuario["bloqueado_hasta"] == "":
        return False
    hoy = datetime.now().strftime("%Y-%m-%d")
    return hoy < usuario["bloqueado_hasta"]

def iniciar_sesion():
    data = cargar_bd()
    dni = input("DNI: ")
    usuario = None
    for u in data:
        if u["dni"] == dni:
            usuario = u
            break
    if usuario is None:
        print("No existe un usuario con ese DNI.")
        return None, data

    if verificar_bloqueo(usuario):
        print("Agotaste tus intentos, vuelva otro día.")
        return None, data

    intentos = 3
    while intentos > 0:
        pw = input("Contraseña: ")
        if pw == usuario["password"]:
            procesar_pendientes(usuario, data)
            procesar_cobros_automaticos(usuario, data)
            procesar_cobro_semanal(usuario, data)
            guardar_bd(data)
            return usuario, data
        intentos -= 1

    mañana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    usuario["bloqueado_hasta"] = mañana
    guardar_bd(data)
    print("Agotaste tus intentos, vuelva otro día.")
    return None, data

def procesar_pendientes(usuario, data):
    if not usuario["pendientes"]:
        return
    print("\nTienes dinero pendiente de aceptar:")
    for p in usuario["pendientes"][:]:
        print(f"De: {p['from']} | Cantidad: {p['cantidad']} €")
        op = input("¿Aceptar? (s/n): ")
        if op.lower() == "s":
            usuario["saldo"] += p["cantidad"]
            usuario["historial"].append(f"{datetime.now().strftime('%Y-%m-%d')}: Recibido de {p['from']} {p['cantidad']} €")
        else:
            for u in data:
                if u["dni"] == p["from"]:
                    u["saldo"] += p["cantidad"]
                    u["historial"].append(f"{datetime.now().strftime('%Y-%m-%d')}: Reembolso de {usuario['dni']} {p['cantidad']} €")
        usuario["pendientes"].remove(p)

def enviar_dinero(usuario, data):
    pw = input("Contraseña para confirmar: ")
    if pw != usuario["password"]:
        print("Contraseña incorrecta.")
        return
    dni_dest = input("DNI destinatario: ")
    cantidad = float(input("Cantidad: "))

    if usuario["saldo"] < cantidad:
        print("Saldo insuficiente.")
        return

    destino = None
    for u in data:
        if u["dni"] == dni_dest:
            destino = u
            break
    if destino is None:
        print("No existe ese usuario.")
        return

    usuario["saldo"] -= cantidad
    fecha = datetime.now().strftime("%Y-%m-%d")
    usuario["historial"].append(f"{fecha}: Enviado a {dni_dest} {cantidad} €")

    destino["pendientes"].append({"from": usuario["dni"], "cantidad": cantidad})

    if cantidad >= 500:
        print("Transferencia grande, ¡bien hecho!")
    elif cantidad >= 100:
        print("Transferencia enviada correctamente.")
    else:
        print("Transferencia pequeña completada.")

def actualizar_fecha_proximo_cobro(cobro):
    f = datetime.strptime(cobro["prox_fecha"], "%Y-%m-%d")
    f += timedelta(days=7)
    cobro["prox_fecha"] = f.strftime("%Y-%m-%d")

def procesar_cobros_automaticos(usuario, data):
    hoy = datetime.now().strftime("%Y-%m-%d")
    for c in usuario["cobradores"][:]:
        if c["prox_fecha"] != hoy:
            continue
        usuario["saldo"] += c["cantidad"]
        usuario["historial"].append(f"{hoy}: Cobro automático de {c['origen']} {c['cantidad']} €")
        c["repeticiones"] -= 1
        if c["repeticiones"] <= 0:
            usuario["cobradores"].remove(c)
        else:
            actualizar_fecha_proximo_cobro(c)

def procesar_cobro_semanal(usuario, data):
    hoy = datetime.now().strftime("%Y-%m-%d")
    creado = datetime.strptime(usuario["creado"], "%Y-%m-%d")
    semanas = (datetime.now() - creado).days // 7
    ultimo = usuario.get("ult_cobro_banco", "")
    if ultimo == str(semanas):
        return
    usuario["saldo"] -= 1
    usuario["historial"].append(f"{hoy}: Cobro semanal del banco 1 €")
    usuario["ult_cobro_banco"] = str(semanas)

def crear_cobro_automatico(usuario, data):
    dni = input("DNI del usuario a cobrar: ")
    destino = None
    for u in data:
        if u["dni"] == dni:
            destino = u
            break
    if destino is None:
        print("No existe ese usuario.")
        return
    cantidad = float(input("Cantidad: "))
    rep = int(input("Repeticiones: "))
    hoy = datetime.now().strftime("%Y-%m-%d")
    destino["cobradores"].append({
        "origen": usuario["dni"],
        "cantidad": cantidad,
        "prox_fecha": hoy,
        "repeticiones": rep
    })
    print("Cobro automático creado.")

def ver_cobradores_activos(usuario):
    print("\n--- Cobradores automáticos activos ---")
    if not usuario["cobradores"]:
        print("No tienes cobradores activos.")
        return
    for c in usuario["cobradores"]:
        print(f"Origen: {c['origen']} | Cantidad: {c['cantidad']} € | Próximo: {c['prox_fecha']} | Restantes: {c['repeticiones']}")

def exportar_informacion(usuario, data):
    fname = f"{usuario['dni']}_reporte.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"Usuario: {usuario['nombre']}\n")
        f.write(f"DNI: {usuario['dni']}\n")
        f.write(f"Saldo: {usuario['saldo']} €\n\n")
        f.write("Movimientos:\n")
        for h in usuario["historial"]:
            f.write(f"- {h}\n")
        f.write("\nCobradores activos:\n")
        if usuario["cobradores"]:
            for c in usuario["cobradores"]:
                f.write(f"- {c['origen']} | {c['cantidad']} € | Próximo: {c['prox_fecha']} | Restantes: {c['repeticiones']}\n")
        else:
            f.write("No tienes cobradores activos.\n")
    print("Archivo exportado.")

def menu_usuario(usuario, data):
    while True:
        print("\n1. Ver saldo")
        print("2. Enviar dinero")
        print("3. Crear cobro automático")
        print("4. Ver cobradores activos")
        print("5. Exportar historial")
        print("6. Salir")

        op = input("> ")
        if op == "1":
            print("Saldo:", usuario["saldo"])
        elif op == "2":
            enviar_dinero(usuario, data)
            guardar_bd(data)
        elif op == "3":
            crear_cobro_automatico(usuario, data)
            guardar_bd(data)
        elif op == "4":
            ver_cobradores_activos(usuario)
        elif op == "5":
            exportar_informacion(usuario, data)
        elif op == "6":
            guardar_bd(data)
            break

def main():
    while True:
        print("\n--- CachabanBank ---")
        print("1. Crear cuenta")
        print("2. Iniciar sesión")
        print("3. Salir")
        op = input("> ")
        if op == "1":
            crear_usuario()
        elif op == "2":
            usuario, data = iniciar_sesion()
            if usuario:
                menu_usuario(usuario, data)
        elif op == "3":
            break

if __name__ == "__main__":
    main()
