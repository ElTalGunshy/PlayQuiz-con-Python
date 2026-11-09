"""Almacenamiento en SQLite de votos, votos demo e historial de partidas.

Se usa en dos sitios:
  * data/servidor.db -> votos REALES (los escribe el servidor Flask).
  * data/local.db    -> modo demostración (votos ficticios) e historial de partidas.
"""
import sqlite3
import zlib
from contextlib import closing
from datetime import datetime

import numpy as np
import pandas as pd

ESQUEMA = """
CREATE TABLE IF NOT EXISTS votos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta_id TEXT NOT NULL,
    jugador_id  TEXT NOT NULL,
    opcion      TEXT NOT NULL CHECK (opcion IN ('A','B')),
    creado      TEXT NOT NULL,
    UNIQUE (pregunta_id, jugador_id)
);
CREATE INDEX IF NOT EXISTS idx_votos_pregunta ON votos (pregunta_id);
CREATE TABLE IF NOT EXISTS base_demo (
    pregunta_id TEXT PRIMARY KEY,
    votos_a INTEGER NOT NULL,
    votos_b INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS partidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jugador_id TEXT NOT NULL,
    modo TEXT NOT NULL,
    categoria TEXT,
    creado TEXT NOT NULL,
    total INTEGER NOT NULL,
    con_mayoria INTEGER NOT NULL,
    con_minoria INTEGER NOT NULL,
    empates INTEGER NOT NULL
);
"""


def ahora():
    return datetime.now().isoformat(timespec="seconds")


def votos_demo_iniciales(pregunta_id):
    """Votos FICTICIOS y reproducibles para una pregunta (semilla = id de la pregunta)."""
    rng = np.random.default_rng(zlib.crc32(pregunta_id.encode("utf-8")))
    total = int(rng.integers(60, 201))
    if rng.random() < 0.06:                       # algunos empates para probar
        total -= total % 2
        return total // 2, total // 2
    a = int(round(total * rng.uniform(0.25, 0.75)))
    return a, total - a


class Almacen:
    def __init__(self, ruta):
        self.ruta = str(ruta)
        with closing(self._con()) as con, con:
            con.executescript(ESQUEMA)

    def _con(self):
        con = sqlite3.connect(self.ruta, timeout=15)
        con.row_factory = sqlite3.Row
        return con

    # ---------- votos ----------
    def registrar_voto(self, pregunta_id, jugador_id, opcion):
        """Guarda un voto. Devuelve (guardado, opcion_registrada).

        Si el jugador ya había votado esa pregunta NO se guarda otra vez y se
        devuelve (False, opcion_anterior).
        """
        if opcion not in ("A", "B"):
            raise ValueError("La opción debe ser 'A' o 'B'.")
        with closing(self._con()) as con:
            try:
                with con:
                    con.execute(
                        "INSERT INTO votos (pregunta_id, jugador_id, opcion, creado) VALUES (?,?,?,?)",
                        (pregunta_id, jugador_id, opcion, ahora()))
                return True, opcion
            except sqlite3.IntegrityError:
                fila = con.execute(
                    "SELECT opcion FROM votos WHERE pregunta_id=? AND jugador_id=?",
                    (pregunta_id, jugador_id)).fetchone()
                return False, fila["opcion"]

    def voto_de(self, pregunta_id, jugador_id):
        with closing(self._con()) as con:
            fila = con.execute("SELECT opcion FROM votos WHERE pregunta_id=? AND jugador_id=?",
                               (pregunta_id, jugador_id)).fetchone()
        return fila["opcion"] if fila else None

    def conteo(self, pregunta_id, con_base_demo=False):
        """(votos_a, votos_b). Con con_base_demo=True suma los votos ficticios de la demo."""
        with closing(self._con()) as con:
            filas = con.execute("SELECT opcion, COUNT(*) n FROM votos WHERE pregunta_id=? GROUP BY opcion",
                                (pregunta_id,)).fetchall()
        n = {f["opcion"]: f["n"] for f in filas}
        a, b = n.get("A", 0), n.get("B", 0)
        if con_base_demo:
            ba, bb = self.base_demo(pregunta_id)
            a, b = a + ba, b + bb
        return a, b

    # ---------- demo ----------
    def base_demo(self, pregunta_id):
        with closing(self._con()) as con:
            fila = con.execute("SELECT votos_a, votos_b FROM base_demo WHERE pregunta_id=?",
                               (pregunta_id,)).fetchone()
        return (fila["votos_a"], fila["votos_b"]) if fila else votos_demo_iniciales(pregunta_id)

    def fijar_base_demo(self, pregunta_id, votos_a, votos_b):
        if votos_a < 0 or votos_b < 0:
            raise ValueError("Los votos no pueden ser negativos.")
        with closing(self._con()) as con, con:
            con.execute("INSERT INTO base_demo (pregunta_id, votos_a, votos_b) VALUES (?,?,?) "
                        "ON CONFLICT(pregunta_id) DO UPDATE SET votos_a=excluded.votos_a, votos_b=excluded.votos_b",
                        (pregunta_id, int(votos_a), int(votos_b)))

    def reiniciar_demo(self):
        """Borra los votos ficticios de la demo y vuelve a los valores iniciales reproducibles."""
        with closing(self._con()) as con, con:
            con.execute("DELETE FROM votos WHERE jugador_id LIKE 'demo-%'")
            con.execute("DELETE FROM base_demo")

    def borrar_votos(self):
        with closing(self._con()) as con, con:
            con.execute("DELETE FROM votos")

    # ---------- historial y estadísticas ----------
    def registrar_partida(self, jugador_id, modo, categoria, total, con_mayoria, con_minoria, empates):
        with closing(self._con()) as con, con:
            con.execute("INSERT INTO partidas (jugador_id, modo, categoria, creado, total, con_mayoria, "
                        "con_minoria, empates) VALUES (?,?,?,?,?,?,?,?)",
                        (jugador_id, modo, categoria, ahora(), total, con_mayoria, con_minoria, empates))

    def historial(self):
        with closing(self._con()) as con:
            return pd.read_sql_query("SELECT * FROM partidas ORDER BY id DESC", con)

    def votos_por_pregunta(self):
        """DataFrame con pregunta_id, votos_a, votos_b, total (solo votos guardados en votos)."""
        with closing(self._con()) as con:
            df = pd.read_sql_query(
                "SELECT pregunta_id, "
                "SUM(CASE WHEN opcion='A' THEN 1 ELSE 0 END) AS votos_a, "
                "SUM(CASE WHEN opcion='B' THEN 1 ELSE 0 END) AS votos_b "
                "FROM votos GROUP BY pregunta_id", con)
        df["total"] = df["votos_a"] + df["votos_b"]
        return df
