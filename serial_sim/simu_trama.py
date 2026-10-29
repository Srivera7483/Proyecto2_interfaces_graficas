"""
Simulador de Trama - Sensor PMS7003ST
======================================
Simula los datos de 5 UMAs (Unidades Medio Ambientales)
enviando tramas CSV por puerto serial COM1.

Formato de trama:
  id,mp01,mp25,mp10,h03,h05,h01,h25,h50,h10,te,hr

Donde:
  id   = ID de la UMA (1-5)
  mp01 = Material Particulado PM1.0 (ug/m3)
  mp25 = Material Particulado PM2.5 (ug/m3)
  mp10 = Material Particulado PM10  (ug/m3)
  h03  = Histograma 0.3 um
  h05  = Histograma 0.5 um
  h01  = Histograma 1.0 um
  h25  = Histograma 2.5 um
  h50  = Histograma 5.0 um
  h10  = Histograma 10 um
  te   = Temperatura (Celsius)
  hr   = Humedad Relativa (%)

Uso:
  python simu_trama.py [puerto] [intervalo_seg]
  Ej: python simu_trama.py COM1 0.1
"""

import serial as rs
import time as ti
import random as RA
import sys
import argparse

def Make_Data(nId):
    """Genera datos aleatorios simulando un sensor PMS7003ST."""
    nEMA  = nId                          # Identificador de la UMA
    nMP01 = RA.randint(5,  100)          # Material Particulado 1.0 um
    nMP25 = RA.randint(5,  100)          # Material Particulado 2.5 um
    nMP10 = RA.randint(5,  100)          # Material Particulado 10 um
    nH103 = RA.randint(10, 10000)        # Histograma MP 0.3 um
    nH105 = RA.randint(10, 10000)        # Histograma MP 0.5 um
    nH101 = RA.randint(10, 10000)        # Histograma MP 1.0 um
    nH125 = RA.randint(10, 10000)        # Histograma MP 2.5 um
    nH150 = RA.randint(10, 10000)        # Histograma MP 5.0 um
    nH110 = RA.randint(10, 10000)        # Histograma MP 10 um
    nTE   = RA.randint(5,  35)           # Temperatura Celsius
    nHR   = RA.randint(20, 80)           # Humedad Relativa Aire

    sLine = (f"{nEMA},{nMP01},{nMP25},{nMP10},"
             f"{nH103},{nH105},{nH101},"
             f"{nH125},{nH150},{nH110},"
             f"{nTE},{nHR}\n")
    return sLine

def main():
    parser = argparse.ArgumentParser(description='Simulador de trama UMA serial')
    parser.add_argument('puerto',    nargs='?', default='COM1',
                        help='Puerto serial (default: COM1)')
    parser.add_argument('intervalo', nargs='?', default=0.1, type=float,
                        help='Intervalo en segundos entre tramas (default: 0.1)')
    args = parser.parse_args()

    print(f"[SIM] Puerto: {args.puerto} | Intervalo: {args.intervalo}s")
    print(f"[SIM] Enviando tramas de 5 UMAs a 9600-8N1")
    print(f"[SIM] Presiona Ctrl+C para detener")
    print("-" * 50)

    try:
        MyCnx = rs.Serial(args.puerto, baudrate=9600, timeout=1)
    except Exception as e:
        print(f"[ERROR] No se pudo abrir {args.puerto}: {e}")
        print(f"  Asegúrese de tener Virtual Serial Port Emulator activo.")
        sys.exit(1)

    nId = 1
    trama_count = 0

    try:
        while True:
            sAux = Make_Data(nId)
            print(f"[{trama_count:06d}] {sAux}", end='')
            MyCnx.write(sAux.encode())
            ti.sleep(args.intervalo)
            nId += 1
            if nId > 5:
                nId = 1
            trama_count += 1
    except KeyboardInterrupt:
        print(f"\n[SIM] Detenido. Total tramas enviadas: {trama_count}")
    finally:
        MyCnx.close()

if __name__ == '__main__':
    main()