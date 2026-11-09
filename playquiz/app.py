"""PlayQuiz con CustomTkinter: diseño de la primera versión + modos Local, Demostración y Servidor.

Modos:
  * local: X jugadores en la misma pantalla votan por turnos; todo empieza en 0 votos.
  * demo : votos ficticios acumulados, editables y reiniciables (para pruebas).
  * real : votos reales guardados por el servidor Flask (servidor.py).

Notas de robustez:
  * Nunca se destruyen los hijos de un CTkScrollableFrame (son piezas internas de la librería).
  * El botón "Siguiente" se habilita ANTES de cualquier ajuste cosmético, y cualquier error
    en una función de botón se muestra en un cuadro de diálogo y se guarda en data/errores.log.
"""
import textwrap
import tkinter as tk
import traceback
from tkinter import messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from . import config, graficos
from .almacen import Almacen
from .banco import Banco
from .juego import Partida
from .votos import ErrorServidor, FuenteDemo, FuenteLocal, FuenteReal, cargar_jugador_id

# ---- paleta y tipografía de la primera versión ----
FONDO, MORADO, TEXTO, BLANCO = "#F4F1FF", "#6C4DF6", "#262B40", "#FFFFFF"
COLOR_A, COLOR_B = graficos.COLOR_A, graficos.COLOR_B
VERDE, NARANJA, LILA, AZUL, GRIS_OSC, GRIS = "#1FA67A", "#D9822B", "#9B4DCA", "#2B7DE9", "#6B7088", "#9AA0B8"
PALETA = ["#6C4DF6", "#E8505B", "#2B7DE9", "#1FA67A", "#D9822B", "#9B4DCA"]
COLORES_JUGADOR = PALETA
FUENTE = "Segoe UI"
PASOS_ANIMACION, MS_PASO = 8, 28
DESCRIPCION_MODO = {
    "local": "👥 Local: varios jugadores en esta pantalla. Los votos empiezan en 0.",
    "demo": "🧪 Demostración: votos ficticios acumulados que puedes editar o reiniciar.",
    "real": "🌐 Votación real: votos de varios dispositivos guardados en el servidor.",
}


def fuente(tam=14, negrita=False):
    return ctk.CTkFont(family=FUENTE, size=tam, weight="bold" if negrita else "normal")


def boton(padre, texto, comando, color=MORADO, tam=13, height=42, **kw):
    return ctk.CTkButton(padre, text=texto, command=comando, fg_color=color, hover_color=color,
                         text_color=BLANCO, font=fuente(tam, True), corner_radius=14, height=height, **kw)


def etiqueta(padre, texto, tam=14, negrita=False, color=TEXTO, **kw):
    return ctk.CTkLabel(padre, text=texto, font=fuente(tam, negrita), text_color=color, **kw)


def color_jugador(i):
    return COLORES_JUGADOR[i % len(COLORES_JUGADOR)]


class PlayQuizApp(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("PlayQuiz 🎯 - ¿Qué prefieres?")
        self.geometry("1100x760")
        self.minsize(980, 700)
        self.configure(fg_color=FONDO)
        self.report_callback_exception = self._error_en_callback
        self.banco = Banco()
        self.almacen = Almacen(config.LOCAL_DB)
        self.jugador_id = cargar_jugador_id()
        self.modo = tk.StringVar(value="local")
        self.url = tk.StringVar(value=config.URL_SERVIDOR)
        self.n_preguntas = 10
        self.n_jugadores = 2
        self.vars_nombres = []
        self._filas_nombres = []
        self.nombres = []
        self.categoria = None
        self.fuente = None
        self.partida = None
        self.notas = ""
        self._pendientes = []
        self._anim_id = None
        self._mostrado = (0, 0)
        self.fig = self.canvas = None
        self.contenedor = ctk.CTkFrame(self, fg_color=FONDO, corner_radius=0)
        self.contenedor.pack(fill="both", expand=True)
        self.mostrar_bienvenida()

    # ------------------------------------------------------------------ utilidades
    def _error_en_callback(self, exc, val, tb):
        texto = "".join(traceback.format_exception(exc, val, tb))
        try:
            config.DATA.mkdir(exist_ok=True)
            with open(config.DATA / "errores.log", "a", encoding="utf-8") as f:
                f.write(texto + "\n")
        except OSError:
            pass
        messagebox.showerror("Error en PlayQuiz", f"{val}\n\n(Detalle guardado en data/errores.log)")

    def _cancelar(self):
        for ident in self._pendientes + [self._anim_id]:
            if ident is not None:
                try:
                    self.after_cancel(ident)
                except Exception:  # noqa: BLE001
                    pass
        self._pendientes, self._anim_id = [], None

    def limpiar(self):
        self._cancelar()
        for w in self.contenedor.winfo_children():
            w.destroy()
        self.fig = self.canvas = None
        self._filas_nombres = []

    def barra_superior(self, texto):
        b = ctk.CTkFrame(self.contenedor, fg_color=MORADO, corner_radius=0)
        b.pack(fill="x")
        etiqueta(b, texto, 20, True, BLANCO).pack(pady=10)

    def _var_nombre(self, i):
        while len(self.vars_nombres) <= i:
            self.vars_nombres.append(tk.StringVar(value=f"Jugador {len(self.vars_nombres) + 1}"))
        return self.vars_nombres[i]

    def _nombres_validos(self):
        """Vacíos -> 'Jugador N'; repetidos -> 'Ana (2)'."""
        vistos, nombres = {}, []
        for i in range(self.n_jugadores):
            n = self._var_nombre(i).get().strip()[:18] or f"Jugador {i + 1}"
            vistos[n] = vistos.get(n, 0) + 1
            nombres.append(n if vistos[n] == 1 else f"{n} ({vistos[n]})")
        return nombres

    # ------------------------------------------------------------------ 1. bienvenida
    def mostrar_bienvenida(self):
        self.limpiar()
        c = self.contenedor
        self.barra_superior("🎯 PlayQuiz")
        etiqueta(c, "¿Qué prefieres?", 36, True).pack(pady=(14, 0))
        etiqueta(c, "Elige una opción y descubre cuál fue la más votada.", 15).pack()

        tarjetas = ctk.CTkFrame(c, fg_color=FONDO)
        tarjetas.pack(pady=12)
        izq = ctk.CTkFrame(tarjetas, fg_color=BLANCO, corner_radius=18)
        izq.grid(row=0, column=0, padx=10, sticky="n")
        etiqueta(izq, "Modo de juego", 15, True).pack(anchor="w", padx=22, pady=(18, 4))
        for valor, txt in (("local", "Local (jugadores en esta pantalla)"), ("demo", "Demostración (votos ficticios)"),
                           ("real", "Votación real (servidor)")):
            ctk.CTkRadioButton(izq, text=txt, variable=self.modo, value=valor, font=fuente(13), text_color=TEXTO,
                               command=self._actualizar_modo).pack(anchor="w", padx=22, pady=3)
        self.lbl_modo = etiqueta(izq, "", 11, color=GRIS_OSC, wraplength=330, justify="left")
        self.lbl_modo.pack(anchor="w", padx=22, pady=(4, 2))
        self.entrada_url = ctk.CTkEntry(izq, textvariable=self.url, width=320, font=fuente(12))
        self.entrada_url.pack(padx=22, pady=(6, 2))
        fila = ctk.CTkFrame(izq, fg_color=BLANCO)
        fila.pack(anchor="w", padx=22, pady=4)
        self.btn_probar = ctk.CTkButton(fila, text="Probar conexión", command=self._probar, font=fuente(12),
                                        fg_color=AZUL, hover_color=AZUL, width=140)
        self.btn_probar.pack(side="left", padx=(0, 6))
        self.btn_reset_demo = ctk.CTkButton(fila, text="🗑 Reiniciar datos demo", command=self._reiniciar_demo,
                                            font=fuente(12), fg_color=LILA, hover_color=LILA, width=170)
        self.btn_reset_demo.pack(side="left")
        etiqueta(izq, "Preguntas por partida", 15, True).pack(anchor="w", padx=22, pady=(12, 4))
        self.sel_preguntas = ctk.CTkSegmentedButton(
            izq, values=[str(n) for n in config.PREGUNTAS_POR_PARTIDA],
            command=lambda v: setattr(self, "n_preguntas", int(v)))
        self.sel_preguntas.set(str(self.n_preguntas))
        self.sel_preguntas.pack(padx=22, pady=(0, 18))

        der = ctk.CTkFrame(tarjetas, fg_color=BLANCO, corner_radius=18)
        der.grid(row=0, column=1, padx=10, sticky="n")
        etiqueta(der, "👥 Número de jugadores", 15, True).pack(anchor="w", padx=22, pady=(18, 4))
        selector = ctk.CTkFrame(der, fg_color=BLANCO)
        selector.pack(padx=22, pady=(0, 4))
        ctk.CTkButton(selector, text="−", width=44, height=40, font=fuente(20, True), fg_color=MORADO,
                      hover_color=MORADO, command=lambda: self._fijar_jugadores(self.n_jugadores - 1)).pack(side="left", padx=4)
        self.var_cantidad = tk.StringVar(value=str(self.n_jugadores))
        entrada = ctk.CTkEntry(selector, textvariable=self.var_cantidad, width=70, height=40,
                               font=fuente(18, True), justify="center")
        entrada.pack(side="left", padx=4)
        entrada.bind("<Return>", lambda e: self._fijar_jugadores(self.var_cantidad.get()))
        entrada.bind("<FocusOut>", lambda e: self._fijar_jugadores(self.var_cantidad.get()))
        ctk.CTkButton(selector, text="+", width=44, height=40, font=fuente(20, True), fg_color=MORADO,
                      hover_color=MORADO, command=lambda: self._fijar_jugadores(self.n_jugadores + 1)).pack(side="left", padx=4)
        etiqueta(der, f"(de 1 a {config.MAX_JUGADORES} jugadores)", 11, color=GRIS_OSC).pack()
        self.zona_nombres = ctk.CTkScrollableFrame(der, fg_color=BLANCO, width=300, height=200)
        self.zona_nombres.pack(padx=18, pady=(6, 18), fill="x")
        self._dibujar_nombres()
        self._actualizar_modo()
        boton(c, "¡Jugar! ▶", self.mostrar_menu, VERDE, 22, height=56, width=260).pack(pady=8)
        etiqueta(c, f"{len(self.banco.df)} preguntas · {len(self.banco.categorias)} temáticas", 11,
                 color=GRIS_OSC).pack(pady=4)

    def _actualizar_modo(self):
        modo = self.modo.get()
        self.lbl_modo.configure(text=DESCRIPCION_MODO[modo])
        self.entrada_url.configure(state="normal" if modo == "real" else "disabled")
        self.btn_probar.configure(state="normal" if modo == "real" else "disabled")
        self.btn_reset_demo.configure(state="normal" if modo == "demo" else "disabled")

    def _fijar_jugadores(self, valor):
        try:
            n = int(str(valor).strip())
        except ValueError:
            n = self.n_jugadores
        self.n_jugadores = max(1, min(config.MAX_JUGADORES, n))
        self.var_cantidad.set(str(self.n_jugadores))
        self._dibujar_nombres()

    def _dibujar_nombres(self):
        # Se destruyen solo las filas propias; nunca los hijos internos del CTkScrollableFrame.
        for f in self._filas_nombres:
            f.destroy()
        self._filas_nombres = []
        for i in range(self.n_jugadores):
            fila = ctk.CTkFrame(self.zona_nombres, fg_color=BLANCO)
            fila.pack(fill="x", pady=2)
            ctk.CTkLabel(fila, text="●", text_color=color_jugador(i), font=fuente(18), width=24).pack(side="left")
            ctk.CTkEntry(fila, textvariable=self._var_nombre(i), width=210, font=fuente(13),
                         placeholder_text=f"Jugador {i + 1}").pack(side="left", padx=4)
            self._filas_nombres.append(fila)

    def _crear_fuente_real(self):
        f = FuenteReal(self.url.get(), self.jugador_id)
        f.probar()
        return f

    def _probar(self):
        try:
            self._crear_fuente_real()
            messagebox.showinfo("Conexión", "¡Conexión correcta con el servidor!")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Conexión", str(e))

    def _reiniciar_demo(self):
        if messagebox.askyesno("Reiniciar datos demo",
                               "Se borrarán los votos ficticios editados y acumulados de la demostración.\n¿Continuar?"):
            FuenteDemo(self.almacen).reiniciar_datos()
            messagebox.showinfo("Demostración", "Datos de demostración reiniciados.")

    # ------------------------------------------------------------------ 2. menú de temáticas
    def _nueva_fuente(self):
        """Crea la fuente de votos según el modo. Devuelve False si el servidor no responde."""
        modo = self.modo.get()
        if modo == "real":
            try:
                self.fuente = self._crear_fuente_real()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("Servidor", str(e))
                return False
        elif modo == "demo":
            self.fuente = FuenteDemo(self.almacen)
        else:
            self.fuente = FuenteLocal()
        return True

    def mostrar_menu(self):
        if not self._nueva_fuente():
            return
        self.nombres = self._nombres_validos()
        self.limpiar()
        c = self.contenedor
        self.barra_superior("Elige una temática")
        fila = ctk.CTkFrame(c, fg_color=FONDO)
        fila.pack(fill="x", padx=20, pady=10)
        boton(fila, "🎲 Todas las temáticas (aleatorio)", lambda: self.iniciar(None), VERDE, 14).pack(side="left")
        boton(fila, "⬅ Inicio", self.mostrar_bienvenida, GRIS_OSC, 12, width=110).pack(side="right")
        juegan = ("Juegan: " + ", ".join(self.nombres)) if len(self.nombres) <= 5 else f"Juegan {len(self.nombres)} jugadores"
        etiqueta(fila, juegan, 12, color=GRIS_OSC).pack(side="right", padx=14)
        zona = ctk.CTkScrollableFrame(c, fg_color=FONDO)
        zona.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        columnas = 4
        for k in range(columnas):
            zona.columnconfigure(k, weight=1, uniform="cat")
        for i, cat in enumerate(self.banco.categorias):
            color = PALETA[i % len(PALETA)]
            ctk.CTkButton(zona, text="\n".join(textwrap.wrap(f"{cat['emoji']}  {cat['nombre']}", 22)),
                          fg_color=color, hover_color=color, text_color=BLANCO, font=fuente(12, True),
                          corner_radius=14, height=64, command=lambda cid=cat["id"]: self.iniciar(cid)
                          ).grid(row=i // columnas, column=i % columnas, padx=6, pady=6, sticky="nsew")

    # ------------------------------------------------------------------ 3. partida
    def iniciar(self, categoria):
        self.categoria = categoria
        self.reiniciar_partida(nueva_fuente=False)      # el menú ya creó la fuente de votos

    def reiniciar_partida(self, nueva_fuente=True):
        """Nueva partida con las mismas opciones. En modo local vuelve a 0 votos."""
        if nueva_fuente and not self._nueva_fuente():
            return
        preguntas = self.banco.aleatorias(self.n_preguntas, self.categoria)
        self.partida = Partida(preguntas, self.categoria, self.nombres or self._nombres_validos())
        self.mostrar_pregunta()

    def mostrar_pregunta(self):
        self.limpiar()
        c, p = self.contenedor, self.partida
        q = p.actual
        cat = self.banco.categoria(q["categoria"])
        self.notas = ""
        self._mostrado = (0, 0)
        self.barra_superior(f"{cat['emoji']} {cat['nombre']}")

        fila = ctk.CTkFrame(c, fg_color=FONDO)
        fila.pack(fill="x", padx=30, pady=(8, 0))
        etiqueta(fila, f"Pregunta {p.numero} de {p.total}", 12, True).pack(side="left")
        if self.fuente.es_demo:
            etiqueta(fila, " MODO DEMOSTRACIÓN · datos ficticios ", 10, True, "#7A4300", fg_color="#FFE8A3",
                     corner_radius=8).pack(side="right")
        elif self.fuente.es_local:
            etiqueta(fila, " MODO LOCAL · solo votos de esta mesa ", 10, True, "#0B5B42", fg_color="#CFF3E5",
                     corner_radius=8).pack(side="right")
        self.barra = ctk.CTkProgressBar(c, progress_color=MORADO, fg_color="#DAD4F5", height=10)
        self.barra.pack(fill="x", padx=30, pady=6)
        self.barra.set(p.indice / p.total)

        tarjeta = ctk.CTkFrame(c, fg_color=BLANCO, corner_radius=18)
        tarjeta.pack(fill="x", padx=60, pady=(2, 6))
        etiqueta(tarjeta, q["pregunta"], 26, True, wraplength=900).pack(padx=24, pady=14)

        self.lbl_turno = etiqueta(c, "", 16, True, BLANCO, corner_radius=12, height=36)
        self.lbl_turno.pack(fill="x", padx=60, pady=(0, 6))

        botones = ctk.CTkFrame(c, fg_color=FONDO)
        botones.pack(fill="x", padx=60)
        botones.columnconfigure((0, 1), weight=1, uniform="op")
        self.btn_a = ctk.CTkButton(botones, text="\n".join(["A", *textwrap.wrap(q["opcion_a"], 30)]),
                                   fg_color=COLOR_A, hover_color="#C93B47", text_color=BLANCO,
                                   font=fuente(20, True), corner_radius=18, height=96,
                                   command=lambda: self.votar("A"))
        self.btn_a.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.btn_b = ctk.CTkButton(botones, text="\n".join(["B", *textwrap.wrap(q["opcion_b"], 30)]),
                                   fg_color=COLOR_B, hover_color="#1F65C0", text_color=BLANCO,
                                   font=fuente(20, True), corner_radius=18, height=96,
                                   command=lambda: self.votar("B"))
        self.btn_b.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.lbl_estado = etiqueta(c, "", 12, False, TEXTO, wraplength=980)
        self.lbl_estado.pack(pady=(6, 0))

        marco = ctk.CTkFrame(c, fg_color=BLANCO, corner_radius=16)
        marco.pack(fill="both", expand=True, padx=60, pady=6)
        self.fig = graficos.crear_figura(9.0, 3.3)
        self.canvas = FigureCanvasTkAgg(self.fig, master=marco)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        pie = ctk.CTkFrame(c, fg_color=FONDO)
        pie.pack(pady=(0, 10))
        boton(pie, "🏠 Inicio", self.mostrar_bienvenida, GRIS_OSC, 12, width=110).pack(side="left", padx=4)
        boton(pie, "📂 Temáticas", self.mostrar_menu, GRIS_OSC, 12, width=130).pack(side="left", padx=4)
        boton(pie, "🔄 Reiniciar", self.reiniciar_partida, NARANJA, 12, width=120).pack(side="left", padx=4)
        if self.fuente.es_demo:
            boton(pie, "✏️ Editar votos demo", self.editar_demo, LILA, 12, width=170).pack(side="left", padx=4)
            boton(pie, "🗑 Reiniciar datos demo", self.reiniciar_datos_demo, LILA, 12, width=190).pack(side="left", padx=4)
        elif not self.fuente.es_local:
            boton(pie, "↻ Actualizar", self.refrescar, AZUL, 12, width=120).pack(side="left", padx=4)
        self.btn_sig = boton(pie, "Siguiente ▶", self.siguiente, GRIS, 15, width=170, state="disabled")
        self.btn_sig.pack(side="left", padx=8)

        self._actualizar_turno()
        self._dibujar_grafico(None)
        if not (self.fuente.es_demo or self.fuente.es_local):
            self._pendientes.append(self.after(5000, self._auto))

    # ------------------------------------------------------------------ votación por turnos
    def votar(self, letra):
        p = self.partida
        if p is None or p.terminada or p.ronda.completa:
            return
        q, jugador = p.actual, p.turno
        try:
            res = self.fuente.votar(q["id"], letra, self.fuente.id_jugador(jugador))
        except ErrorServidor as e:
            messagebox.showerror("Servidor", str(e))
            return
        opcion = res.tu_opcion or letra
        antes = self._mostrado
        if p.ronda.votos or antes != (0, 0):
            desde = antes
        else:      # primer voto: las barras crecen desde lo que había (0 en modo local)
            desde = (res.votos_a - int(opcion == "A" and not res.duplicado),
                     res.votos_b - int(opcion == "B" and not res.duplicado))
        p.votar(opcion, res.votos_a, res.votos_b)
        self.notas = (f"{p.jugadores[jugador]} ya había votado esta pregunta: su voto no se cuenta dos veces."
                      if res.duplicado else "")
        self._actualizar_turno()                 # habilita "Siguiente" si ya votaron todos
        self._animar(desde, (res.votos_a, res.votos_b))

    def _actualizar_turno(self):
        """Estado de botones y textos. Lo esencial (Siguiente / A / B) va primero y sin adornos."""
        p = self.partida
        r = p.ronda
        turno = r.turno
        completa = turno is None
        ultima = p.indice == p.total - 1
        # --- lo esencial ---
        self.btn_sig.configure(text="Ver resumen 🏁" if ultima else "Siguiente ▶",
                               state="normal" if completa else "disabled",
                               fg_color=VERDE if completa else GRIS,
                               hover_color=VERDE if completa else GRIS)
        self.btn_a.configure(state="disabled" if completa else "normal", fg_color=GRIS if completa else COLOR_A)
        self.btn_b.configure(state="disabled" if completa else "normal", fg_color=GRIS if completa else COLOR_B)
        # --- cosmético ---
        if completa:
            self.lbl_turno.configure(text="✔ ¡Todos votaron! Pulsa «Siguiente»", fg_color=VERDE)
        else:
            self.lbl_turno.configure(text=f"Turno de {p.jugadores[turno]}  ({len(r.votos) + 1} de {p.n_jugadores})",
                                     fg_color=color_jugador(turno))
        if p.n_jugadores <= 8:
            partes = []
            for i in r.orden:
                marca = "✅" if i in r.votos else ("▶" if i == turno else "⏳")
                partes.append(f"{marca} {p.jugadores[i]}")
            estado = "   ".join(partes)
        else:
            estado = f"Han votado {len(r.votos)} de {p.n_jugadores} jugadores"
        self.lbl_estado.configure(text=estado + (f"\n{self.notas}" if self.notas else ""))
        self.barra.set((p.indice + (1 if completa else 0)) / p.total)

    # ------------------------------------------------------------------ gráfico en vivo
    def _dibujar_grafico(self, valores):
        """valores=(a, b) a mostrar; None = redibujar el estado actual (o 'esperando' si nadie votó)."""
        r = self.partida.ronda
        q = r.pregunta
        if valores is None and not r.votos:
            graficos.dibujar_esperando(self.fig, q["pregunta"], q["opcion_a"], q["opcion_b"],
                                       self.fuente.es_demo, titulo=False)
        else:
            a, b = valores if valores is not None else (r.votos_a, r.votos_b)
            graficos.dibujar_resultados(self.fig, q["pregunta"], q["opcion_a"], q["opcion_b"], a, b, None,
                                        self.fuente.es_demo, ronda=None if self.fuente.es_local else r.votos_mesa,
                                        titulo=False)
            self._mostrado = (a, b)
        self.canvas.draw_idle()

    def _animar(self, desde, hasta, paso=1):
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:  # noqa: BLE001
                pass
            self._anim_id = None
        if self.canvas is None:
            return
        if paso >= PASOS_ANIMACION or desde == hasta:
            self._dibujar_grafico(hasta)
            return
        t = paso / PASOS_ANIMACION
        self._dibujar_grafico((round(desde[0] + (hasta[0] - desde[0]) * t),
                               round(desde[1] + (hasta[1] - desde[1]) * t)))
        self._anim_id = self.after(MS_PASO, lambda: self._animar(desde, hasta, paso + 1))

    # ------------------------------------------------------------------ administración
    def refrescar(self):
        p = self.partida
        if p is None or p.terminada or self.canvas is None:
            return
        try:
            res = self.fuente.resultados(p.actual["id"], self.fuente.id_jugador(0))
        except ErrorServidor as e:
            self.lbl_estado.configure(text=str(e))
            return
        if p.ronda.votos:
            p.actualizar_totales(res.votos_a, res.votos_b)
            self._animar(self._mostrado, (res.votos_a, res.votos_b))

    def _auto(self):
        self.refrescar()
        if self.canvas is not None:
            self._pendientes.append(self.after(5000, self._auto))

    def _pedir_entero(self, texto, inicial):
        valor = ctk.CTkInputDialog(text=f"{texto}\n(actual: {inicial})", title="Editar votos demo").get_input()
        if valor is None:
            return None
        try:
            n = int(valor.strip())
        except ValueError:
            messagebox.showerror("Editar votos demo", "Escribe un número entero.")
            return None
        if not 0 <= n <= 100000:
            messagebox.showerror("Editar votos demo", "El número debe estar entre 0 y 100000.")
            return None
        return n

    def editar_demo(self):
        p = self.partida
        q = p.actual
        a0, b0 = self.fuente.almacen.base_demo(q["id"])
        a = self._pedir_entero(f"Votos FICTICIOS para «{q['opcion_a']}»:", a0)
        if a is None:
            return
        b = self._pedir_entero(f"Votos FICTICIOS para «{q['opcion_b']}»:", b0)
        if b is None:
            return
        self.fuente.editar_base(q["id"], a, b)
        self._recargar_demo()

    def reiniciar_datos_demo(self):
        if not messagebox.askyesno("Reiniciar datos demo",
                                   "Se borrarán los votos ficticios editados y acumulados.\n"
                                   "Las preguntas ya votadas de esta partida se mantienen.\n¿Continuar?"):
            return
        self.fuente.reiniciar_datos()
        self._recargar_demo()

    def _recargar_demo(self):
        p = self.partida
        if p.ronda.votos:
            res = self.fuente.resultados(p.actual["id"], self.fuente.id_jugador(0))
            p.actualizar_totales(res.votos_a, res.votos_b)
            self._animar(self._mostrado, (res.votos_a, res.votos_b))

    # ------------------------------------------------------------------ avanzar
    def siguiente(self):
        p = self.partida
        if p is None or p.terminada or not p.ronda.completa:
            return
        if p.avanzar():
            self.mostrar_pregunta()
        else:
            self.mostrar_final()

    # ------------------------------------------------------------------ 5. resumen final
    def mostrar_final(self):
        self.limpiar()
        c, p = self.contenedor, self.partida
        por_jugador = p.resumen_por_jugador()
        total = p.resumen()
        for j, f in enumerate(por_jugador):
            self.almacen.registrar_partida(self.fuente.id_jugador(j), self.fuente.modo, self.categoria,
                                           p.total, f["mayoria"], f["minoria"], f["empate"])
        self.barra_superior("🏁 ¡Partida terminada!")
        cuerpo = ctk.CTkFrame(c, fg_color=FONDO)
        cuerpo.pack(fill="both", expand=True, padx=20, pady=10)
        izq = ctk.CTkFrame(cuerpo, fg_color=BLANCO, corner_radius=16)
        izq.pack(side="left", fill="y", padx=(0, 8))
        fig = graficos.crear_figura(5.2, 3.6)
        graficos.dibujar_resumen(fig, total["mayoria"], total["minoria"], total["empate"])
        FigureCanvasTkAgg(fig, master=izq).get_tk_widget().pack(padx=6, pady=6)
        der = ctk.CTkScrollableFrame(cuerpo, fg_color=BLANCO, corner_radius=16)
        der.pack(side="left", fill="both", expand=True, padx=(8, 0))
        etiqueta(der, "Por jugador", 15, True).pack(anchor="w", padx=8, pady=(4, 2))
        for j, f in enumerate(por_jugador):
            etiqueta(der, f"●  {f['jugador']}:  {f['mayoria']} con la más votada · {f['minoria']} con la "
                          f"menos votada · {f['empate']} empates", 12, color=color_jugador(j),
                     anchor="w", wraplength=520, justify="left").pack(fill="x", padx=8, pady=1)
        etiqueta(der, "Por pregunta", 15, True).pack(anchor="w", padx=8, pady=(12, 2))
        for r in p.rondas:
            q = r.pregunta
            mesa = ", ".join(f"{p.jugadores[i]}→{r.votos[i]}" for i in sorted(r.votos))
            etiqueta(der, f"• {q['pregunta']}\n   A «{q['opcion_a']}»: {r.votos_a} votos · "
                          f"B «{q['opcion_b']}»: {r.votos_b} votos\n   Mesa: {mesa}", 11, anchor="w",
                     wraplength=520, justify="left").pack(fill="x", padx=8, pady=3)
        if self.fuente.es_demo:
            etiqueta(c, "Modo demostración: los votos son ficticios.", 12, True, "#7A4300").pack()
        fila = ctk.CTkFrame(c, fg_color=FONDO)
        fila.pack(pady=12)
        boton(fila, "🔄 Jugar otra vez", self.reiniciar_partida, VERDE, 14).pack(side="left", padx=6)
        boton(fila, "📂 Temáticas", self.mostrar_menu, GRIS_OSC, 14, width=140).pack(side="left", padx=6)
        boton(fila, "🏠 Inicio", self.mostrar_bienvenida, GRIS_OSC, 14, width=120).pack(side="left", padx=6)


def main():
    config.DATA.mkdir(exist_ok=True)
    PlayQuizApp().mainloop()
