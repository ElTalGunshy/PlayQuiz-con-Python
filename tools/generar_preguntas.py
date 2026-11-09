# -*- coding: utf-8 -*-
"""Genera data/preguntas.json a partir de los archivos datos_*.py.

Uso:  python tools/generar_preguntas.py
Edita los datos_*.py (o directamente data/preguntas.json) para ampliar el banco.
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from datos_1 import DATOS as D1  # noqa: E402
from datos_2 import DATOS as D2  # noqa: E402
from datos_3 import DATOS as D3  # noqa: E402
from datos_4 import DATOS as D4  # noqa: E402
from datos_5 import DATOS as D5  # noqa: E402


def construir():
    categorias, preguntas = [], []
    for cid, nombre, emoji, items in D1 + D2 + D3 + D4 + D5:
        categorias.append({"id": cid, "nombre": nombre, "emoji": emoji})
        for n, (q, a, b) in enumerate(items, start=1):
            preguntas.append({
                "id": f"{cid}-{n:02d}",
                "categoria": cid,
                "pregunta": q,
                "opcion_a": a,
                "opcion_b": b,
            })
    return {"version": 1, "categorias": categorias, "preguntas": preguntas}


if __name__ == "__main__":
    datos = construir()
    destino = AQUI.parent / "data" / "preguntas.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(datos['categorias'])} categorías, {len(datos['preguntas'])} preguntas -> {destino}")
