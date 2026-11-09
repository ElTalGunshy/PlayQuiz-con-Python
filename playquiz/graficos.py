"""Gráficos de barras con Matplotlib (sin pyplot, para poder incrustarlos en Tkinter y en Flask)."""
import io
import textwrap

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

COLOR_A = "#E8505B"      # coral
COLOR_B = "#2B7DE9"      # azul
COLOR_EMPATE = "#8A8FA3"
COLOR_TEXTO = "#262B40"
COLOR_FONDO = "#FFFFFF"
COLOR_MAYORIA = "#1FA67A"
COLOR_MINORIA = "#F2A33A"
AVISO_DEMO = "DATOS FICTICIOS de demostración: no son votos de niños ni adolescentes reales"


def crear_figura(ancho=8.4, alto=4.4):
    return Figure(figsize=(ancho, alto), dpi=100, facecolor=COLOR_FONDO)


def _voto(n):
    return f"{n} voto" if n == 1 else f"{n} votos"


def _envolver(texto, ancho):
    return "\n".join(textwrap.wrap(texto, ancho)) or texto


def dibujar_resultados(fig, pregunta, opcion_a, opcion_b, votos_a, votos_b,
                       eleccion=None, demo=False, ronda=None, titulo=True):
    """Dibuja dos barras horizontales con escala común.

    - Eje horizontal: cantidad de votos (el mismo para ambas barras).
    - El número de votos va al final de cada barra.
    - La opción ganadora lleva borde grueso y la etiqueta '★ MÁS VOTADA';
      la otra barra se dibuja con su longitud real, sin ocultarla.
    - Si hay empate se indica con un cartel y ambas barras llevan 'EMPATE'.
    - eleccion: 'A' o 'B' marca con ✔ la respuesta del jugador.
    - ronda: (a, b) votos emitidos por la mesa local en esta pregunta; se dibujan como un
      tramo oscuro dentro de cada barra (parte de los votos totales).
    """
    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_facecolor(COLOR_FONDO)

    etiquetas = []
    for letra, texto in (("A", opcion_a), ("B", opcion_b)):
        t = _envolver(texto, 24)
        if eleccion == letra:
            t += "\n✔ Tu elección"
        etiquetas.append(t)

    valores = [votos_a, votos_b]
    colores = [COLOR_A, COLOR_B]
    empate = votos_a == votos_b
    ganadora = None if empate else (0 if votos_a > votos_b else 1)
    maximo = max(valores + [1])

    barras = ax.barh([0, 1], valores, color=colores, height=0.58,
                     edgecolor=COLOR_FONDO, linewidth=0)
    if ganadora is not None:
        barras[ganadora].set_edgecolor(COLOR_TEXTO)
        barras[ganadora].set_linewidth(3)

    if ronda is not None:
        for i, r in enumerate(ronda):
            if r > 0:
                ax.barh(i, min(r, valores[i]), color=(0, 0, 0, 0.32), height=0.58, edgecolor=COLOR_FONDO,
                        hatch="//", linewidth=0, zorder=3)
        ax.text(0.0, 1.02, f"Tramo oscuro = votos de esta mesa  (A: {ronda[0]} · B: {ronda[1]})",
                transform=ax.transAxes, fontsize=10, color="#6B7088", va="bottom")

    for i, v in enumerate(valores):
        texto = _voto(v)
        if empate:
            texto += "\n= EMPATE"
        elif i == ganadora:
            texto += "\n★ MÁS VOTADA"
        ax.text(v + maximo * 0.02, i, texto, va="center", ha="left", fontsize=13,
                fontweight="bold", color=COLOR_TEXTO)

    ax.set_xlim(0, maximo * 1.5)
    ax.set_ylim(1.6, -0.6)                         # A arriba, B abajo
    ax.set_yticks([0, 1])
    ax.set_yticklabels(etiquetas, fontsize=13, color=COLOR_TEXTO)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.tick_params(axis="x", labelsize=11, colors=COLOR_TEXTO)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Cantidad de votos", fontsize=12, color=COLOR_TEXTO)
    ax.grid(axis="x", color="#E3E6F0", linewidth=1)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color("#B8BDD0")

    if empate:
        ax.text(0.98, 0.02, "¡EMPATE!", transform=ax.transAxes, ha="right", va="bottom",
                fontsize=16, fontweight="bold", color=COLOR_TEXTO,
                bbox=dict(boxstyle="round,pad=0.35", fc="#FFE8A3", ec=COLOR_TEXTO))

    if titulo:
        fig.text(0.5, 0.965, _envolver(pregunta, 60), ha="center", va="top",
                 fontsize=16, fontweight="bold", color=COLOR_TEXTO)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.80 if titulo else 0.86,
                        bottom=0.24 if demo else 0.19)
    if demo:
        fig.text(0.5, 0.015, AVISO_DEMO, ha="center", va="bottom", fontsize=10,
                 fontweight="bold", color="#B25E00")
    return fig


def dibujar_esperando(fig, pregunta, opcion_a, opcion_b, demo=False, titulo=True):
    """Marco vacío mientras nadie ha votado: no se adelantan resultados."""
    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_xticks([])
    ax.set_yticks([])
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.set_facecolor("#F7F5FF")
    ax.text(0.5, 0.55, "Esperando el primer voto…", ha="center", va="center", fontsize=18,
            fontweight="bold", color=COLOR_TEXTO, transform=ax.transAxes)
    ax.text(0.5, 0.38, "Las barras crecerán con cada voto", ha="center", va="center", fontsize=12,
            color="#6B7088", transform=ax.transAxes)
    if titulo:
        fig.text(0.5, 0.965, _envolver(pregunta, 60), ha="center", va="top", fontsize=16,
                 fontweight="bold", color=COLOR_TEXTO)
    fig.subplots_adjust(left=0.05, right=0.95, top=0.80 if titulo else 0.95, bottom=0.10)
    return fig


def dibujar_resumen(fig, con_mayoria, con_minoria, empates):
    """Resumen final: cuántas veces coincidió el jugador con la mayoría (conteo de preguntas)."""
    fig.clear()
    ax = fig.add_subplot(111)
    nombres = ["Con la más votada", "Con la menos votada", "Preguntas empatadas"]
    valores = [con_mayoria, con_minoria, empates]
    colores = [COLOR_MAYORIA, COLOR_MINORIA, COLOR_EMPATE]
    ax.barh(range(3), valores, color=colores, height=0.55)
    maximo = max(valores + [1])
    for i, v in enumerate(valores):
        ax.text(v + maximo * 0.03, i, f"{v} " + ("pregunta" if v == 1 else "preguntas"),
                va="center", fontsize=12, fontweight="bold", color=COLOR_TEXTO)
    ax.set_xlim(0, maximo * 1.6)
    ax.set_ylim(2.6, -0.6)
    ax.set_yticks(range(3))
    ax.set_yticklabels(nombres, fontsize=12, color=COLOR_TEXTO)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.set_xlabel("Cantidad de preguntas", fontsize=11, color=COLOR_TEXTO)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color="#E3E6F0")
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    fig.text(0.5, 0.96, "Tus elecciones frente a las de los demás", ha="center", va="top",
             fontsize=14, fontweight="bold", color=COLOR_TEXTO)
    fig.subplots_adjust(left=0.36, right=0.97, top=0.82, bottom=0.18)
    return fig


def figura_a_png(fig):
    """Devuelve los bytes PNG de una figura (usado por el servidor web)."""
    buffer = io.BytesIO()
    FigureCanvasAgg(fig).print_png(buffer)
    return buffer.getvalue()
