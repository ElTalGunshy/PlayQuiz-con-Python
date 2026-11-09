"""Estadísticas generales de los votos guardados.

Uso:  python -m playquiz.estadisticas --db data/servidor.db --csv resultados.csv
"""
import argparse

import pandas as pd

from . import config
from .almacen import Almacen
from .banco import Banco


def tabla_general(almacen, banco):
    """Una fila por pregunta (incluidas las que aún no tienen votos)."""
    votos = almacen.votos_por_pregunta()
    df = banco.df.merge(votos, how="left", left_on="id", right_on="pregunta_id")
    for col in ("votos_a", "votos_b", "total"):
        df[col] = df[col].fillna(0).astype(int)
    df["ganadora"] = df.apply(
        lambda f: "sin votos" if f["total"] == 0 else
        "empate" if f["votos_a"] == f["votos_b"] else
        (f["opcion_a"] if f["votos_a"] > f["votos_b"] else f["opcion_b"]), axis=1)
    return df.drop(columns=["pregunta_id"])


def resumen_por_categoria(tabla):
    return (tabla.groupby("categoria")[["votos_a", "votos_b", "total"]].sum()
            .sort_values("total", ascending=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(config.SERVIDOR_DB))
    p.add_argument("--csv", help="archivo CSV de salida")
    args = p.parse_args()
    tabla = tabla_general(Almacen(args.db), Banco())
    print(f"Votos totales: {int(tabla['total'].sum())}  |  preguntas con votos: {(tabla['total'] > 0).sum()}")
    with pd.option_context("display.max_rows", 20, "display.width", 120):
        print(resumen_por_categoria(tabla).head(10))
    if args.csv:
        tabla.to_csv(args.csv, index=False, encoding="utf-8-sig")
        print("CSV guardado en", args.csv)


if __name__ == "__main__":
    main()
