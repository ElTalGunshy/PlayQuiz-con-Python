"""Servidor de votación REAL (Flask + SQLite).

Uso:  python servidor.py --host 0.0.0.0 --port 5000
Desde otros dispositivos de la misma red abre  http://IP-DE-ESTA-PC:5000
"""
import argparse
import re

from flask import Flask, Response, jsonify, request

from playquiz import config, graficos
from playquiz.almacen import Almacen
from playquiz.banco import Banco
from playquiz.estadisticas import tabla_general
from playquiz.web import PAGINA

ID_VALIDO = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


def crear_app(ruta_db=None, ruta_preguntas=None):
    app = Flask(__name__)
    banco = Banco(ruta_preguntas)
    almacen = Almacen(ruta_db or config.SERVIDOR_DB)

    def error(msg, codigo):
        return jsonify(error=msg), codigo

    @app.get("/")
    @app.get("/jugar")
    def pagina():
        return Response(PAGINA, mimetype="text/html")

    @app.get("/api/salud")
    def salud():
        return jsonify(ok=True, preguntas=len(banco.df))

    @app.get("/api/categorias")
    def categorias():
        return jsonify(banco.categorias)

    @app.get("/api/preguntas")
    def preguntas():
        cat = request.args.get("categoria") or None
        if cat and cat not in {c["id"] for c in banco.categorias}:
            return error("Categoría desconocida.", 404)
        n = max(1, min(request.args.get("n", 10, type=int), 50))
        return jsonify(banco.aleatorias(n, cat))

    @app.post("/api/votar")
    def votar():
        d = request.get_json(silent=True) or {}
        pid, jid, op = d.get("pregunta_id"), d.get("jugador_id"), d.get("opcion")
        if not isinstance(jid, str) or not ID_VALIDO.match(jid):
            return error("jugador_id inválido (8-64 caracteres alfanuméricos).", 400)
        if op not in ("A", "B"):
            return error("La opción debe ser 'A' o 'B'.", 400)
        try:
            banco.obtener(pid)
        except KeyError:
            return error("Pregunta desconocida.", 404)
        guardado, registrada = almacen.registrar_voto(pid, jid, op)
        a, b = almacen.conteo(pid)
        return jsonify(votos_a=a, votos_b=b, tu_opcion=registrada, duplicado=not guardado,
                       error=None if guardado else "Ya habías votado esta pregunta."), (201 if guardado else 409)

    @app.get("/api/resultados/<pid>")
    def resultados(pid):
        try:
            banco.obtener(pid)
        except KeyError:
            return error("Pregunta desconocida.", 404)
        a, b = almacen.conteo(pid)
        jid = request.args.get("jugador_id")
        return jsonify(votos_a=a, votos_b=b, tu_opcion=almacen.voto_de(pid, jid) if jid else None)

    @app.get("/api/grafico/<pid>.png")
    def grafico(pid):
        try:
            q = banco.obtener(pid)
        except KeyError:
            return error("Pregunta desconocida.", 404)
        a, b = almacen.conteo(pid)
        eleccion = request.args.get("eleccion")
        fig = graficos.crear_figura()
        graficos.dibujar_resultados(fig, q["pregunta"], q["opcion_a"], q["opcion_b"], a, b,
                                    eleccion if eleccion in ("A", "B") else None)
        resp = Response(graficos.figura_a_png(fig), mimetype="image/png")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/api/estadisticas")
    def estadisticas():
        t = tabla_general(almacen, banco)
        return jsonify(votos_totales=int(t["total"].sum()),
                       preguntas_con_votos=int((t["total"] > 0).sum()),
                       por_categoria=t.groupby("categoria")["total"].sum().to_dict())

    return app


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5000)
    args = p.parse_args()
    config.DATA.mkdir(exist_ok=True)
    crear_app().run(host=args.host, port=args.port, threaded=True)
