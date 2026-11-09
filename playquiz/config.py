"""Rutas y valores de configuración compartidos por todo el proyecto."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
PREGUNTAS = DATA / "preguntas.json"   # banco de preguntas (editable)
LOCAL_DB = DATA / "local.db"          # modo demo + historial de partidas del equipo
SERVIDOR_DB = DATA / "servidor.db"    # votos reales (los escribe el servidor Flask)
JUGADOR = DATA / "jugador.json"       # identificador anónimo de este equipo
URL_SERVIDOR = "http://127.0.0.1:5000"
PREGUNTAS_POR_PARTIDA = (5, 10, 15, 20)

OPCIONES = ("A", "B")

# Máximo de jugadores en una mesa local. Súbelo o bájalo si lo necesitas (mínimo 1).
MAX_JUGADORES = 40
