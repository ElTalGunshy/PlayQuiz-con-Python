"""Carga y validación del banco de preguntas (data/preguntas.json) con pandas/NumPy."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

COLUMNAS = ["id", "categoria", "pregunta", "opcion_a", "opcion_b"]


class ErrorBanco(ValueError):
    pass


class Banco:
    def __init__(self, ruta=None):
        self.ruta = Path(ruta) if ruta else config.PREGUNTAS
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.categorias = datos["categorias"]
        self.df = pd.DataFrame(datos["preguntas"], columns=COLUMNAS)
        self._cat = {c["id"]: c for c in self.categorias}
        self.validar()

    # ---------- validación ----------
    def validar(self):
        if self.df["id"].duplicated().any():
            raise ErrorBanco("Hay identificadores de pregunta repetidos.")
        if len(self._cat) != len(self.categorias):
            raise ErrorBanco("Hay identificadores de categoría repetidos.")
        desconocidas = set(self.df["categoria"]) - set(self._cat)
        if desconocidas:
            raise ErrorBanco(f"Categorías no declaradas: {sorted(desconocidas)}")
        for col in COLUMNAS:
            if self.df[col].isna().any() or (self.df[col].astype(str).str.strip() == "").any():
                raise ErrorBanco(f"La columna '{col}' tiene valores vacíos.")
        if (self.df["opcion_a"].str.strip() == self.df["opcion_b"].str.strip()).any():
            raise ErrorBanco("Hay preguntas con dos opciones idénticas.")

    # ---------- consultas ----------
    def categoria(self, cid):
        return self._cat[cid]

    def preguntas(self, categoria=None):
        df = self.df if categoria is None else self.df[self.df["categoria"] == categoria]
        return df.to_dict("records")

    def obtener(self, pregunta_id):
        fila = self.df[self.df["id"] == pregunta_id]
        if fila.empty:
            raise KeyError(pregunta_id)
        return fila.iloc[0].to_dict()

    def aleatorias(self, n, categoria=None, semilla=None):
        """Devuelve hasta n preguntas distintas, en orden aleatorio."""
        df = self.df if categoria is None else self.df[self.df["categoria"] == categoria]
        n = min(int(n), len(df))
        rng = np.random.default_rng(semilla)
        indices = rng.choice(len(df), size=n, replace=False)
        return df.iloc[indices].to_dict("records")

    def conteo_por_categoria(self):
        return self.df.groupby("categoria").size()
