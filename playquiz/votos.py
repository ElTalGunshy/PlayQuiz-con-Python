"""Fuentes de votos: demostración (local, ficticia) y real (servidor Flask)."""
import json
import uuid
from dataclasses import dataclass
from typing import Optional

from . import config
from .almacen import Almacen


class ErrorServidor(RuntimeError):
    """No se pudo hablar con el servidor de votación."""


@dataclass
class Resultado:
    votos_a: int
    votos_b: int
    duplicado: bool = False          # el jugador ya había votado esta pregunta
    tu_opcion: Optional[str] = None  # opción registrada para este jugador


def cargar_jugador_id(ruta=None):
    """Identificador anónimo de este equipo; se crea la primera vez y se reutiliza."""
    ruta = ruta or config.JUGADOR
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))["jugador_id"]
    except (OSError, ValueError, KeyError):
        jugador = uuid.uuid4().hex
        try:
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps({"jugador_id": jugador}), encoding="utf-8")
        except OSError:
            pass
        return jugador


class FuenteLocal:
    """Modo local: votos SOLO de los jugadores de esta pantalla. Todo empieza en 0 (sin datos ficticios).

    Los votos viven en memoria durante la partida; el resumen final se guarda en el historial.
    """
    modo = "local"
    es_demo = False
    es_local = True

    def __init__(self):
        self._conteos = {}                 # pregunta_id -> [votos_a, votos_b]
        self._votos = {}                   # (pregunta_id, indice_jugador) -> opcion
        self.jugador_id = "local-" + uuid.uuid4().hex[:12]

    def id_jugador(self, indice):
        return f"{self.jugador_id}-j{indice + 1}"

    def votar(self, pregunta_id, opcion, jugador_id=None) -> Resultado:
        if opcion not in ("A", "B"):
            raise ValueError("La opción debe ser 'A' o 'B'.")
        clave = (pregunta_id, jugador_id or self.jugador_id)
        previa = self._votos.get(clave)
        if previa is None:
            self._votos[clave] = opcion
            c = self._conteos.setdefault(pregunta_id, [0, 0])
            c[0 if opcion == "A" else 1] += 1
        a, b = self._conteos.get(pregunta_id, [0, 0])
        return Resultado(a, b, duplicado=previa is not None, tu_opcion=previa or opcion)

    def resultados(self, pregunta_id, jugador_id=None) -> Resultado:
        a, b = self._conteos.get(pregunta_id, [0, 0])
        return Resultado(a, b, tu_opcion=self._votos.get((pregunta_id, jugador_id or self.jugador_id)))


class FuenteDemo:
    """Votos simulados y acumulados (editables y reiniciables). Cada partida usa una sesión nueva."""
    modo = "demo"
    es_demo = True
    es_local = False

    def __init__(self, almacen: Almacen):
        self.almacen = almacen
        self.jugador_id = "demo-" + uuid.uuid4().hex[:12]

    def id_jugador(self, indice):
        """Identificador de cada jugador de la mesa local (0, 1, 2…)."""
        return f"{self.jugador_id}-j{indice + 1}"

    def votar(self, pregunta_id, opcion, jugador_id=None) -> Resultado:
        jugador_id = jugador_id or self.jugador_id
        self.almacen.registrar_voto(pregunta_id, jugador_id, opcion)
        return self.resultados(pregunta_id, jugador_id)

    def resultados(self, pregunta_id, jugador_id=None) -> Resultado:
        a, b = self.almacen.conteo(pregunta_id, con_base_demo=True)
        return Resultado(a, b, tu_opcion=self.almacen.voto_de(pregunta_id, jugador_id or self.jugador_id))

    def editar_base(self, pregunta_id, votos_a, votos_b):
        self.almacen.fijar_base_demo(pregunta_id, votos_a, votos_b)

    def reiniciar_datos(self):
        """Borra lo editado y los votos acumulados de la demo."""
        self.almacen.reiniciar_demo()


class FuenteReal:
    """Votos reales guardados por el servidor (servidor.py)."""
    modo = "real"
    es_demo = False
    es_local = False

    def __init__(self, url, jugador_id, tiempo_espera=6):
        import requests  # se importa aquí para que el modo demo funcione sin la biblioteca
        self._requests = requests
        self.url = url.rstrip("/")
        self.jugador_id = jugador_id
        self.tiempo_espera = tiempo_espera

    def _llamar(self, metodo, ruta, **kw):
        try:
            return self._requests.request(metodo, self.url + ruta, timeout=self.tiempo_espera, **kw)
        except self._requests.RequestException as e:
            raise ErrorServidor(f"No se pudo conectar con {self.url}. ¿Está encendido el servidor?") from e

    def probar(self):
        r = self._llamar("GET", "/api/salud")
        if r.status_code != 200:
            raise ErrorServidor(f"El servidor respondió con el código {r.status_code}.")
        return True

    def id_jugador(self, indice):
        """Cada jugador de la mesa local es un votante distinto para el servidor."""
        return f"{self.jugador_id}-j{indice + 1}"

    def votar(self, pregunta_id, opcion, jugador_id=None) -> Resultado:
        r = self._llamar("POST", "/api/votar", json={
            "pregunta_id": pregunta_id, "jugador_id": jugador_id or self.jugador_id, "opcion": opcion})
        if r.status_code not in (200, 201, 409):
            raise ErrorServidor(f"El servidor rechazó el voto: {r.text[:200]}")
        d = r.json()
        return Resultado(d["votos_a"], d["votos_b"], duplicado=(r.status_code == 409),
                         tu_opcion=d.get("tu_opcion"))

    def resultados(self, pregunta_id, jugador_id=None) -> Resultado:
        r = self._llamar("GET", f"/api/resultados/{pregunta_id}",
                         params={"jugador_id": jugador_id or self.jugador_id})
        if r.status_code != 200:
            raise ErrorServidor(f"No se pudieron leer los resultados ({r.status_code}).")
        d = r.json()
        return Resultado(d["votos_a"], d["votos_b"], tu_opcion=d.get("tu_opcion"))
