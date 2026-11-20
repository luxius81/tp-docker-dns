import os
import requests
from flask import Flask, render_template_string

app = Flask(__name__)

PIHOLE_URL = os.environ.get("PIHOLE_URL", "http://pihole:80")
PIHOLE_PASSWORD = os.environ.get("PIHOLE_PASSWORD", "")

session_id = None


def get_session_id():
    """Se autentica contra la API de Pi-hole v6 y guarda el sid para reutilizarlo."""
    global session_id
    try:
        response = requests.post(
            f"{PIHOLE_URL}/api/auth",
            json={"password": PIHOLE_PASSWORD},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            session_id = data.get("session", {}).get("sid")
            return session_id
    except Exception as e:
        print(f"Error de autenticación con Pi-hole: {e}")
    return None


def api_get(path):
    """GET autenticado a la API de Pi-hole.
    Reutiliza el sid; si la API responde 401, se vuelve a autenticar y reintenta una vez.
    Si algo falla devuelve {} para que la página muestre "Sin datos" en vez de romperse."""
    global session_id
    if not session_id:
        get_session_id()

    for _ in range(2):
        headers = {"X-FTL-SID": session_id} if session_id else {}
        try:
            r = requests.get(f"{PIHOLE_URL}{path}", headers=headers, timeout=5)
            if r.status_code == 401 and get_session_id():
                continue
            return r.json() if r.status_code == 200 else {}
        except Exception as e:
            print(f"Error al consultar {path}: {e}")
            return {}
    return {}


HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Pi-hole Reporter</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; color: #333; text-align: center; padding: 50px; }
        .card { background: white; padding: 20px; margin: 10px auto; width: 300px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #00529b; }
        table { width: 100%; text-align: left; border-collapse: collapse; }
        td { padding: 4px 0; word-break: break-all; }
        td.count { text-align: right; padding-left: 10px; }
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
    <div class="card">
        <h3>Dominios más bloqueados</h3>
        {% if top_domains %}
        <table>
            {% for d in top_domains %}
            <tr><td>{{ d.domain }}</td><td class="count">{{ d.count }}</td></tr>
            {% endfor %}
        </table>
        {% else %}
        <p>Sin datos</p>
        {% endif %}
    </div>
</body>
</html>
"""


@app.route("/")
def index():
    stats = api_get("/api/stats/summary")
    top = api_get("/api/stats/top_domains?blocked=true")

    # Extraer métricas desde el objeto 'queries' de Pi-hole v6
    queries = stats.get("queries", {})
    total_queries = queries.get("total", "Sin datos")
    blocked_queries = queries.get("blocked", "Sin datos")
    percent_blocked = queries.get("percent_blocked", 0.0)

    # Top 10 de dominios bloqueados
    top_domains = top.get("domains", [])[:10]

    return render_template_string(
        HTML_TEMPLATE,
        total_queries=total_queries,
        blocked_queries=blocked_queries,
        percent_blocked=percent_blocked,
        top_domains=top_domains,
    )


@app.route("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
