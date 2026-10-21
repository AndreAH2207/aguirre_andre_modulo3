# AI Operations Agent · AndesSupply

Trabajo integrador del Módulo 3 (DSRP · AI Engineer).

| CASO_ID | Variante | Semilla |
|---|---|---|
| CRE-008 | Crédito | 2135 |

Proceso: liberación de venta. El sistema decide si un pedido se libera, pasa a revisión de Finanzas o se rechaza, según el stock, el estado de crédito del cliente, su línea disponible y el monto de revisión.

## Requisitos

- Python 3.11 o superior.
- [uv](https://docs.astral.sh/uv/).
- Una API key de OpenAI o de un proveedor compatible (por ejemplo Google Gemini, que tiene tier gratuito).

## Instalación

```bash
uv sync
```

Copiar `.env.example` como `.env` y completar la clave. El archivo trae dos opciones:

- **OpenAI** (como en clase): `MODEL_PROVIDER=openai` y `OPENAI_API_KEY`.
- **Proveedor compatible** (usado en este proyecto: Gemini con `gemini-3.1-flash-lite`): descomentar el bloque `openai_compatible` y completar `PROVIDER_API_KEY`.

`ROUTER_STRATEGY` puede ser `deterministic`, `model` o `hybrid` (por defecto).

## Ejecución

Todos los comandos se ejecutan desde esta carpeta.

```bash
# Parámetros generados por la semilla
uv run python case_config.py

# Crear la base de ventas históricas (data/business.db)
uv run python bootstrap_db.py

# Agente: pregunta en lenguaje natural (Enter usa "Libera 9 KRN-900X para C-1003")
uv run python main.py

# Evaluación del router: 12 casos con las tres estrategias
uv run python benchmark.py

# Pruebas automáticas (no necesitan API key)
uv run pytest
```

## Estructura

| Archivo | Contenido |
|---|---|
| `case_config.py` | CASO_ID, semilla y los tres parámetros de crédito |
| `data.py` | Clientes, productos e inventario |
| `bootstrap_db.py` | Crea la tabla `sales` con las ventas históricas |
| `rules.py` | Reglas deterministas de liberación (`calculate_release`) |
| `router.py` | Routers determinista, por modelo e híbrido |
| `rag.py`, `docs/` | Recuperación semántica sobre las políticas de crédito y liberación |
| `tools.py` | Tools del agente (producto, stock, cliente, liberación, ventas, políticas) |
| `engine.py` | Elige la ruta y ejecuta el agente con las tools de esa ruta |
| `schemas.py`, `context.py`, `model_factory.py` | Salidas estructuradas, contexto y configuración del modelo |
| `main.py` | Punto de entrada |
| `benchmark.py`, `benchmark_cases.json` | Evaluación del router |
| `tests/` | Pruebas del router, SQL y tools |
| `HITOS.md` | Avance por hito |
| `EVIDENCIAS.md` | Evidencias de cada hito |
