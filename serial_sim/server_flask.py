"""
Server Flask - DataLogger Contaminación Ambiental
=================================================
Recibe datos JSON por POST desde el cliente Lazarus.
Almacena en SQLite con DateTime.
API REST para consultas.
Visualización de gráfica Matplotlib en el navegador.
"""

from flask import Flask, request, jsonify, send_file
from datetime import datetime
import sqlite3
import json
import io
import os
import base64

# Matplotlib en modo no interactivo
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'datalogger.db')

# ─── Inicializar Base de Datos ──────────────────────────────────────────────

def init_db():
    """Crea la tabla si no existe."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS mediciones (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            uma_id   INTEGER NOT NULL,
            mp01     INTEGER,
            mp25     INTEGER,
            mp10     INTEGER,
            h03      INTEGER,
            h05      INTEGER,
            h10      INTEGER,
            h25      INTEGER,
            h50      INTEGER,
            h100     INTEGER,
            te       INTEGER,
            hr       INTEGER,
            fecha    TEXT NOT NULL
        )
    ''')
    con.commit()
    con.close()
    print(f"[DB] Base de datos lista en: {DB_PATH}")

# ─── Helper DB ──────────────────────────────────────────────────────────────

def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

# ─── RUTAS ──────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET'])
def index():
    """Página principal: muestra resumen del servidor."""
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>DataLogger UMA - API</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #eee; margin: 0; padding: 20px; }
            h1 { color: #00d4ff; text-shadow: 0 0 10px #00d4ff55; }
            h2 { color: #88aaff; }
            a { color: #00ffcc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            .card { background: #111827; border: 1px solid #1e3a5f; border-radius: 8px;
                    padding: 16px; margin: 12px 0; max-width: 700px; }
            code { background: #1a2a3a; padding: 2px 6px; border-radius: 4px; color: #00d4ff; }
            .badge { display: inline-block; background: #00d4ff; color: #000;
                     border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 0.8em; }
        </style>
    </head>
    <body>
        <h1>🌿 DataLogger - Monitor de Contaminación Ambiental</h1>
        <p>Servidor Flask activo | Base de datos: SQLite</p>
        <div class="card">
            <h2>Endpoints disponibles</h2>
            <ul>
                <li><span class="badge">POST</span> <code>/datos</code> — Recibir datos JSON del cliente Lazarus</li>
                <li><span class="badge">GET</span>  <code>/datos</code> — Listar todas las mediciones (JSON)</li>
                <li><span class="badge">GET</span>  <code>/datos/uma/&lt;id&gt;</code> — Filtrar por UMA (JSON)</li>
                <li><span class="badge">GET</span>  <code>/datos/ultimas/&lt;n&gt;</code> — Últimas N mediciones (JSON)</li>
                <li><span class="badge">GET</span>  <code>/grafica</code> — Gráfica PM (PNG)</li>
                <li><span class="badge">GET</span>  <code>/grafica/uma/&lt;id&gt;</code> — Gráfica PM de una UMA (PNG)</li>
                <li><span class="badge">GET</span>  <code>/dashboard</code> — Dashboard visual con gráficas</li>
                <li><span class="badge">GET</span>  <code>/estadisticas</code> — Estadísticas por UMA (JSON)</li>
            </ul>
        </div>
        <div class="card">
            <h2>Ejemplo JSON POST</h2>
            <pre style="color:#aaffcc">{"id":1,"mp01":30,"mp25":55,"mp10":80,
 "h03":1200,"h05":800,"h10":400,
 "h25":200,"h50":100,"h100":50,
 "te":22,"hr":65}</pre>
        </div>
        <p><a href="/dashboard">→ Ver Dashboard</a> | <a href="/datos">→ Ver datos JSON</a></p>
    </body>
    </html>
    """
    return html


@app.route('/datos', methods=['POST'])
def recibir_datos():
    """Recibe datos JSON del cliente Lazarus y los almacena en SQLite."""
    try:
        data = request.get_json(force=True)
        if data is None:
            return jsonify({'error': 'JSON inválido'}), 400

        uma_id = int(data.get('id',   0))
        mp01   = int(data.get('mp01', 0))
        mp25   = int(data.get('mp25', 0))
        mp10   = int(data.get('mp10', 0))
        h03    = int(data.get('h03',  0))
        h05    = int(data.get('h05',  0))
        h10    = int(data.get('h10',  0))
        h25    = int(data.get('h25',  0))
        h50    = int(data.get('h50',  0))
        h100   = int(data.get('h100', 0))
        te     = int(data.get('te',   0))
        hr     = int(data.get('hr',   0))
        fecha  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        con = get_db()
        con.execute('''
            INSERT INTO mediciones
              (uma_id,mp01,mp25,mp10,h03,h05,h10,h25,h50,h100,te,hr,fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uma_id, mp01, mp25, mp10, h03, h05, h10, h25, h50, h100, te, hr, fecha))
        con.commit()
        con.close()

        print(f"[{fecha}] UMA{uma_id} PM1={mp01} PM2.5={mp25} PM10={mp10} T={te}°C HR={hr}%")
        return jsonify({'status': 'ok', 'fecha': fecha}), 201

    except Exception as e:
        print(f"[ERROR POST] {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/datos', methods=['GET'])
def listar_datos():
    """Devuelve todas las mediciones en JSON."""
    try:
        limit = request.args.get('limit', 100, type=int)
        con = get_db()
        rows = con.execute(
            'SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/datos/uma/<int:uma_id>', methods=['GET'])
def datos_por_uma(uma_id):
    """Devuelve las mediciones de una UMA específica."""
    try:
        limit = request.args.get('limit', 100, type=int)
        con = get_db()
        rows = con.execute(
            'SELECT * FROM mediciones WHERE uma_id=? ORDER BY id DESC LIMIT ?',
            (uma_id, limit)
        ).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/datos/ultimas/<int:n>', methods=['GET'])
def ultimas_n(n):
    """Devuelve las últimas N mediciones."""
    try:
        con = get_db()
        rows = con.execute(
            'SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (n,)
        ).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/estadisticas', methods=['GET'])
def estadisticas():
    """Devuelve estadísticas por UMA."""
    try:
        con = get_db()
        rows = con.execute('''
            SELECT
                uma_id,
                COUNT(*) as total,
                ROUND(AVG(mp01),1) as avg_mp01,
                ROUND(AVG(mp25),1) as avg_mp25,
                ROUND(AVG(mp10),1) as avg_mp10,
                ROUND(AVG(te),1)   as avg_te,
                ROUND(AVG(hr),1)   as avg_hr,
                MAX(fecha) as ultima_fecha
            FROM mediciones
            GROUP BY uma_id
            ORDER BY uma_id
        ''').fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _generar_grafica_pm(rows, titulo='Series de Tiempo - Material Particulado'):
    """Genera una gráfica de línea para PM1.0, PM2.5 y PM10."""
    if not rows:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=18, color='gray')
        ax.set_facecolor('#0a0a1a')
        fig.patch.set_facecolor('#0a0a1a')
    else:
        fechas = [datetime.strptime(r['fecha'], '%Y-%m-%d %H:%M:%S') for r in rows]
        mp01  = [r['mp01'] for r in rows]
        mp25  = [r['mp25'] for r in rows]
        mp10  = [r['mp10'] for r in rows]
        te    = [r['te']   for r in rows]
        hr    = [r['hr']   for r in rows]

        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        fig.patch.set_facecolor('#0d1117')

        # PM series
        ax1 = axes[0]
        ax1.plot(fechas, mp01, color='#ff4444', linewidth=2, label='PM1.0 μg/m³', marker='o', markersize=3)
        ax1.plot(fechas, mp25, color='#44ff88', linewidth=2, label='PM2.5 μg/m³', marker='s', markersize=3)
        ax1.plot(fechas, mp10, color='#4488ff', linewidth=2, label='PM10 μg/m³',  marker='^', markersize=3)
        ax1.set_facecolor('#0d1117')
        ax1.set_ylabel('Concentración (μg/m³)', color='white')
        ax1.set_title(titulo, color='white', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper right', facecolor='#1a1a2e', labelcolor='white')
        ax1.tick_params(colors='white')
        ax1.spines[:].set_color('#333')
        ax1.grid(True, alpha=0.2, color='#444')

        # Temperatura
        ax2 = axes[1]
        ax2.plot(fechas, te, color='#ffaa44', linewidth=2, label='Temperatura (°C)', marker='o', markersize=3)
        ax2.set_facecolor('#0d1117')
        ax2.set_ylabel('Temperatura (°C)', color='white')
        ax2.legend(loc='upper right', facecolor='#1a1a2e', labelcolor='white')
        ax2.tick_params(colors='white')
        ax2.spines[:].set_color('#333')
        ax2.grid(True, alpha=0.2, color='#444')

        # Humedad
        ax3 = axes[2]
        ax3.plot(fechas, hr, color='#44aaff', linewidth=2, label='Humedad Relativa (%)', marker='o', markersize=3)
        ax3.set_facecolor('#0d1117')
        ax3.set_ylabel('Humedad (%)', color='white')
        ax3.set_xlabel('Fecha/Hora', color='white')
        ax3.legend(loc='upper right', facecolor='#1a1a2e', labelcolor='white')
        ax3.tick_params(colors='white')
        ax3.spines[:].set_color('#333')
        ax3.grid(True, alpha=0.2, color='#444')
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig.autofmt_xdate(rotation=30)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor())
    plt.close()
    buf.seek(0)
    return buf


@app.route('/grafica', methods=['GET'])
def grafica_general():
    """Genera y devuelve una imagen PNG con las series de tiempo de todas las mediciones."""
    try:
        limit = request.args.get('limit', 50, type=int)
        con = get_db()
        rows = con.execute(
            'SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (limit,)
        ).fetchall()
        con.close()
        rows = list(reversed(rows))
        buf = _generar_grafica_pm(rows, 'Todos los sensores UMA - Últimas mediciones')
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/grafica/uma/<int:uma_id>', methods=['GET'])
def grafica_uma(uma_id):
    """Genera gráfica PNG para una UMA específica."""
    try:
        limit = request.args.get('limit', 50, type=int)
        con = get_db()
        rows = con.execute(
            'SELECT * FROM mediciones WHERE uma_id=? ORDER BY id DESC LIMIT ?',
            (uma_id, limit)
        ).fetchall()
        con.close()
        rows = list(reversed(rows))
        buf = _generar_grafica_pm(rows, f'UMA{uma_id} - Material Particulado')
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/grafica/histograma', methods=['GET'])
def grafica_histograma():
    """Gráfica de barras del histograma de partículas (promedio global)."""
    try:
        uma_id = request.args.get('uma', None, type=int)
        con = get_db()
        if uma_id:
            row = con.execute('''
                SELECT AVG(h03) h03,AVG(h05) h05,AVG(h10) h10,
                       AVG(h25) h25,AVG(h50) h50,AVG(h100) h100
                FROM mediciones WHERE uma_id=?
            ''', (uma_id,)).fetchone()
        else:
            row = con.execute('''
                SELECT AVG(h03) h03,AVG(h05) h05,AVG(h10) h10,
                       AVG(h25) h25,AVG(h50) h50,AVG(h100) h100
                FROM mediciones
            ''').fetchone()
        con.close()

        labels = ['0.3 μm', '0.5 μm', '1.0 μm', '2.5 μm', '5.0 μm', '10 μm']
        valores = [row['h03'] or 0, row['h05'] or 0, row['h10'] or 0,
                   row['h25'] or 0, row['h50'] or 0, row['h100'] or 0]
        colores = ['#ff4444', '#ff8844', '#4488ff', '#44ff88', '#ffff44', '#aa44ff']

        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#0d1117')
        bars = ax.bar(labels, valores, color=colores, edgecolor='#333', linewidth=0.5)
        ax.set_title('Histograma de Partículas (Promedio)', color='white', fontsize=14, fontweight='bold')
        ax.set_xlabel('Diámetro de Partícula', color='white')
        ax.set_ylabel('Conteo', color='white')
        ax.tick_params(colors='white')
        ax.spines[:].set_color('#333')
        ax.grid(True, axis='y', alpha=0.2, color='#444')
        for bar, val in zip(bars, valores):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    f'{val:.0f}', ha='center', va='bottom', color='white', fontsize=9)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=fig.get_facecolor())
        plt.close()
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Dashboard HTML con gráficas embebidas."""
    uma_id = request.args.get('uma', 1, type=int)
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="10">
        <title>Dashboard DataLogger UMA{uma_id}</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #eee; }}
            header {{ background: linear-gradient(135deg, #0d1117 0%, #1a237e 100%);
                      padding: 16px 24px; border-bottom: 1px solid #1e3a8a; }}
            header h1 {{ font-size: 1.6rem; color: #00d4ff;
                         text-shadow: 0 0 12px #00d4ff66; }}
            header p {{ color: #8899aa; font-size: 0.9rem; margin-top: 4px; }}
            .controls {{ display: flex; gap: 12px; padding: 16px 24px; background: #0d1117;
                         border-bottom: 1px solid #1e3a5f; flex-wrap: wrap; align-items: center; }}
            .controls label {{ color: #88aaff; font-weight: bold; }}
            .controls select, .controls input {{
                background: #1a2a3a; color: #eee; border: 1px solid #1e3a5f;
                border-radius: 6px; padding: 6px 10px; font-size: 0.9rem; }}
            .controls button {{
                background: linear-gradient(135deg, #00d4ff, #0060aa);
                color: #000; border: none; border-radius: 6px;
                padding: 8px 18px; font-weight: bold; cursor: pointer; font-size: 0.9rem; }}
            .controls button:hover {{ opacity: 0.85; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
                     padding: 20px 24px; }}
            .card {{ background: #111827; border: 1px solid #1e3a5f;
                     border-radius: 10px; padding: 16px; }}
            .card h2 {{ color: #88aaff; font-size: 1rem; margin-bottom: 12px; }}
            .card img {{ width: 100%; border-radius: 6px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
                            gap: 10px; margin-top: 8px; }}
            .stat {{ background: #0d1117; border: 1px solid #1e3a5f; border-radius: 8px;
                     padding: 10px; text-align: center; }}
            .stat .val {{ font-size: 1.5rem; font-weight: bold; color: #00d4ff; }}
            .stat .lbl {{ font-size: 0.75rem; color: #8899aa; margin-top: 4px; }}
            .full-width {{ grid-column: 1 / -1; }}
            footer {{ text-align: center; padding: 12px; color: #445; font-size: 0.8rem; }}
            @media (max-width: 700px) {{ .grid {{ grid-template-columns: 1fr; }} }}
        </style>
    </head>
    <body>
        <header>
            <h1>🌿 DataLogger — Monitor de Contaminación Ambiental</h1>
            <p>Auto-actualización cada 10 segundos | UMA seleccionada: <strong>UMA{uma_id}</strong></p>
        </header>
        <div class="controls">
            <label>Sensor UMA:</label>
            <select id="selUMA" onchange="cambiarUMA(this.value)">
                {''.join(f'<option value="{i}" {"selected" if i==uma_id else ""}>UMA{i}</option>' for i in range(1,6))}
            </select>
            <label>Últimas:</label>
            <select id="selLimit" onchange="cambiarUMA(document.getElementById('selUMA').value)">
                <option value="20">20</option>
                <option value="50" selected>50</option>
                <option value="100">100</option>
            </select>
            <button onclick="location.reload()">🔄 Actualizar</button>
            <button onclick="window.open('/datos/uma/{uma_id}')">📋 Ver JSON</button>
            <button onclick="window.open('/estadisticas')">📊 Estadísticas</button>
        </div>
        <div class="grid">
            <div class="card full-width">
                <h2>📈 Series de Tiempo — UMA{uma_id}</h2>
                <img src="/grafica/uma/{uma_id}?limit=50&t={{Math.random()}}"
                     id="imgPM" alt="Gráfica PM"
                     onerror="this.alt='Sin datos aún...'">
            </div>
            <div class="card">
                <h2>📊 Histograma de Partículas — UMA{uma_id}</h2>
                <img src="/grafica/histograma?uma={uma_id}&t={{Math.random()}}"
                     id="imgHist" alt="Histograma"
                     onerror="this.alt='Sin datos aún...'">
            </div>
            <div class="card">
                <h2>📋 Estadísticas Globales</h2>
                <div id="statsDiv">Cargando...</div>
            </div>
        </div>
        <footer>INFO1128 — Proyecto 2 (Unidad II) | Flask + SQLite + Matplotlib</footer>
        <script>
            function cambiarUMA(id) {{
                const limit = document.getElementById('selLimit').value;
                window.location.href = '/dashboard?uma=' + id + '&limit=' + limit;
            }}
            // Cargar estadísticas via fetch
            fetch('/estadisticas')
              .then(r => r.json())
              .then(data => {{
                if (!data.length) {{ document.getElementById('statsDiv').innerHTML = 'Sin datos aún.'; return; }}
                let html = '<div class="stats-grid">';
                data.forEach(row => {{
                    html += `<div class="stat"><div class="val">UMA${{row.uma_id}}</div>
                             <div class="lbl">${{row.total}} mediciones</div>
                             <div class="lbl">PM1.0: ${{row.avg_mp01}} μg/m³</div>
                             <div class="lbl">PM2.5: ${{row.avg_mp25}} μg/m³</div>
                             <div class="lbl">PM10:  ${{row.avg_mp10}} μg/m³</div>
                             <div class="lbl">T: ${{row.avg_te}}°C  HR: ${{row.avg_hr}}%</div>
                             </div>`;
                }});
                html += '</div>';
                document.getElementById('statsDiv').innerHTML = html;
              }})
              .catch(() => document.getElementById('statsDiv').innerHTML = 'Error cargando estadísticas.');
        </script>
    </body>
    </html>
    """
    return html


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  DataLogger Flask Server")
    print("  http://127.0.0.1:5000")
    print("  http://127.0.0.1:5000/dashboard")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
