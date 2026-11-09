# PlayQuiz — ¿Qué prefieres?

Juego de preguntas de dos opciones para niños y adolescentes, con interfaz moderna en **CustomTkinter** y
**jugadores locales por ronda** (varias personas en la misma computadora). Al responder se muestra un **gráfico de barras
horizontales de Matplotlib** con la cantidad de votos de cada respuesta.

        ## Modos de juego
| 👥 **Local** | Solo los de los X jugadores de esta pantalla. **Empiezan en 0**, sin datos ficticios. | Jugar en grupo en una sola computadora. |
| 🧪 **Demostración** | Ficticios, acumulados, **editables y reiniciables**. Se avisa en pantalla y en el gráfico. | Probar la app. |
| 🌐 **Servidor real** | Reales, de varios dispositivos (`servidor.py`). | Encuestas con muchas personas. |

**Modo local:** elige X jugadores (− / + o escribiendo; 1 a 40, ajustable en `MAX_JUGADORES` de `playquiz/config.py`)
y sus nombres. En cada pregunta votan uno por uno (el orden rota) y el gráfico de Matplotlib crece con cada voto.
"Siguiente" se habilita en cuanto votó el último jugador. Con 1 jugador funciona igual (votación individual).

**Controles durante la partida:** 🏠 Inicio · 📂 Temáticas · 🔄 Reiniciar (en local vuelve a 0 votos) ·
✏️ Editar votos demo y 🗑 Reiniciar datos demo (solo demostración) · ↻ Actualizar (solo servidor) · Siguiente.

Si algo falla en un botón, la app muestra el error y lo guarda en `data/errores.log` (envíamelo para corregirlo).

## Estructura
```
playquiz/
├─ main.py                  # abre el juego (Tkinter)
├─ servidor.py              # servidor de votación real (Flask + SQLite)
├─ requirements.txt         # dependencias
├─ data/preguntas.json      # banco: 50 categorías x 10 = 500 preguntas
├─ playquiz/
│  ├─ config.py             # rutas y valores por defecto
│  ├─ banco.py              # carga y valida preguntas (pandas + NumPy)
│  ├─ almacen.py            # SQLite: votos, demo editable, historial
│  ├─ votos.py              # FuenteDemo (ficticia) y FuenteReal (servidor)
│  ├─ juego.py              # lógica de una partida (sin interfaz)
│  ├─ graficos.py           # gráficos de Matplotlib
│  ├─ app.py                # interfaz Tkinter
│  ├─ web.py                # página web para votar desde celulares
│  └─ estadisticas.py       # estadísticas generales y exportación a CSV
├─ tools/                   # generador del banco (datos_1..5.py + generar_preguntas.py)
└─ tests/                   # pruebas
```

## Instalación en Windows
1. Instala Python 3.10 o superior desde python.org (marca **Add Python to PATH**; Tkinter viene incluido; CustomTkinter se instala con pip).
2. En la carpeta del proyecto, abre una terminal (PowerShell) y ejecuta:
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar
- **Modo demostración:** `python main.py` → elige "Demostración" → ¡Jugar!
  Los votos son **ficticios** (se avisa en pantalla y en el gráfico) y puedes editarlos con "✏️ Editar votos demo".
- **Modo real:** en una computadora ejecuta `python servidor.py --host 0.0.0.0 --port 5000`.
  - Otros dispositivos de la misma red abren `http://IP-DE-LA-SERVIDORA:5000` en el navegador y votan (la página
    muestra el mismo gráfico de Matplotlib).
  - La app de escritorio también puede votar: en la bienvenida elige "Votación real", escribe la dirección del
    servidor, pulsa "Probar conexión" y juega. El gráfico se actualiza solo cada 5 segundos.
  - Windows puede pedir permiso en el Firewall la primera vez: acéptalo para redes privadas.
  - Para saber la IP: `ipconfig` (busca "Dirección IPv4").

## Cómo funciona cada parte
- **banco.py**: lee `preguntas.json` en un DataFrame de pandas, valida y
  elige preguntas al azar con NumPy.
- **almacen.py**: guarda votos en SQLite. La restricción `UNIQUE(pregunta_id, jugador_id)` impide votar dos veces
  la misma pregunta. También guarda los votos ficticios de la demo y el historial de partidas.
- **votos.py**: dos fuentes con la misma interfaz (`votar`, `resultados`). La demo suma votos ficticios
  reproducibles (semilla = id de pregunta) a los de la partida; la real habla con el servidor por HTTP.
- **juego.py**: lleva la cuenta de la partida y calcula si coincidiste con la opción más votada, la menos votada o hubo empate.
- **graficos.py**: dibuja las barras. Usa `Figure` sin `pyplot`, así se incrusta en Tkinter y también se exporta a PNG para la web.
- **servidor.py**: API (`/api/votar`, `/api/resultados/<id>`, `/api/grafico/<id>.png`, `/api/estadisticas`…).
- **estadisticas.py**: `python -m playquiz.estadisticas --db data/servidor.db --csv resultados.csv`.

Bibliotecas: matplotlib (gráficos), numpy (muestreo y semillas), pandas (banco y estadísticas), flask (servidor),
requests (cliente HTTP). customtkinter (interfaz moderna sobre Tkinter).

## Añadir preguntas y categorías
- **Rápido:** edita `data/preguntas.json`. Una pregunta nueva:
  `{"id": "futbol-11", "categoria": "futbol", "pregunta": "...", "opcion_a": "...", "opcion_b": "..."}`
  (el id debe ser único). Una categoría nueva se añade en la lista `categorias`:
  `{"id": "cocina", "nombre": "Cocina", "emoji": "🍳"}` y luego sus preguntas con `"categoria": "cocina"`.
- **Desde el generador:** edita `tools/datos_*.py` y ejecuta `python tools/generar_preguntas.py`
  (¡sobrescribe preguntas.json!).
- Al abrir el juego se valida el banco y avisa si hay errores.

## Pruebas
`pip install pytest` y luego `python -m pytest -q`. Cubren: banco (500/50/10), voto único, demo editable,
partida, gráficos (longitud de barras, empate, redibujado), servidor (votos, duplicados, PNG) y un recorrido
completo de la interfaz con 3 jugadores. La prueba de interfaz usa un doble simulado si CustomTkinter no está instalado.

## Sobre las temáticas
Las 50 temáticas son una selección curada a partir de intereses frecuentes de niñas, niños y adolescentes
(videojuegos, YouTube, TikTok, Roblox, anime, fútbol, etc.) y de las categorías pedidas. **No es un ranking
medido**: no hay datos suficientes para justificar un orden exacto. Fuentes consultadas de referencia:
[El CEO](https://elceo.com/negocios/youtube-disney-y-roblox-cuales-son-las-marcas-mejor-posicionadas-entre-los-jovenes-mexicanos/),
[LevelUp](https://www.levelup.com/noticias/ninos-mexicanos-prefieren-usar-tiktok-antes-que-netflix/),
[N+](https://www.nmas.com.mx/sociedad/entender-a-los-adolescentes-que-les-gusta-a-los-jovenes-mexicanos/).

## Limitaciones conocidas
- El "jugador" es un identificador anónimo guardado en `data/jugador.json` (o en el navegador). Evita votos
  repetidos accidentales, pero quien borre ese dato podría votar de nuevo. Para controles estrictos haría falta
  registro de usuarios.
- Los votos del modo real y los de la demo se guardan en bases distintas y nunca se mezclan.
