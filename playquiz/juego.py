"""Lógica de una partida local con varios jugadores (sin interfaz).

Cada pregunta es una *ronda*: todos los jugadores de la mesa votan por turnos y,
al terminar, se puede avanzar. El orden de turnos rota en cada pregunta.
"""
from dataclasses import dataclass, field

from . import config


def veredicto_de(opcion, votos_a, votos_b):
    """'mayoria', 'minoria' o 'empate' para quien eligió `opcion` ('A' o 'B')."""
    propios, otros = (votos_a, votos_b) if opcion == "A" else (votos_b, votos_a)
    if propios == otros:
        return "empate"
    return "mayoria" if propios > otros else "minoria"


@dataclass
class Ronda:
    pregunta: dict
    orden: list                                  # índices de jugador en el orden de turnos
    votos: dict = field(default_factory=dict)    # índice de jugador -> 'A' / 'B'
    votos_a: int = 0                             # totales acumulados (incluye otras fuentes)
    votos_b: int = 0

    @property
    def turno(self):
        """Índice del jugador al que le toca votar, o None si ya votaron todos."""
        for i in self.orden:
            if i not in self.votos:
                return i
        return None

    @property
    def completa(self):
        return self.turno is None

    @property
    def votos_mesa(self):
        """(votos A, votos B) emitidos solo por los jugadores de esta mesa en la ronda."""
        a = sum(1 for o in self.votos.values() if o == "A")
        return a, len(self.votos) - a

    def veredicto(self, jugador):
        return veredicto_de(self.votos[jugador], self.votos_a, self.votos_b)


class Partida:
    def __init__(self, preguntas, categoria=None, jugadores=("Jugador 1",)):
        if not preguntas:
            raise ValueError("Una partida necesita al menos una pregunta.")
        jugadores = list(jugadores)
        if not 1 <= len(jugadores) <= config.MAX_JUGADORES:
            raise ValueError(f"Debe haber entre 1 y {config.MAX_JUGADORES} jugadores.")
        self.jugadores = jugadores
        self.categoria = categoria
        self.indice = 0
        n = len(jugadores)
        self.rondas = [Ronda(q, [(k + r) % n for k in range(n)]) for r, q in enumerate(preguntas)]

    # ---------- estado ----------
    @property
    def n_jugadores(self):
        return len(self.jugadores)

    @property
    def total(self):
        return len(self.rondas)

    @property
    def terminada(self):
        return self.indice >= self.total

    @property
    def ronda(self):
        return None if self.terminada else self.rondas[self.indice]

    @property
    def actual(self):
        return None if self.terminada else self.rondas[self.indice].pregunta

    @property
    def numero(self):
        return min(self.indice + 1, self.total)

    @property
    def turno(self):
        return None if self.terminada else self.ronda.turno

    # ---------- acciones ----------
    def votar(self, opcion, votos_a, votos_b):
        """Registra el voto del jugador en turno con los totales acumulados resultantes.
        Devuelve el índice del jugador que votó."""
        if self.terminada:
            raise RuntimeError("La partida ya terminó.")
        if opcion not in ("A", "B"):
            raise ValueError("Opción inválida.")
        jugador = self.ronda.turno
        if jugador is None:
            raise RuntimeError("Todos los jugadores ya votaron esta pregunta.")
        self.ronda.votos[jugador] = opcion
        self.actualizar_totales(votos_a, votos_b)
        return jugador

    def actualizar_totales(self, votos_a, votos_b):
        self.ronda.votos_a, self.ronda.votos_b = votos_a, votos_b

    def avanzar(self):
        if not self.ronda.completa:
            raise RuntimeError("Faltan jugadores por votar.")
        self.indice += 1
        return not self.terminada

    # ---------- resúmenes ----------
    def resumen_por_jugador(self):
        filas = []
        for j, nombre in enumerate(self.jugadores):
            c = {"mayoria": 0, "minoria": 0, "empate": 0}
            for r in self.rondas:
                if j in r.votos:
                    c[r.veredicto(j)] += 1
            filas.append({"jugador": nombre, **c})
        return filas

    def resumen(self):
        total = {"mayoria": 0, "minoria": 0, "empate": 0}
        for f in self.resumen_por_jugador():
            for k in total:
                total[k] += f[k]
        return total
