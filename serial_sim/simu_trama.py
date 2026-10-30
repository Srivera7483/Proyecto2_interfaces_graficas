import argparse
import random as ra
import sys
import time as ti
import serial as rs


def make_data(uma_id):
    mp01 = ra.randint(5, 100)
    mp25 = ra.randint(5, 100)
    mp10 = ra.randint(5, 100)
    h03 = ra.randint(10, 10000)
    h05 = ra.randint(10, 10000)
    h10 = ra.randint(10, 10000)
    h25 = ra.randint(10, 10000)
    h50 = ra.randint(10, 10000)
    h100 = ra.randint(10, 10000)
    te = ra.randint(5, 35)
    hr = ra.randint(20, 80)

    return f"{uma_id},{mp01},{mp25},{mp10},{h03},{h05},{h10},{h25},{h50},{h100},{te},{hr}\n"


def main():
    parser = argparse.ArgumentParser(description='Simulador de trama UMA serial')
    parser.add_argument('puerto', nargs='?', default='COM1', help='Puerto serial (default: COM1)')
    parser.add_argument('intervalo', nargs='?', default=0.1, type=float, help='Intervalo en segundos (default: 0.1)')
    args = parser.parse_args()

    print(f"[SIMULADOR] Puerto: {args.puerto} | Intervalo: {args.intervalo}s | 9600-8N1")
    print("[SIMULADOR] Presiona Ctrl+C para detener")

    try:
        cnx = rs.Serial(args.puerto, baudrate=9600, timeout=1)
    except Exception as e:
        print(f"[ERROR] No se pudo abrir {args.puerto}: {e}")
        sys.exit(1)

    uma_id = 1
    total = 0

    try:
        while True:
            trama = make_data(uma_id)
            print(f"[{total:06d}] {trama}", end='')
            cnx.write(trama.encode('utf-8'))
            ti.sleep(args.intervalo)
            uma_id = 1 if uma_id >= 5 else uma_id + 1
            total += 1
    except KeyboardInterrupt:
        print(f"\n[SIMULADOR] Detenido. Total enviadas: {total}")
    finally:
        cnx.close()


if __name__ == '__main__':
    main()
