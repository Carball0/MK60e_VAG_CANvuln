import can
import curses
import os
import time
import datetime
import threading
import queue

msg_queue = queue.Queue(maxsize=80000)
stop_event = threading.Event()
bus_channel = "can0"
bus_interface = "socketcan"

buffer_list = {
    "0x1a0": "\n\n-->0x1A0 no ha emitido\n",
    "0x3a0": "\n\n-->0x3A0 no ha emitido\n",
    "0x4a0": "\n\n-->0x4A0 no ha emitido\n",
    "0x4a8": "\n\n-->0x4A8 no ha emitido\n",
    "0x5a0": "\n\n-->0x5A0 no ha emitido\n",
    "0x723": "\n\n-->0x723 no ha emitido\n"
}

buffer_can_listener = {
    "total": 0,
    "total_not_filtered": 0
}

vh_status_dic = {               # Status vehicle driver choice
    0x00: "Parado (Vehicle standing)",
    0x01: "Se mueve hacia adelante",
    0x02: "Se mueve hacia atrás",
    0x03: "Se mueve (dirección desconocida)",
    0x07: "Error (Invalid signal)"
}

module_status_dic = {           # Module status (heartbeat)
    0x00: "Encendido (Boot-up)",
    0x04: "Parado (Stopped)",
    0x05: "Funcionando (Operational)",
    0x7F: "Preparando (Pre-operational)"
}

brake_pressure_dic = {          # Brake pressure (excluding ACC)
    0x80: "No hay frenada activa (No active braking from ABS module)"
}

# Selecciona del array de datos el dato entre dos posiciones en bits
# endianness: "big" o "little"
def get_from_bit_to_bit(data, bit_i, size, endianness, is_signed, factor, offset):
    data_int = int.from_bytes(data, byteorder=endianness)           # Convierte a entero
    data_int_shifted = (data_int >> bit_i) & ((1 << size) - 1)      # Desplaza drcha hasta bit_i con longitud size
    if is_signed and (data_int_shifted & (1 << (size - 1))):
        data_int_shifted -= (1 << size)
        
    return data_int_shifted * factor + offset

def add_to_buffer(arb_id, buffer):
    if arb_id in buffer_list:
        buffer_list[arb_id] = buffer
    else:
        raise Exception(f"arb_id {arb_id} no existente, no se puede almacenar en buffer")

def print_buffers(qsize):
    # Descomentar si se desea imprimir la lista completa de IDs con el total de paquetes
    # can_listener_print(qsize)
    
    for key, value in buffer_list.items():
         print(f"{value}")
    print("-"*60)

# Plataforma PQ: Bremse_1
def id_0x1A0(msg):
    data = msg.data

    # Plataforma PQ: Fahrer_bremst__Bremse_1___4_1_
    brake_pedal = get_from_bit_to_bit(data, 11, 1, 'little', False, 1, 0)
    
    # Sistemas activos o exigencia de ellos - Plataforma PQ
    exi_ASR = get_from_bit_to_bit(data, 0, 1, 'little', False, 1, 0)    # ASR_Anforderung
    exi_MSR = get_from_bit_to_bit(data, 1, 1, 'little', False, 1, 0)    # MSR_Anforderung
    exi_ABS = get_from_bit_to_bit(data, 2, 1, 'little', False, 1, 0)    # ABS_Bremsung__4_1_
    exi_ESP = get_from_bit_to_bit(data, 4, 1, 'little', False, 1, 0)    # ESP_Eingriff

    # Plataforma PQ: Geschwindigkeit_neu__Bremse_1_, en km/h
    speed = get_from_bit_to_bit(data, 17, 15, 'little', False, 0.01, 0)

    # Status vehicle driver choice // Pruebas de módulo BMW, no fiable
    # https://www.ms4x.net/index.php?title=CAN_Bus_ID_0x1A0
    vhstatus = get_from_bit_to_bit(data, 15, 1, 'little', False, 1, 0) # Bit 7 del Byte 1

    vhstatus_str = vh_status_dic.get(vhstatus, f"Unknowm data: 0x{vhstatus:02X}")
    
    buffer = f"\n----ARBID 0x1a0---- {can_listener_print_by_id('0x1a0')}"
    buffer += f"Active Systems: ABS: {exi_ABS}, ASR: {exi_ASR}, MSR: {exi_MSR}, ESP {exi_ESP}\n"
    buffer += f"Brake Pedal: {'Braking...' if brake_pedal else 'Not pressed' }\n"
    buffer += f"ABS Braking: {'ABS Braking...' if exi_ABS else 'No ABS Braking' }\n"
    buffer += f"Speed (from all WSS): {speed:.2f} (km/h)\n"
    buffer += f"Vehicle Status: {vhstatus_str}\n"
    
    add_to_buffer("0x1a0", buffer)
    
# Plataforma PQ: Bremse_10
def id_0x3A0(msg):
    data = msg.data

    # Plataforma PQ: B10_QB_Wegimp_HR, 0 conectado 1 desconectado
    alive_wrr = f'Alive' if get_from_bit_to_bit(data, 15, 1, 'little', False, 1, 0) == 0 else 'Disconnected'
    # Plataforma PQ: B10_QB_Fahrtr_HR, 0 back 1 forward (dirección rueda)
    dir_wrr = f'Forward' if get_from_bit_to_bit(data, 59, 1, 'little', False, 1, 0) == 1 else 'Backwards'
    # Plataforma PQ: B10_Wegimp_HR, contador trasera derecha
    counter_wrr = get_from_bit_to_bit(data, 46, 10, 'little', False, 1, 0)
    
    # Plataforma PQ: B10_QB_Wegimp_HL, 0 conectado 1 desconectado
    alive_wrl = f'Alive' if get_from_bit_to_bit(data, 14, 1, 'little', False, 1, 0) == 0 else 'Disconnected'
    # Plataforma PQ: B10_QB_Fahrtr_HL, 0 back 1 forward (dirección rueda)
    dir_wrl = f'Forward' if get_from_bit_to_bit(data, 58, 1, 'little', False, 1, 0) == 1 else 'Backwards'
    # Plataforma PQ: B10_Wegimp_HL, contador trasera izqda
    counter_wrl = get_from_bit_to_bit(data, 36, 10, 'little', False, 1, 0)
    
    # Plataforma PQ: B10_Wegimp_VR, 0 conectado 1 desconectado
    alive_wfr = f'Alive' if get_from_bit_to_bit(data, 13, 1, 'little', False, 1, 0) == 0 else 'Disconnected'
    # Plataforma PQ: B10_QB_Fahrtr_VR, 0 back 1 forward (dirección rueda)
    dir_wfr = f'Forward' if get_from_bit_to_bit(data, 57, 1, 'little', False, 1, 0) == 1 else 'Backwards'
    # Plataforma PQ: B10_QB_Wegimp_VR, contador delantera derecha
    counter_wfr = get_from_bit_to_bit(data, 26, 10, 'little', False, 1, 0)
    
    # Plataforma PQ: B10_QB_Wegimp_VL, 0 conectado 1 desconectado
    alive_wfl = f'Alive' if get_from_bit_to_bit(data, 12, 1, 'little', False, 1, 0) == 0 else 'Disconnected'
    # Plataforma PQ: B10_QB_Fahrtr_VL, 0 back 1 forward (dirección rueda)
    dir_wfl = f'Forward' if get_from_bit_to_bit(data, 56, 1, 'little', False, 1, 0) == 1 else 'Backwards'
    # Plataforma PQ: B10_Wegimp_VL, contador delantera izqda
    counter_wfl = get_from_bit_to_bit(data, 16, 10, 'little', False, 1, 0)
    
    buffer = f"\n----ARBID 0x3a0---- {can_listener_print_by_id('0x3a0')}"
    buffer += f"FR Wheel: Count - {counter_wfr} ({dir_wfr}, {alive_wfr})\n"
    buffer += f"FL Wheel: Count - {counter_wfl} ({dir_wfl}, {alive_wfl})\n"
    buffer += f"RR Wheel: Count - {counter_wrr} ({dir_wrr}, {alive_wrr})\n"
    buffer += f"RL Wheel: Count - {counter_wrl} ({dir_wrl}, {alive_wrl})\n"
    
    add_to_buffer("0x3a0", buffer)

# Plataforma PQ: Bremse_3 (datos completos)
# 8 bytes de datos - Cada 2 bytes (menos el primer bit) corresponde a una rueda
def id_0x4A0(msg):        # Velocidad de cada sensor de velocidad de rueda
    data = msg.data
    
    # Plataforma PQ: Radgeschw__HR_4_1, en km/h
    # Velocidad de la rueda trasera derecha
    speed_wrr = get_from_bit_to_bit(data, 49, 15, 'little', False, 0.01, 0)
    speed_wrr = f'{speed_wrr:.2f}' if speed_wrr < 326 else 'Disconnected'
    # Plataforma PQ: BR3_Fahrtr_HR, 0 back 1 forward (dirección rueda)
    speed_wrr_first = get_from_bit_to_bit(data, 48, 1, 'little', False, 1, 0)
    
    # Plataforma PQ: Radgeschw__HL_4_1, en km/h
    # Velocidad de la rueda trasera izquierda
    speed_wrl = get_from_bit_to_bit(data, 33, 15, 'little', False, 0.01, 0)
    speed_wrl = f'{speed_wrl:.2f}' if speed_wrl < 326 else 'Disconnected'
    # Plataforma PQ: BR3_Fahrtr_HL, 0 back 1 forward (dirección rueda)
    speed_wrl_first = get_from_bit_to_bit(data, 32, 1, 'little', False, 1, 0)
    
    # Plataforma PQ: Radgeschw__VR_4_1, en km/h
    # Velocidad de la rueda delantera derecha
    speed_wfr = get_from_bit_to_bit(data, 17, 15, 'little', False, 0.01, 0)
    speed_wfr = f'{speed_wfr:.2f}' if speed_wfr < 326 else 'Disconnected'
    # Plataforma PQ: BR3_Fahrtr_VR, 0 back 1 forward (dirección rueda)
    speed_wfr_first = get_from_bit_to_bit(data, 16, 1, 'little', False, 1, 0)
    
    # Plataforma PQ: Radgeschw__VL_4_1, en km/h
    # Velocidad de la rueda delantera izquierda
    speed_wfl = get_from_bit_to_bit(data, 1, 15, 'little', False, 0.01, 0)
    speed_wfl = f'{speed_wfl:.2f}' if speed_wfl < 326 else 'Disconnected'
    # Plataforma PQ: BR3_Fahrtr_VL, 0 back 1 forward (dirección rueda)
    speed_wfl_first = get_from_bit_to_bit(data, 0, 1, 'little', False, 1, 0)
    
    buffer = f"\n----ARBID 0x4a0---- {can_listener_print_by_id('0x4a0')}"
    buffer += f"Speed FR Wheel: {speed_wfr} km/h ({speed_wfr_first})\n"
    buffer += f"Speed FL Wheel: {speed_wfl} km/h ({speed_wfl_first})\n"
    buffer += f"Speed RR Wheel: {speed_wrr} km/h ({speed_wrr_first})\n"
    buffer += f"Speed RL Wheel: {speed_wrl} km/h ({speed_wrl_first})\n"

    add_to_buffer("0x4a0", buffer)

# Plataforma PQ: Bremse_5
def id_0x4A8(msg):
    data = msg.data

    # Presión de frenado (b3 << 8 + b2)
    # https://github.com/v-ivanyshyn/parse_can_logs/blob/master/VW%20CAN%20IDs%20Summary.md
    brake = ((data[3] << 8) + data[2])
    brake_act = (data[3])
    
    # Plataforma PQ: Bremsdruck, bar
    # Presión de freno en la línea
    brake_press = get_from_bit_to_bit(data, 16, 12, 'little', False, 0.1, 0)
    
    # Plataforma PQ: Giergeschwindigkeit, grad/s
    # Sensor YAW de movimiento lateral del vehículo, interior del MK60e
    yaw_rate = get_from_bit_to_bit(data, 0, 14, 'little', False, 0.01, 0)
    
    brake_str = brake_pressure_dic.get(brake, f"{brake}")
    brake_act_str = brake_pressure_dic.get(brake_act, f"{brake_act}")
    
    buffer = f"\n----ARBID 0x4a8---- {can_listener_print_by_id('0x4a8')}"
    buffer += f"Brake Pressure: {brake_press:.2f} bar  //  {brake_str} (raw)\n"
    buffer += f"Yaw Rate Sensor: {yaw_rate:.2f} grad/s\n"
    buffer += f"Brake Actuation by ABS: {brake_act_str}\n"
    
    add_to_buffer("0x4a8", buffer)

# Plataforma PQ: Bremse_2
def id_0x5A0(data):
    data = data.data;
    if len(data) != 8:
        raise ValueError("El mensaje debe tener exactamente 8 bytes")
        
    # Plataforma PQ: Warnlampe_DDS, ON u OFF
    # Lámpara de advertencia de sistema DDS (electroválvula de corte de combustible)
    ddl_light = get_from_bit_to_bit(data, 53, 1, 'little', False, 1, 0)

    # Plataforma PQ: gemessene_Querbeschleunigung
    # Indicador de aceleración transversal
    transversal = get_from_bit_to_bit(data, 0, 8, 'little', False, 0.01, -1.27)

    # Plataforma PQ: BR2_mi_Radgeschw (not found on DBC)
    # Revoluciones medias por rueda
    rev_median = get_from_bit_to_bit(data, 9, 14, 'little', False, 1, 0)

    # Extraer contador de distancia (BB) - bytes 5 y 6 (LSB primero)
    BB = data[5] + (data[6] << 8)
    distancia = BB / 50  # metros

    # Extraer bitfield CC - byte 3
    CC = data[3]
    presion_adv = (CC & (1 << 3)) != 0  # bit 3
    
    buffer = f"\n----ARBID 0x5a0---- {can_listener_print_by_id('0x5a0')}"
    buffer += f"DDL Light (Gas cut): {'ON' if ddl_light else 'OFF' }\n"
    buffer += f"Transversal Acceleration: {transversal:.2f} g\n"
    buffer += f"Distancia: {distancia} (m)\n"
    buffer += f"Median speed/wheel: {rev_median} rpm\n"
    buffer += f"Presion: {presion_adv}\n"
    
    add_to_buffer("0x5a0", buffer)
    
def id_0x723(msg):        # Heartbeat centralita
    data = msg.data
    
    # Byte 0 completo -> Byte de heartbeat
    # https://www.nikhef.nl/pub/departments/ct/po/doc/CANopen30.pdf
    module_status = data[0]
    module_status_str = module_status_dic.get(module_status, f"Unknowm data: 0x{module_status:02X}")
    
    buffer = f"\n----ARBID 0x723---- {can_listener_print_by_id('0x723')}"
    buffer += f"Module Heartbeat: {module_status_str}\n"
    
    add_to_buffer("0x723", buffer)

# CAN Listener: almacena la cuenta total de paquetes recibidos en el bus
# Guarda la cuenta total la específica por paquete, almacenando también los datos del último paquete
# abs_only: solo registra la lista de IDs indexada del módulo MK60e
def can_listener_MK60e(msg, abs_only):
    data = msg.data
    id_str = str(hex(msg.arbitration_id)).lower()
    buffer_can_listener["total_not_filtered"] += 1
    if abs_only and id_str not in buffer_list.keys():
        return
    else:
        buffer_can_listener["total"] += 1
        
        if str(hex(msg.arbitration_id)) in buffer_can_listener:
            buffer_can_listener[id_str][0] +=  1
        else:
            buffer_can_listener.setdefault(id_str, [0, "", "", ""])
            buffer_can_listener[id_str][0] = 1
        
        buffer_can_listener[id_str][1] = bytearray_to_str_padded(msg.data)
        buffer_can_listener[id_str][2] = datetime.datetime.fromtimestamp(msg.timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")
    
# Imprime datos almacenados por can_listener(...)
def can_listener_print(qsize):
    buffer = ""
    total = 0
    for key, value in buffer_can_listener.items():
        if key == "total":
            buffer += f"Paquetes recibidos (procesados+cola): {value + qsize} (Cola: {qsize}, Procesados: {value})\n"
            total = value
        if key == "total_not_filtered":
            if value > total:
                buffer += f"Paquetes totales recibidos (sin contar filtro 'ABS only' ni cola): {value}\n"
        elif key != "buffer" and key != "total" and key != "total_not_filtered":
            buffer += f"ID {key}{' '*5}Data: {value[1]}{' '*5}Count: {value[0]}{' '*5}Time: {value[2]}\n"
    
    buffer += f"\n{'-'*32}"
    print(f"\n{'-'*10}CAN Listener{'-'*10}\n" + buffer + f"\n{'-'*32}")
    
# Imprime datos almacenados por can_listener(...) para un ID específico
def can_listener_print_by_id(id_str):
    for key, value in buffer_can_listener.items():
        if key == id_str:
            return f"Data: {value[1]}{' '*4}Count: {value[0]}{' '*4}Time: {value[2]}\n"
    return f"Last CAN message not recorded for ID {id_str}"

# Da formato al array de datos de un paquete CAN, y se paddea si no llega a 8 bytes
def bytearray_to_str_padded(data):
    hex_bytes = [f"{b:02X}" for b in data]
    padding_count = 8 - len(hex_bytes) 
    padding = ["  "] * padding_count
    result = " ".join(hex_bytes + padding)
    return result

# Lectura de mensajes del bus CAN
def reader_thread():
    bus = can.interface.Bus(channel=bus_channel, interface=bus_interface)
    listener = can.BufferedReader()
    notifier = can.Notifier(bus, [listener])
    while True and not stop_event.is_set():
        msg = listener.get_message(timeout=0.05)
        if msg:
            try:
                msg_queue.put_nowait(msg)
            except queue.Full:
                print("FULL QUEUE! - Cannot handle bus speed")
                pass
    time.sleep(0.5)
    print("\nClosing reader_thread...")
    bus.shutdown()

def main_thread():
    while True and not stop_event.is_set():
        msg = msg_queue.get()
        can_listener_MK60e(msg, True)
        if msg.arbitration_id == 0x1A0:
            id_0x1A0(msg)
        elif msg.arbitration_id == 0x3A0:
            id_0x3A0(msg)
        elif msg.arbitration_id == 0x4A0:
            id_0x4A0(msg)
        elif msg.arbitration_id == 0x4A8:
            id_0x4A8(msg)
        elif msg.arbitration_id == 0x5A0:
            id_0x5A0(msg)
        elif msg.arbitration_id == 0x723:
            id_0x723(msg)
        print_buffers(msg_queue.qsize())
        msg_queue.task_done()
    time.sleep(0.5)
    print("Closing main_thread...")
        
thread_1 = threading.Thread(target=main_thread)
thread_2 = threading.Thread(target=reader_thread)
thread_1.start()
thread_2.start()

while True:
    try:
        time.sleep(2)
    except KeyboardInterrupt:
        stop_event.set()
        print("\nClosing main process...")
        time.sleep(0.1)
        thread_1.join()
        thread_2.join()     # Bus shutwdown, must be the last to kill
        break
