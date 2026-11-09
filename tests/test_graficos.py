from playquiz import graficos as g


def _barras(fig):
    return [p.get_width() for p in fig.axes[0].patches]


def test_longitud_de_barras_proporcional_a_los_votos():
    fig = g.crear_figura()
    g.dibujar_resultados(fig, "¿Qué videojuego prefieres?", "Minecraft", "Roblox", 72, 48, "A")
    assert _barras(fig) == [72, 48]
    textos = [t.get_text() for t in fig.axes[0].texts]
    assert any("72 votos" in t and "MÁS VOTADA" in t for t in textos)
    assert any("48 votos" in t for t in textos)
    assert fig.axes[0].get_xlabel() == "Cantidad de votos"


def test_empate_se_indica():
    fig = g.crear_figura()
    g.dibujar_resultados(fig, "P", "A", "B", 5, 5)
    assert any("EMPATE" in t.get_text() for t in fig.axes[0].texts)


def test_se_redibuja_sin_acumular_ejes_y_sin_votos():
    fig = g.crear_figura()
    for a, b in ((0, 0), (1, 0), (10, 30)):
        g.dibujar_resultados(fig, "P", "A", "B", a, b, demo=True)
    assert len(fig.axes) == 1 and _barras(fig) == [10, 30]


def test_png_valido_y_resumen():
    fig = g.crear_figura()
    g.dibujar_resultados(fig, "P", "A", "B", 1, 2)
    assert g.figura_a_png(fig)[:4] == b"\x89PNG"
    fig2 = g.crear_figura(5, 3.5)
    g.dibujar_resumen(fig2, 3, 1, 0)
    assert _barras(fig2) == [3, 1, 0]


def test_ronda_dibuja_tramo_de_la_mesa_y_espera_sin_votos():
    fig = g.crear_figura()
    g.dibujar_resultados(fig, "P", "A", "B", 12, 7, ronda=(2, 1))
    anchos = _barras(fig)
    assert anchos[:2] == [12, 7] and anchos[2:] == [2, 1]
    g.dibujar_esperando(fig, "P", "A", "B")
    assert len(fig.axes) == 1 and _barras(fig) == []
    assert any("Esperando" in t.get_text() for t in fig.axes[0].texts)
