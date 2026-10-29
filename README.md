# Proyecto 2 — DataLogger Contaminación Ambiental
## INFO1128 - Unidad II

## Estructura del Proyecto
```
Proyecto2_interfaces_graficas/
├── lazarus_client/          ← Cliente Lazarus Pascal
│   ├── Lazarus_client.lpi   ← Proyecto Lazarus
│   ├── Lazarus_client.lpr   ← Programa principal
│   ├── unit1.pas            ← Lógica completa (serial, gráficas, Flask)
│   ├── unit1.lfm            ← Diseño de la interfaz
│   └── Lazarus_client.exe   ← Ejecutable compilado
│
├── serial_sim/              ← Scripts Python
│   ├── simu_trama.py        ← Simulador serial (COM1 → COM2)
│   └── server_flask.py      ← Servidor Flask con API REST + SQLite
│
├── TLazSerial/              ← Librería TLazSerial (clonada de GitHub)
└── proyecto2.vspe           ← Config Virtual Serial Port Emulator
```

---

## Cómo ejecutar el proyecto

### Paso 1: Virtual Serial Port Emulator (VSPE)
1. Abrir **VSPE** (Virtual Serial Port Emulator)
2. Cargar el archivo `proyecto2.vspe` (o crear un Pair: **COM1 ↔ COM2**)
3. Activar el par de puertos virtuales

### Paso 2: Servidor Flask
Abrir una terminal PowerShell y ejecutar:
```powershell
cd c:\ruta\al\proyecto\serial_sim
python server_flask.py
```
El servidor estará disponible en `http://127.0.0.1:5000`

**Endpoints disponibles:**
| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/` | Página de inicio |
| GET | `/dashboard` | Dashboard visual con gráficas |
| POST | `/datos` | Recibir datos JSON del cliente Lazarus |
| GET | `/datos` | Listar todas las mediciones (JSON) |
| GET | `/datos/uma/<id>` | Filtrar por UMA 1-5 (JSON) |
| GET | `/datos/ultimas/<n>` | Últimas N mediciones (JSON) |
| GET | `/estadisticas` | Estadísticas promedio por UMA (JSON) |
| GET | `/grafica` | Gráfica PNG de todas las mediciones |
| GET | `/grafica/uma/<id>` | Gráfica PNG de una UMA específica |
| GET | `/grafica/histograma` | Histograma de partículas (PNG) |

### Paso 3: Simulador Serial
Abrir otra terminal y ejecutar:
```powershell
cd c:\ruta\al\proyecto\serial_sim
python simu_trama.py COM1 0.1
```
Esto envía tramas de las 5 UMAs por COM1 cada 0.1 segundos.

### Paso 4: Cliente Lazarus
Ejecutar `Lazarus_client.exe` (o compilar en Lazarus IDE):
1. Seleccionar el puerto **COM2** en el campo Puerto COM
2. Elegir la UMA a monitorear (UMA1-UMA5)
3. Activar **"Enviar a Flask"** si se desea almacenar en BD
4. Clic en **Conectar**

---

## Formato de la Trama Serial
```
id,mp01,mp25,mp10,h03,h05,h10,h25,h50,h100,te,hr\n
```
| Campo | Descripción |
|-------|-------------|
| id | ID de la UMA (1-5) |
| mp01 | PM1.0 μg/m³ |
| mp25 | PM2.5 μg/m³ |
| mp10 | PM10 μg/m³ |
| h03-h100 | Histograma 0.3→10 μm |
| te | Temperatura °C |
| hr | Humedad Relativa % |

## Formato JSON enviado a Flask
```json
{
  "id": 1,
  "mp01": 45, "mp25": 67, "mp10": 80,
  "h03": 1200, "h05": 800, "h10": 400,
  "h25": 200, "h50": 100, "h100": 50,
  "te": 22, "hr": 65
}
```

## Base de Datos SQLite
Archivo: `serial_sim/datalogger.db`
Tabla: `mediciones` — incluye todos los campos + `fecha` (DateTime).

## Compilar el proyecto Lazarus (si se requiere)
```powershell
$env:PATH = "C:\lazarus;C:\lazarus\fpc\3.2.2\bin\x86_64-win64;" + $env:PATH
$pcp = "c:\Users\Kuro_Waza\.lazarus"
& "C:\lazarus\lazbuild.exe" --pcp=$pcp "lazarus_client\Lazarus_client.lpi"
```
