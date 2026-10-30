import base64
from datetime import datetime, timedelta
import io
import os
import sqlite3
import threading

from flask import Flask, jsonify, request, send_file
import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), 'datalogger.db')
plot_lock = threading.Lock()


def init_db():
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


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def parse_fecha(f_str):
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'):
        try:
            return datetime.strptime(f_str, fmt)
        except Exception:
            pass
    return datetime.now()


def generar_grafica_pm(rows, titulo='Series de Tiempo - Material Particulado'):
    with plot_lock:
        fig = plt.figure(figsize=(12, 9), facecolor='#0d1117')
        if not rows:
            ax = fig.add_subplot(111)
            ax.set_facecolor('#0d1117')
            ax.text(0.5, 0.5, f'{titulo}\n\n(Esperando datos de la estación...)',
                    ha='center', va='center', fontsize=14, color='#00d4ff')
            ax.axis('off')
        else:
            fechas = [parse_fecha(r['fecha']) for r in rows]
            mp01 = [r['mp01'] or 0 for r in rows]
            mp25 = [r['mp25'] or 0 for r in rows]
            mp10 = [r['mp10'] or 0 for r in rows]
            te = [r['te'] or 0 for r in rows]
            hr = [r['hr'] or 0 for r in rows]

            ax1 = fig.add_subplot(3, 1, 1)
            ax2 = fig.add_subplot(3, 1, 2, sharex=ax1)
            ax3 = fig.add_subplot(3, 1, 3, sharex=ax1)

            for ax in (ax1, ax2, ax3):
                ax.set_facecolor('#0d1117')
                ax.tick_params(colors='white')
                ax.spines[:].set_color('#333')
                ax.grid(True, alpha=0.25, color='#444')

            ax1.plot(fechas, mp01, color='#ff4444', linewidth=2, label='PM1.0 μg/m³', marker='o', markersize=4)
            ax1.plot(fechas, mp25, color='#22c55e', linewidth=2, label='PM2.5 μg/m³', marker='s', markersize=4)
            ax1.plot(fechas, mp10, color='#38bdf8', linewidth=2, label='PM10 μg/m³', marker='^', markersize=4)
            ax1.set_ylabel('Concentración (μg/m³)', color='white')
            ax1.set_title(titulo, color='white', fontsize=13, fontweight='bold', pad=10)
            ax1.legend(loc='upper right', facecolor='#1e293b', labelcolor='white', framealpha=0.85)

            ax2.plot(fechas, te, color='#f59e0b', linewidth=2, label='Temperatura (°C)', marker='o', markersize=4)
            ax2.set_ylabel('Temp (°C)', color='white')
            ax2.legend(loc='upper right', facecolor='#1e293b', labelcolor='white', framealpha=0.85)

            ax3.plot(fechas, hr, color='#06b6d4', linewidth=2, label='Humedad Relativa (%)', marker='o', markersize=4)
            ax3.set_ylabel('HR (%)', color='white')
            ax3.set_xlabel('Hora de Registro', color='white')
            ax3.legend(loc='upper right', facecolor='#1e293b', labelcolor='white', framealpha=0.85)

            if len(fechas) == 1:
                t0 = fechas[0]
                ax3.set_xlim(t0 - timedelta(minutes=2), t0 + timedelta(minutes=2))

            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            fig.autofmt_xdate(rotation=25)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf


def generar_histograma(uma_id=None):
    with plot_lock:
        con = get_db()
        if uma_id:
            row = con.execute('''
                SELECT AVG(h03) h03, AVG(h05) h05, AVG(h10) h10,
                       AVG(h25) h25, AVG(h50) h50, AVG(h100) h100
                FROM mediciones WHERE uma_id=?
            ''', (uma_id,)).fetchone()
            titulo = f'Histograma de Partículas — UMA{uma_id}'
        else:
            row = con.execute('''
                SELECT AVG(h03) h03, AVG(h05) h05, AVG(h10) h10,
                       AVG(h25) h25, AVG(h50) h50, AVG(h100) h100
                FROM mediciones
            ''').fetchone()
            titulo = 'Histograma de Partículas (Promedio Global)'
        con.close()

        labels = ['0.3 μm', '0.5 μm', '1.0 μm', '2.5 μm', '5.0 μm', '10 μm']
        if row and any(row[k] is not None for k in ['h03', 'h05', 'h10', 'h25', 'h50', 'h100']):
            valores = [
                row['h03'] or 0, row['h05'] or 0, row['h10'] or 0,
                row['h25'] or 0, row['h50'] or 0, row['h100'] or 0
            ]
        else:
            valores = [0, 0, 0, 0, 0, 0]

        colores = ['#ef4444', '#f97316', '#3b82f6', '#22c55e', '#eab308', '#a855f7']

        fig = plt.figure(figsize=(9, 4.5), facecolor='#0d1117')
        ax = fig.add_subplot(111)
        ax.set_facecolor('#0d1117')
        bars = ax.bar(labels, valores, color=colores, edgecolor='#334155', linewidth=0.8)
        ax.set_title(titulo, color='white', fontsize=13, fontweight='bold', pad=10)
        ax.set_xlabel('Diámetro de Partícula', color='white')
        ax.set_ylabel('Conteo Promedio', color='white')
        ax.tick_params(colors='white')
        ax.spines[:].set_color('#333')
        ax.grid(True, axis='y', alpha=0.25, color='#444')

        for bar, val in zip(bars, valores):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (max(valores) * 0.02 if valores else 1),
                    f'{val:.0f}', ha='center', va='bottom', color='white', fontsize=9, fontweight='bold')

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf


@app.route('/', methods=['GET'])
def index():
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>DataLogger UMA - API</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a1a; color: #eee; margin: 0; padding: 20px; }
        h1 { color: #00d4ff; text-shadow: 0 0 10px rgba(0,212,255,0.3); }
        h2 { color: #88aaff; }
        a { color: #00ffcc; text-decoration: none; font-weight: bold; }
        a:hover { text-decoration: underline; }
        .card { background: #111827; border: 1px solid #1e3a5f; border-radius: 8px; padding: 16px; margin: 12px 0; max-width: 700px; }
        code { background: #1a2a3a; padding: 2px 6px; border-radius: 4px; color: #00d4ff; }
        .badge { display: inline-block; background: #00d4ff; color: #000; border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 0.8em; }
    </style>
</head>
<body>
    <h1>DataLogger - Monitor de Contaminación Ambiental</h1>
    <p>Servidor Flask activo | Base de datos SQLite</p>
    <div class="card">
        <h2>Endpoints disponibles</h2>
        <ul>
            <li><span class="badge">POST</span> <code>/datos</code> - Registrar medición (JSON)</li>
            <li><span class="badge">GET</span>  <code>/datos</code> - Listar mediciones (JSON)</li>
            <li><span class="badge">GET</span>  <code>/datos/uma/&lt;id&gt;</code> - Filtrar por UMA (JSON)</li>
            <li><span class="badge">GET</span>  <code>/datos/ultimas/&lt;n&gt;</code> - Últimas N mediciones (JSON)</li>
            <li><span class="badge">GET</span>  <code>/grafica</code> - Gráfica temporal (PNG)</li>
            <li><span class="badge">GET</span>  <code>/grafica/uma/&lt;id&gt;</code> - Gráfica de una UMA (PNG)</li>
            <li><span class="badge">GET</span>  <code>/dashboard</code> - Dashboard web visual</li>
            <li><span class="badge">GET</span>  <code>/estadisticas</code> - Estadísticas por UMA (JSON)</li>
        </ul>
    </div>
    <p><a href="/dashboard">Ver Dashboard</a> | <a href="/datos">Ver datos JSON</a></p>
</body>
</html>"""


@app.route('/datos', methods=['POST'])
def recibir_datos():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'JSON inválido'}), 400

        uma_id = int(data.get('id', 0))
        mp01 = int(data.get('mp01', 0))
        mp25 = int(data.get('mp25', 0))
        mp10 = int(data.get('mp10', 0))
        h03 = int(data.get('h03', 0))
        h05 = int(data.get('h05', 0))
        h10 = int(data.get('h10', 0))
        h25 = int(data.get('h25', 0))
        h50 = int(data.get('h50', 0))
        h100 = int(data.get('h100', 0))
        te = int(data.get('te', 0))
        hr = int(data.get('hr', 0))
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        con = get_db()
        con.execute('''
            INSERT INTO mediciones
              (uma_id,mp01,mp25,mp10,h03,h05,h10,h25,h50,h100,te,hr,fecha)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uma_id, mp01, mp25, mp10, h03, h05, h10, h25, h50, h100, te, hr, fecha))
        con.commit()
        con.close()

        print(f"[{fecha}] UMA{uma_id} PM1={mp01} PM2.5={mp25} PM10={mp10} T={te}C HR={hr}%")
        return jsonify({'status': 'ok', 'fecha': fecha}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/datos', methods=['GET'])
def listar_datos():
    try:
        limit = request.args.get('limit', 100, type=int)
        con = get_db()
        rows = con.execute('SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/datos/uma/<int:uma_id>', methods=['GET'])
def datos_por_uma(uma_id):
    try:
        limit = request.args.get('limit', 100, type=int)
        con = get_db()
        rows = con.execute('SELECT * FROM mediciones WHERE uma_id=? ORDER BY id DESC LIMIT ?', (uma_id, limit)).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/datos/ultimas/<int:n>', methods=['GET'])
def ultimas_n(n):
    try:
        con = get_db()
        rows = con.execute('SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (n,)).fetchall()
        con.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/estadisticas', methods=['GET'])
def estadisticas():
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


@app.route('/grafica', methods=['GET'])
def grafica_general():
    try:
        limit = request.args.get('limit', 50, type=int)
        con = get_db()
        rows = con.execute('SELECT * FROM mediciones ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        con.close()
        rows = list(reversed(rows))
        buf = generar_grafica_pm(rows, 'Todos los sensores UMA')
        return send_file(buf, mimetype='image/png', max_age=0)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/grafica/uma/<int:uma_id>', methods=['GET'])
def grafica_uma(uma_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        con = get_db()
        rows = con.execute('SELECT * FROM mediciones WHERE uma_id=? ORDER BY id DESC LIMIT ?', (uma_id, limit)).fetchall()
        con.close()
        rows = list(reversed(rows))
        buf = generar_grafica_pm(rows, f'UMA{uma_id} — Material Particulado')
        return send_file(buf, mimetype='image/png', max_age=0)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/grafica/histograma', methods=['GET'])
def grafica_histograma():
    try:
        uma_id = request.args.get('uma', None, type=int)
        buf = generar_histograma(uma_id)
        return send_file(buf, mimetype='image/png', max_age=0)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard', methods=['GET'])
def dashboard():
    uma_id = request.args.get('uma', 1, type=int)
    limit = request.args.get('limit', 50, type=int)

    con = get_db()
    rows = con.execute('SELECT * FROM mediciones WHERE uma_id=? ORDER BY id DESC LIMIT ?', (uma_id, limit)).fetchall()
    con.close()
    rows = list(reversed(rows))

    buf_pm = generar_grafica_pm(rows, f'UMA{uma_id} — Material Particulado')
    b64_pm = base64.b64encode(buf_pm.getvalue()).decode('utf-8')

    buf_hist = generar_histograma(uma_id)
    b64_hist = base64.b64encode(buf_hist.getvalue()).decode('utf-8')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="10">
    <title>Dashboard DataLogger UMA{uma_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0a0a1a; color: #eee; }}
        header {{ background: linear-gradient(135deg, #0d1117 0%, #1a237e 100%); padding: 16px 24px; border-bottom: 1px solid #1e3a8a; }}
        header h1 {{ font-size: 1.6rem; color: #00d4ff; text-shadow: 0 0 12px rgba(0,212,255,0.4); }}
        header p {{ color: #94a3b8; font-size: 0.9rem; margin-top: 4px; }}
        .controls {{ display: flex; gap: 12px; padding: 14px 24px; background: #0d1117; border-bottom: 1px solid #1e293b; flex-wrap: wrap; align-items: center; }}
        .controls label {{ color: #38bdf8; font-weight: bold; font-size: 0.9rem; }}
        .controls select {{ background: #1e293b; color: #eee; border: 1px solid #334155; border-radius: 6px; padding: 6px 12px; font-size: 0.9rem; cursor: pointer; }}
        .controls button {{
            background: linear-gradient(135deg, #00d4ff, #0284c7);
            color: #04101e; border: none; border-radius: 6px;
            padding: 7px 16px; font-weight: bold; cursor: pointer; font-size: 0.85rem;
            transition: transform 0.1s, opacity 0.1s;
        }}
        .controls button:hover {{ opacity: 0.9; transform: scale(1.02); }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 20px 24px; }}
        .card {{ background: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }}
        .card h2 {{ color: #38bdf8; font-size: 1rem; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; }}
        .card img {{ width: 100%; border-radius: 6px; display: block; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; margin-top: 8px; }}
        .stat {{ background: #0d1117; border: 1px solid #1e293b; border-radius: 8px; padding: 10px; text-align: center; }}
        .stat .val {{ font-size: 1.4rem; font-weight: bold; color: #00d4ff; }}
        .stat .lbl {{ font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }}
        .full-width {{ grid-column: 1 / -1; }}
        footer {{ text-align: center; padding: 14px; color: #64748b; font-size: 0.8rem; border-top: 1px solid #1e293b; margin-top: 10px; }}
        @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <header>
        <h1>DataLogger — Monitor de Contaminación Ambiental</h1>
        <p>Actualización cada 10s | Estación activa: <strong>UMA{uma_id}</strong> | Registros: {len(rows)}</p>
    </header>
    <div class="controls">
        <label>Seleccionar UMA:</label>
        <select id="selUMA" onchange="cambiarVista()">
            {''.join(f'<option value="{i}" {"selected" if i==uma_id else ""}>UMA {i}</option>' for i in range(1,6))}
        </select>
        <label>Muestras:</label>
        <select id="selLimit" onchange="cambiarVista()">
            <option value="20" {"selected" if limit==20 else ""}>20</option>
            <option value="50" {"selected" if limit==50 else ""}>50</option>
            <option value="100" {"selected" if limit==100 else ""}>100</option>
        </select>
        <button onclick="location.reload()">Actualizar</button>
        <button onclick="window.open('/datos/uma/{uma_id}')">JSON UMA{uma_id}</button>
        <button onclick="window.open('/estadisticas')">Estadísticas</button>
    </div>
    <div class="grid">
        <div class="card full-width">
            <h2>Series Temporales — UMA{uma_id}</h2>
            <img src="data:image/png;base64,{b64_pm}" alt="Series Temporales UMA{uma_id}">
        </div>
        <div class="card">
            <h2>Histograma de Partículas — UMA{uma_id}</h2>
            <img src="data:image/png;base64,{b64_hist}" alt="Histograma UMA{uma_id}">
        </div>
        <div class="card">
            <h2>Resumen por Estación UMA</h2>
            <div id="statsDiv">Cargando...</div>
        </div>
    </div>
    <footer>INFO1128 — Unidad II | DataLogger UMA</footer>
    <script>
        function cambiarVista() {{
            const uma = document.getElementById('selUMA').value;
            const lim = document.getElementById('selLimit').value;
            window.location.href = '/dashboard?uma=' + uma + '&limit=' + lim;
        }}
        fetch('/estadisticas')
            .then(r => r.json())
            .then(data => {{
                if (!data || !data.length) {{
                    document.getElementById('statsDiv').innerHTML = '<p style="color:#94a3b8;padding:12px;">Sin registros aún.</p>';
                    return;
                }}
                let html = '<div class="stats-grid">';
                data.forEach(r => {{
                    html += `<div class="stat">
                        <div class="val">UMA${{r.uma_id}}</div>
                        <div class="lbl">${{r.total}} registros</div>
                        <div class="lbl">PM1.0: ${{r.avg_mp01}}</div>
                        <div class="lbl">PM2.5: ${{r.avg_mp25}}</div>
                        <div class="lbl">PM10: ${{r.avg_mp10}}</div>
                        <div class="lbl">${{r.avg_te}}°C | ${{r.avg_hr}}%</div>
                    </div>`;
                }});
                html += '</div>';
                document.getElementById('statsDiv').innerHTML = html;
            }})
            .catch(() => {{
                document.getElementById('statsDiv').innerHTML = '<p style="color:#ef4444;padding:12px;">Error al cargar estadísticas.</p>';
            }});
    </script>
</body>
</html>"""
    return html


if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("  DataLogger Flask Server")
    print("  http://127.0.0.1:5000")
    print("  http://127.0.0.1:5000/dashboard")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
