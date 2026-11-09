import os
import requests
from flask import Flask, render_template_string

app = Flask(__name__)

PIHOLE_URL = os.environ.get("PIHOLE_URL", "http://pihole:80")
PIHOLE_PASSWORD = os.environ.get("PIHOLE_PASSWORD", "")

session_id = None

def get_session_id():
    global session_id
    try:
        response = requests.post(f"{PIHOLE_URL}/api/auth", json={"password": PIHOLE_PASSWORD}, timeout=5)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session", {}).get("sid")
            return session_id
    except Exception as e:
        print(f"Error de autenticación con Pi-hole: {e}")
    return None

@app.route("/")
def index():
    global session_id
    if not session_id:
        get_session_id()

    headers = {"X-FTL-SID": session_id} if session_id else {}

    try:
        summary_res = requests.get(f"{PIHOLE_URL}/api/stats/summary", headers=headers, timeout=5)

        if summary_res.status_code == 401:
            if get_session_id():
                headers["X-FTL-SID"] = session_id
                summary_res = requests.get(f"{PIHOLE_URL}/api/stats/summary", headers=headers, timeout=5)

        stats = summary_res.json() if summary_res.status_code == 200 else {}
    except Exception as e:
        print(f"Error al obtener métricas: {e}")
        stats = {}

    # Extraer métricas desde el objeto 'queries' de Pi-hole v6
    queries = stats.get("queries", {})
    total_queries = queries.get("total", "Sin datos")
    blocked_queries = queries.get("blocked", "Sin datos")
    percent_blocked = queries.get("percent_blocked", 0.0)

    html_template = """
    <!doctype html>
    <html>
    <head>
        <title>Pi-hole Reporter</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body { font-family: Arial, sans-serif; background: #f4f6f9; color: #333; text-align: center; padding: 50px; }
            .card { background: white; padding: 20px; margin: 10px auto; width: 300px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            h1 { color: #00529b; }
        </style>
    </head>
    <body>
        <h1>Panel de Métricas - Pi-hole & Unbound</h1>
        <div class="card">
            <h3>Consultas Totales</h3>
            <p>{{ total_queries }}</p>
        </div>
        <div class="card">
            <h3>Consultas Bloqueadas</h3>
            <p>{{ blocked_queries }}</p>
        </div>
        <div class="card">
            <h3>Porcentaje Bloqueado</h3>
            <p>{{ "%.2f"|format(percent_blocked) }}%</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html_template,
        total_queries=total_queries,
        blocked_queries=blocked_queries,
        percent_blocked=percent_blocked
    )

@app.route("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
