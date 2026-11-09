import pytest

from servidor import crear_app


@pytest.fixture
def cli(tmp_path):
    return crear_app(tmp_path / "s.db").test_client()


def voto(cli, jid, op, pid="videojuegos-01"):
    return cli.post("/api/votar", json={"pregunta_id": pid, "jugador_id": jid, "opcion": op})


def test_votar_y_actualizar_resultados(cli):
    assert voto(cli, "jugador-001", "A").status_code == 201
    assert voto(cli, "jugador-002", "B").status_code == 201
    assert voto(cli, "jugador-003", "B").json["votos_b"] == 2
    r = cli.get("/api/resultados/videojuegos-01?jugador_id=jugador-001").json
    assert (r["votos_a"], r["votos_b"], r["tu_opcion"]) == (1, 2, "A")


def test_no_permite_votar_dos_veces(cli):
    voto(cli, "jugador-001", "A")
    r = voto(cli, "jugador-001", "B")
    assert r.status_code == 409 and r.json["duplicado"] and r.json["tu_opcion"] == "A"
    assert (r.json["votos_a"], r.json["votos_b"]) == (1, 0)


def test_entradas_invalidas(cli):
    assert voto(cli, "x", "A").status_code == 400
    assert voto(cli, "jugador-001", "Z").status_code == 400
    assert voto(cli, "jugador-001", "A", pid="no-existe").status_code == 404
    assert cli.get("/api/preguntas?categoria=nada").status_code == 404


def test_grafico_png_y_pagina(cli):
    voto(cli, "jugador-001", "A")
    g = cli.get("/api/grafico/videojuegos-01.png?eleccion=A")
    assert g.status_code == 200 and g.data[:4] == b"\x89PNG"
    assert cli.get("/").status_code == 200
    assert len(cli.get("/api/preguntas?n=7").json) == 7
    assert cli.get("/api/estadisticas").json["votos_totales"] == 1
