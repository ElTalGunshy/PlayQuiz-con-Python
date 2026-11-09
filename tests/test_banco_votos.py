import pytest

from playquiz import config
from playquiz.almacen import Almacen, votos_demo_iniciales
from playquiz.banco import Banco
from playquiz.estadisticas import tabla_general
from playquiz.juego import Partida
from playquiz.votos import FuenteDemo


@pytest.fixture
def almacen(tmp_path):
    return Almacen(tmp_path / "t.db")


def test_banco_tiene_500_preguntas_en_50_categorias():
    b = Banco()
    assert len(b.df) == 500 and len(b.categorias) == 50
    assert set(b.conteo_por_categoria()) == {10}
    assert b.df["id"].is_unique
    assert (b.df["opcion_a"] != b.df["opcion_b"]).all()


def test_aleatorias_por_categoria_y_semilla():
    b = Banco()
    qs = b.aleatorias(5, "futbol", semilla=3)
    assert len(qs) == 5 and {q["categoria"] for q in qs} == {"futbol"}
    assert qs == b.aleatorias(5, "futbol", semilla=3)
    assert len(b.aleatorias(99, "futbol")) == 10


def test_voto_unico_por_jugador(almacen):
    assert almacen.registrar_voto("p1", "jugador-uno", "A") == (True, "A")
    assert almacen.registrar_voto("p1", "jugador-uno", "B") == (False, "A")   # no cambia ni suma
    almacen.registrar_voto("p1", "jugador-dos", "B")
    assert almacen.conteo("p1") == (1, 1)
    with pytest.raises(ValueError):
        almacen.registrar_voto("p1", "x", "C")


def test_demo_es_reproducible_editable_y_suma_el_voto(almacen):
    assert votos_demo_iniciales("videojuegos-01") == votos_demo_iniciales("videojuegos-01")
    f = FuenteDemo(almacen)
    a0, b0 = almacen.base_demo("videojuegos-01")
    r = f.votar("videojuegos-01", "A")
    assert (r.votos_a, r.votos_b) == (a0 + 1, b0)
    f.editar_base("videojuegos-01", 72, 48)
    assert almacen.conteo("videojuegos-01", con_base_demo=True) == (73, 48)
    with pytest.raises(ValueError):
        f.editar_base("videojuegos-01", -1, 3)


def test_partida_un_jugador_y_veredictos():
    qs = Banco().aleatorias(3, semilla=1)
    p = Partida(qs)
    p.votar("A", 10, 5)
    with pytest.raises(RuntimeError):
        p.votar("B", 1, 1)                     # ya votó el único jugador
    assert p.avanzar()
    p.votar("B", 4, 4)
    p.avanzar()
    p.votar("A", 1, 9)
    assert not p.avanzar() and p.terminada
    assert p.resumen() == {"mayoria": 1, "minoria": 1, "empate": 1}


def test_varios_jugadores_votan_por_turnos_y_el_orden_rota():
    p = Partida(Banco().aleatorias(3, semilla=2), jugadores=["Ana", "Beto", "Cami"])
    assert p.turno == 0
    assert p.votar("A", 5, 5) == 0 and p.turno == 1
    with pytest.raises(RuntimeError):
        p.avanzar()                            # faltan jugadores
    p.votar("B", 5, 6)
    p.votar("B", 5, 7)
    assert p.ronda.completa and p.ronda.votos_mesa == (1, 2)
    with pytest.raises(RuntimeError):
        p.votar("A", 6, 7)
    p.avanzar()
    assert p.turno == 1                        # en la siguiente pregunta empieza Beto
    assert (p.ronda.votos_a, p.ronda.votos_b) == (0, 0)


def test_resumen_por_jugador():
    p = Partida(Banco().aleatorias(1, semilla=4), jugadores=["Ana", "Beto"])
    p.votar("A", 1, 0)
    p.votar("B", 1, 1)
    p.actualizar_totales(10, 4)                # totales finales: gana A
    filas = {f["jugador"]: f for f in p.resumen_por_jugador()}
    assert filas["Ana"]["mayoria"] == 1 and filas["Beto"]["minoria"] == 1
    with pytest.raises(ValueError):
        Partida(Banco().aleatorias(1), jugadores=[])
    big = Partida(Banco().aleatorias(1), jugadores=[f"J{i}" for i in range(25)])   # más de 6 jugadores
    assert big.n_jugadores == 25 and big.ronda.orden == list(range(25))
    with pytest.raises(ValueError):
        Partida(Banco().aleatorias(1), jugadores=[str(i) for i in range(config.MAX_JUGADORES + 1)])


def test_demo_cada_jugador_de_la_mesa_suma_un_voto(almacen):
    f = FuenteDemo(almacen)
    a0, b0 = almacen.base_demo("futbol-02")
    r1 = f.votar("futbol-02", "A", f.id_jugador(0))
    r2 = f.votar("futbol-02", "A", f.id_jugador(1))
    r3 = f.votar("futbol-02", "B", f.id_jugador(2))
    assert (r1.votos_a, r2.votos_a, r3.votos_a) == (a0 + 1, a0 + 2, a0 + 2)
    assert r3.votos_b == b0 + 1


def test_estadisticas_generales(almacen):
    almacen.registrar_voto("videojuegos-01", "jugador-uno", "A")
    t = tabla_general(almacen, Banco())
    assert len(t) == 500 and t["total"].sum() == 1
    assert t.loc[t["id"] == "videojuegos-01", "ganadora"].item() == "Minecraft"


def test_fuente_local_empieza_en_cero_y_no_duplica(tmp_path):
    from playquiz.votos import FuenteLocal
    f = FuenteLocal()
    assert (f.resultados("p1").votos_a, f.resultados("p1").votos_b) == (0, 0)
    assert f.votar("p1", "A", f.id_jugador(0)).votos_a == 1
    r = f.votar("p1", "B", f.id_jugador(1))
    assert (r.votos_a, r.votos_b) == (1, 1)
    dup = f.votar("p1", "B", f.id_jugador(0))             # el jugador 0 ya había votado A
    assert dup.duplicado and dup.tu_opcion == "A" and (dup.votos_a, dup.votos_b) == (1, 1)
    assert FuenteLocal().resultados("p1").votos_a == 0     # cada sesión empieza limpia


def test_reiniciar_datos_demo(almacen):
    f = FuenteDemo(almacen)
    base = almacen.base_demo("futbol-03")
    f.editar_base("futbol-03", 9, 9)
    f.votar("futbol-03", "A")
    assert almacen.conteo("futbol-03", con_base_demo=True) == (10, 9)
    f.reiniciar_datos()
    assert almacen.conteo("futbol-03", con_base_demo=True) == base
