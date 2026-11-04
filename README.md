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

- **OpenAI**: `MODEL_PROVIDER=openai` y `OPENAI_API_KEY`.
- **Proveedor compatible** (usado en este proyecto: Gemini con `gemini-3.1-flash-lite`): descomentar el bloque `openai_compatible` y completar `PROVIDER_API_KEY`.

`ROUTER_STRATEGY` puede ser `deterministic`, `model` o `hybrid` (por defecto).

## Ejecución

Todos los comandos se ejecutan desde esta carpeta.

```bash
# Parámetros generados por la semilla
uv run python case_config.py

# Crear la base de ventas históricas (data/business.db)
uv run python bootstrap_db.py

# Caso completo de C-1003: política (RAG), facturación (SQL por MCP), crédito y stock (MCP),
# liberación con pausa para Finanzas y reanudación aprobada
uv run python e2e_demo.py

# Punto de entrada: el router decide si responde el agente o se ejecuta el workflow
uv run python main.py "¿Cuánto le hemos facturado a C-1003 en 2026?"
uv run python main.py "¿Cuánta línea de crédito disponible tiene C-1003?"

# Solicitud de liberación: va al workflow; si requiere Finanzas, se pausa en el id_hilo indicado
uv run python main.py --thread-id pedido-01 "Libera 9 KRN-900X para C-1003"
uv run python main.py --thread-id pedido-01 --resume approve --reviewer ana.finanzas --comment "Excepcion aprobada"

# Sin argumentos pregunta en la terminal (Enter usa "Libera 9 KRN-900X para C-1003")
uv run python main.py

# Workflow de liberación de venta (LangGraph). Sin --request usa "Libera 4 KRN-900X para C-1003"
uv run python workflow_demo.py --thread-id demo-01

# Pedido que pasa a Finanzas: el flujo se pausa en el id_hilo indicado
uv run python workflow_demo.py --thread-id demo-02 --request "Libera 9 KRN-900X para C-1003"

# Reanudar con el MISMO id_hilo y aprobar (--show-state muestra el estado persistido)
uv run python workflow_demo.py --thread-id demo-02 --resume approve --reviewer ana.finanzas --comment "Excepcion aprobada" --show-state

# Otro pedido pausado, esta vez rechazado por Finanzas
uv run python workflow_demo.py --thread-id demo-03 --request "Libera 7 KRN-900X para C-1003"
uv run python workflow_demo.py --thread-id demo-03 --resume reject --reviewer ana.finanzas

# Diagrama del workflow (Mermaid)
uv run python workflow_demo.py --diagram

# MCP: cliente sin LLM (lista y llama tools, lee una política por stdio)
uv run python mcp_client_demo.py

# MCP: agente conectado al mismo servidor (consulta compuesta por defecto o la que se indique)
uv run python mcp_agent.py
uv run python mcp_agent.py "¿Se puede liberar 1 NXS-G10 para C-9999?"

# MCP Inspector (interfaz web; requiere Node.js)
uv run mcp dev mcp_server.py

# Evaluación del router: 12 casos con las tres estrategias
uv run python benchmark.py

# Pruebas automáticas (no necesitan API key)
uv run pytest
```

### Fallo transitorio simulado

`SIMULATE_CREDIT_TIMEOUT=1` hace fallar el primer intento al servicio de crédito, para ver el retry:

```powershell
# PowerShell
$env:SIMULATE_CREDIT_TIMEOUT="1"; uv run python workflow_demo.py --thread-id demo-04
Remove-Item Env:SIMULATE_CREDIT_TIMEOUT
```

```bash
# Bash
SIMULATE_CREDIT_TIMEOUT=1 uv run python workflow_demo.py --thread-id demo-04
```

Los checkpoints se guardan en `data/workflow_checkpoints.db`. Cada `id_hilo` es un pedido: para empezar de cero, usar un `id_hilo` nuevo o borrar ese archivo.

## Estructura

| Archivo | Contenido |
|---|---|
| `case_config.py` | CASO_ID, semilla y los tres parámetros de crédito |
| `data.py` | Clientes, productos e inventario |
| `bootstrap_db.py` | Crea la tabla `sales` con las ventas históricas |
| `rules.py` | Reglas deterministas: validación del pedido (`validate_order`) y decisión de crédito (`evaluate_release`) |
| `release_state.py`, `release_workflow.py` | State y workflow de liberación de venta en LangGraph |
| `workflow_demo.py` | Ejecuta el workflow desde la terminal: iniciar, pausar y reanudar por `id_hilo` |
| `release_runner.py` | Ejecuta el workflow por `id_hilo` con los controles de reanudación y de servicio caído |
| `router.py` | Routers determinista, por modelo e híbrido, con 6 destinos (`rag`, `sql`, `tools`, `release`, `direct`, `clarify`) |
| `rag.py`, `docs/` | Recuperación semántica sobre las políticas de crédito y liberación |
| `tools.py` | Tools del agente (producto, stock, cliente, liberación, ventas, políticas) |
| `sales.py` | Consulta SQL parametrizada de ventas, compartida por el agente y el servidor MCP |
| `mcp_server.py` | Servidor MCP (stdio): 4 tools de solo lectura y 2 resources de políticas |
| `mcp_client_demo.py`, `mcp_agent.py` | Consumidores del servidor MCP: cliente sin LLM y agente |
| `engine.py` | Elige la ruta y ejecuta el agente: RAG local; `sql` y `tools` por el servidor MCP, cada ruta solo con sus tools |
| `schemas.py`, `context.py`, `model_factory.py` | Salidas estructuradas, contexto y configuración del modelo |
| `main.py` | Punto de entrada: router + agente + workflow (`--thread-id`, `--resume`) |
| `e2e_demo.py` | Caso completo reproducible de C-1003 |
| `benchmark.py`, `benchmark_cases.json` | Evaluación del router |
| `tests/` | Pruebas del router, SQL, tools, workflow y MCP |
| `HITOS.md` | Avance por hito |
| `EVIDENCIAS.md` | Evidencia de proceso y aprendizaje, pruebas mínimas y anexo con la evidencia de cada hito |
| `DECISIONES.md` | Decisiones de diseño: alternativas, trade-off, riesgo y cambios para producción |
| `USO_IA.md` | Uso de IA como copiloto |
| `git_log.txt`, `VIDEO_LINK.txt` | Historial de commits y enlace al video técnico |
