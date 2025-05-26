import cantools
import sys
import time

def analizar_dbc(file, can_id):
    try:
        db = cantools.database.load_file(file, strict=False)
        if can_id:
            messages = [m for m in db.messages if str(hex(m.frame_id)).lower() == str(can_id).lower()]
            dbc_print(messages)
        else:
            dbc_print(db.messages)
    except Exception as e:
        print(f"DBC file - error while opening: {e}")
        fixed = "out_no_extended.dbc"
        if file == fixed:   # El fichero ya fue rectificado
            print("The rectified DBC file was already rectified, but still contains errors\nExiting...")
            return
        
        if "11 bits" in f"{e}":
            print("The DBC will be rectified to avoid extended IDs...\n")
            time.sleep(3)
            try:
                dbc_fix_extended(file, fixed)
            except Exception as r:
                print(f"Error while correcting file: {r}")
                return
            analizar_dbc(fixed, can_id)
                
# Elimina IDs extendidos si están mal definidos en el fichero DBC
# Se desencadena ejecución si dichos IDs causan una excepción al abrir el fichero
# file: fichero DBC origen
# newfile: fichero DBC que se escribe con los IDs extendidos eliminados
def dbc_fix_extended(file, newfile):
        with open(file, 'r') as f:
            lines = f.readlines()
        output = []
        skip = False
        for line in lines:
            if line.startswith('BO_'):
                frame_id = int(line.split()[1])
                skip = frame_id > 0x7FF
            if not skip:
                output.append(line)
        with open(newfile, 'w') as f:
            f.writelines(output)

# Interpreta los mensajes del fichero DBC y sus respectivas señales
# Recibe un array de un solo mensaje si se especificó un ID como parámetro de entrada
def dbc_print(messages):
    offset = " "*10
    if messages is None or not messages:
        print("CAN_ID not found on this DBC file")
        return
    for msg in messages:
        print("="*32 + f"ID: {hex(msg.frame_id)} ({msg.frame_id})" + "="*32)
        print(f"Nombre: {msg.name}, Longitud: {msg.length}, FD: {msg.is_extended_frame}")
        print("="*35 + "Señales" + "="*35)

        if not msg.signals:
            print("  --->No signal defined in this CAN_ID <---")
            continue

        for sig in msg.signals:
            print(f"  ----- {sig.name} -----")
            print(f"{offset}Bit inicio: {sig.start}, Longitud: {sig.length} bits")
            print(f"{offset}Endianness: {'Big' if sig.byte_order == 'big_endian' else 'Little'}")
            print(f"{offset}Signed: {sig.is_signed}, Factor: {sig.scale}, Offset: {sig.offset}")
            print(f"{offset}Unidad: {sig.unit or 'N/A'}")
            print(f"{offset}Rango físico: [{sig.minimum}, {sig.maximum}]")
            if sig.choices:
                print("    Valores posibles:")
                for valor, significado in sig.choices.items():
                    print(f"{offset*2}{valor}: {significado}")
        print()


if __name__ == "__main__":
    import sys
    #
    if len(sys.argv) == 2:
        analizar_dbc(sys.argv[1], None)
    elif len(sys.argv) > 2:
        analizar_dbc(sys.argv[1], sys.argv[2])
    else:
        print("Missing arguments. Usage:\n python dbcAnalyzer.py file.dbc\n python dbcAnalyzer.py file.dbc 0x1A0")
