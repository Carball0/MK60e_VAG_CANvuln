# MK60e\_VAG\_CANvuln

Este repositorio contiene una investigación sobre vulnerabilidades en la red CAN (Controller Area Network) de vehículos del grupo VAG, centrada en una centralita ABS y ESP ATE/TEVES **MK60e**.

El modelo específico de centralita proviene de un Audi A3 8P, aunque se puede encontrar en otros vehículos del grupo VAG (Volkswagen, Audi, Skoda, Seat, etc.).

## Estructura del Repositorio

* `CAN_MK60e_sniffer.py`: Script Python que realiza función de sniffer, permitiendo capturar y registrar tráfico CAN específico de la plataforma PQ de VW y que origina la ECU MK60e.
* `dbcAnalyzer.py`: Utilidad para analizar archivos `.dbc` y extraer información de un fichero completo o de un CAN ID específico, y que permite interpretar los IDs y sus respectivas señales.
* `attack_scripts/`: Colección de scripts para realizar pruebas de intrusión y ataques de replay o inyección CAN.
  * `CAN_MK60e_DoS_0x0.py`: Script para el lanzamiento de un ataque DoS sobre el bus CAN haciendo uso del CAN ID 0x0.
* `CAN_trz_standalone_MK60e/`: Trazas obtenidas de la línea CAN en la que está presente la ECU MK60e, en modo standalone (no comparte bus con más ECUs)
* `README.md`: Documento README con la información sobre el repositorio.

## Requisitos del Sistema

* Python 3.7 o superior
* Interfaz hardware USB a CAN o similar, compatible con `socketcan` (en este proyecto se utiliza MKS CANable 2.0 Pro, aunque otros modelos son también utilizables)
* Bibliotecas de Python:

  * `python-can`
  * `cantools`
  * `argparse`, `time`, `os`

Instalación de dependencias:

```bash
pip install python-can cantools
```

## Uso Básico

1. **Captura de tráfico CAN:**

No damite argumentos, el script comenzará a leer datos en la interfaz can0. El script se puede personalizar modificando el código.

```bash
python CAN_MK60e_sniffer.py
```

2. **Análisis con archivo DBC:**

El script dbcAnalyzer.py permite el análisis de ficheros DBC, como los presentes en el proyecto [opendbc de commaai](https://github.com/commaai/opendbc).

Admite dos argumentos, como mínimo se debe especificar uno:

```bash
python dbcAnalyzer.py -d {path_to_dbc_file.dbc} {CAN_ID en hex}
```

Por ejemplo, para describir todas las señales de unfichero DBC, se ejecuta:

```bash
python dbcAnalyzer.py pq.dbc
```

Si del fichero DBC se desea consultar un CAN ID, se puede especificar a continuación en formato hexadecimal. El formato de CAN ID no es case-sensitive.

```bash
python dbcAnalyzer.py pq.dbc 0x1a0
```

## Advertencia Legal y Licencia

Este proyecto se ha desarrollado como proyecto de final de Máster, y su uso se reserva únicamente con fines **educativos y de investigación**. Cualquier uso no autorizado de estas herramientas en vehículos reales puede ser ilegal, y el autor no se hace responsable de usos indebidos.

Este proyecto está bajo la licencia [MIT](LICENSE). Puedes usar, modificar y distribuir este código bajo los términos especificados en dicha licencia.

## Recursos Recomendados

* [opendbc](https://github.com/commaai/opendbc): Archivos DBC para muchos modelos de vehículos.
* [python-can documentation](https://python-can.readthedocs.io/): Referencia oficial de la biblioteca CAN en Python.
* [SavvyCAN](https://github.com/collin80/SavvyCAN): Herramienta gráfica para captura y análisis de tráfico CAN.
