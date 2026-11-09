"""Recorre la interfaz completa. Si CustomTkinter real no está instalado usa un doble simulado
que además recuerda la configuración de cada widget, para comprobar botones habilitados/deshabilitados."""
import sys
import types

import pytest


def _instalar_doble_tk():
    class Var:
        def __init__(self, master=None, value=None, **k):
            self.v = value
        def get(self):
            return self.v
        def set(self, v):
            self.v = v

    class W:
        def __init__(self, *a, **k):
            self.cfg = dict(k)
        def configure(self, **k):
            self.cfg.update(k)
        def get_tk_widget(self):
            return W()
        def winfo_children(self):
            return []
        def after(self, ms, f=None):
            return "id"
        def __getattr__(self, nombre):
            if nombre.startswith("__") or nombre == "cfg":
                raise AttributeError(nombre)
            return lambda *a, **k: None

    tk = types.ModuleType("tkinter")
    tk.StringVar = Var
    mb = types.ModuleType("tkinter.messagebox")
    mb.showerror = mb.showinfo = lambda *a, **k: None
    mb.askyesno = lambda *a, **k: True
    tk.messagebox = mb
    ctk = types.ModuleType("customtkinter")
    for nombre in ("CTk", "CTkFrame", "CTkLabel", "CTkButton", "CTkProgressBar", "CTkSegmentedButton",
                   "CTkEntry", "CTkRadioButton", "CTkScrollableFrame", "CTkFont"):
        setattr(ctk, nombre, W)
    ctk.set_appearance_mode = ctk.set_default_color_theme = lambda *a, **k: None

    class Dialogo(W):
        def get_input(self):
            return "5"
    ctk.CTkInputDialog = Dialogo
    bk = types.ModuleType("matplotlib.backends.backend_tkagg")
    bk.FigureCanvasTkAgg = lambda fig, master=None: W()
    sys.modules.update({"tkinter": tk, "tkinter.messagebox": mb, "customtkinter": ctk,
                        "matplotlib.backends.backend_tkagg": bk})


def _preparar():
    try:
        import customtkinter
    except ImportError:
        _instalar_doble_tk()
        return
    if getattr(customtkinter, "__file__", None):      # los dobles no tienen __file__
        pytest.skip("Hay CustomTkinter real: prueba la interfaz abriendo main.py")


def _app(tmp_path, monkeypatch, modo):
    _preparar()
    from playquiz import app, config
    monkeypatch.setattr(config, "LOCAL_DB", tmp_path / "l.db")
    monkeypatch.setattr(config, "JUGADOR", tmp_path / "j.json")
    a = app.PlayQuizApp()
    a.modo.set(modo)
    a.n_preguntas = 5
    return a


def test_modo_local_empieza_en_cero_y_el_grafico_acumula_voto_a_voto(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "local")
    a.mostrar_bienvenida()
    a._fijar_jugadores("3")
    a._var_nombre(0).set("Ana")
    a._var_nombre(1).set("Ana")                  # repetido -> "Ana (2)"
    a._var_nombre(2).set("   ")                  # vacío -> "Jugador 3"
    a.mostrar_menu()
    assert a.nombres == ["Ana", "Ana (2)", "Jugador 3"] and a.fuente.modo == "local"
    a.iniciar("minecraft")
    r = a.partida.ronda
    assert (r.votos_a, r.votos_b) == (0, 0)      # sin votos simulados
    assert a.btn_sig.cfg["state"] == "disabled"
    vistos = []
    for letra in ("A", "B", "A"):
        a.votar(letra)
        vistos.append((r.votos_a, r.votos_b))
        a.siguiente() if not r.completa else None
        assert a.partida.indice == 0 or r.completa
    assert vistos == [(1, 0), (1, 1), (2, 1)]    # el acumulado sube con cada voto
    assert r.completa and a.btn_sig.cfg["state"] == "normal"
    a.votar("A")                                 # ya votaron todos: se ignora
    assert (r.votos_a, r.votos_b) == (2, 1)
    a.siguiente()
    assert a.partida.indice == 1


def test_flujo_completo_hasta_el_resumen(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "local")
    a._fijar_jugadores(2)
    a.mostrar_menu()
    a.iniciar(None)
    for _ in range(5):
        assert a.btn_sig.cfg["state"] == "disabled"      # bloqueado mientras falte alguien
        a.votar("A")
        assert a.btn_sig.cfg["state"] == "disabled"
        a.votar("B")
        assert a.btn_sig.cfg["state"] == "normal"        # se habilita al terminar la votación
        a.siguiente()
    assert a.partida.terminada
    hist = a.almacen.historial()
    assert len(hist) == 2 and set(hist["modo"]) == {"local"}     # una fila por jugador


def test_navegar_a_mitad_de_partida_y_volver_a_jugar(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "local")
    a._fijar_jugadores(2)
    a.mostrar_menu()
    a.iniciar("futbol")
    a.votar("A")
    a.mostrar_bienvenida()                               # botón Inicio
    a.mostrar_menu()                                     # botón Temáticas
    a.iniciar("futbol")
    assert a.partida.indice == 0 and (a.partida.ronda.votos_a, a.partida.ronda.votos_b) == (0, 0)
    for _ in range(5):
        a.votar("A")
        a.votar("A")
        a.siguiente()
    assert a.partida.terminada


def test_reiniciar_en_local_vuelve_a_cero(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "local")
    a._fijar_jugadores(2)
    a.mostrar_menu()
    a.iniciar("futbol")
    a.votar("A")
    a.votar("A")
    assert a.partida.ronda.votos_a == 2
    a.reiniciar_partida()
    assert (a.partida.ronda.votos_a, a.partida.ronda.votos_b) == (0, 0) and a.partida.indice == 0
    assert a.partida.n_jugadores == 2


def test_modo_demo_votos_ficticios_editables_y_reiniciables(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "demo")
    a._fijar_jugadores(1)
    a.mostrar_menu()
    a.iniciar("videojuegos")
    pid = a.partida.actual["id"]
    base = a.almacen.base_demo(pid)
    a.votar("A")
    r = a.partida.ronda
    assert (r.votos_a, r.votos_b) == (base[0] + 1, base[1]) and r.completa
    assert a.btn_sig.cfg["state"] == "normal"
    a.editar_demo()                              # el diálogo simulado devuelve 5 y 5
    assert a.almacen.base_demo(pid) == (5, 5) and (r.votos_a, r.votos_b) == (6, 5)
    a.reiniciar_datos_demo()
    assert a.almacen.base_demo(pid) == base and (r.votos_a, r.votos_b) == (base[0], base[1])
    a.siguiente()
    assert a.partida.indice == 1


def test_cantidad_de_jugadores_ajustable_hasta_el_maximo(tmp_path, monkeypatch):
    a = _app(tmp_path, monkeypatch, "local")
    from playquiz import config
    a.mostrar_bienvenida()
    a._fijar_jugadores("0")
    assert a.n_jugadores == 1
    a._fijar_jugadores("abc")
    assert a.n_jugadores == 1
    a._fijar_jugadores(10 ** 6)
    assert a.n_jugadores == config.MAX_JUGADORES
    a._fijar_jugadores(15)
    a.mostrar_menu()
    a.iniciar(None)
    for _ in range(15):
        a.votar("A")
    assert a.partida.ronda.completa and a.partida.ronda.votos_mesa == (15, 0)
    assert a.btn_sig.cfg["state"] == "normal"
