# Uso de IA

Caso **CRE-008** · Variante **Crédito** · Semilla **2135**

## Herramientas usadas

| Herramienta | Para qué |
|---|---|
| Claude Code (modelo Claude Opus 5.5), en VS Code | Copiloto: análisis del enunciado, propuesta de decisiones con alternativas, escritura de código y pruebas, ejecución de pruebas y borradores de documentación |
| Google Gemini (`gemini-3.1-flash-lite` y `gemini-embedding-001`) | No es copiloto: es el modelo que usa el sistema en ejecución (router por modelo, extractor del workflow, agente y embeddings del RAG) |

## 3 prompts representativos


Prompt 1

```text
Quiero construir en Python un "AI Operations Agent" para la empresa ficticia AndesSupply,
caso CRE-008, variante Crédito, semilla 2135. El proceso es la liberación de venta: un pedido
se libera, pasa a Finanzas o se rechaza, según el stock, el estado de crédito del cliente
(activo/hold), su línea disponible y el monto de revisión. Respeta literalmente lo que pide
el PDF adjunto para el Hito 1, sin adelantar hitos posteriores. Usa solo Python estándar, sin LLM.

1. case_config.py: sortea en orden fijo con random.Random(2135) el límite de crédito,
   la exposición actual (como monto) y el monto de revisión.
2. data.py: 3 clientes (C-1003 toma sus valores de la semilla), 5 productos e inventario.
3. bootstrap_db.py: crea data/business.db con ventas históricas en la tabla sales.
4. rules.py: calculate_release(customer_id, sku, quantity) devuelve RELEASE, REVIEW o REJECT,
   evaluando existencia → stock → hold → línea → monto de revisión, con sus reasons.
5. main.py: pide cliente, SKU y cantidad y muestra la decisión.
```

Prompt 2

```text
Sobre el workflow de liberación en LangGraph (release_workflow.py), agrega lo que pide el
PDF para el Hito 4, sin adelantar hitos posteriores:

1. Checkpoint persistente con SqliteSaver, por id_hilo.
2. RetryPolicy solo en fetch_credit_profile (3 intentos, solo TimeoutError o ConnectionError),
   con un modo para simular el timeout.
3. interrupt() en finance_review con el memo de crédito, y reanudación validada con
   FinanceDecision (approve o reject, revisor obligatorio). Una respuesta inválida vuelve
   a pausar; nunca aprueba por defecto.
4. Estados finales released_by_exception y rejected_by_finance.
5. workflow_demo.py con --thread-id, --resume, --reviewer, --comment y --show-state.
   Solo reanuda si ese id_hilo está detenido en finance_review.
```

Prompt 3

```text
Integra el router, el agente, el servidor MCP y el workflow de liberación según lo que pide
el PDF para el Hito 6:

1. Ruta release en el router: las solicitudes "Libera..." con cliente y SKU van al workflow.
2. Las rutas tools y sql del agente consumen el servidor MCP, cada una solo con sus tools.
3. Nodo gather_review_context antes de la pausa: agrega al memo el historial de ventas (SQL)
   y las políticas (RAG), sin cambiar la decisión. La respuesta final cita sus fuentes.
4. main.py como punto de entrada único (con --thread-id y --resume) y e2e_demo.py
   con el caso completo de C-1003.
5. README.md con todos los comandos, cada caso con su propio id_hilo. En HITOS.md no escribas
   las reflexiones personales: deja marcados los lugares donde las completo yo.
```

## Qué generó o sugirió la IA

- Análisis del enunciado y listas de decisiones por hito, con alternativas y una recomendación, indicando qué venía del PDF y qué era propuesta propia.
- Apoyo en el codigo y los borradores de `HITOS.md`, `EVIDENCIAS.md`, `DECISIONES.md` y `README.md` en el transcurso de los 6 hitos.
- Código y nombres en inglés y sin tildes; nombres de archivos y funciones lo más parecidos posible a los vistos en el curso.
- El registro de las pruebas y sus salidas como evidencia.

## Qué modificó o decidió el estudiante
- La arquitectura del codigo de los seis hitos en base a lo aprendido en clase.
- Elegir los 5 productos de una lista propia, en lugar de los propuestos.
- Exposición actual sorteada como monto, no como porcentaje del límite, y el orden de los sorteos de la semilla.
- Cliente en hold como excepción para Finanzas (lectura literal del enunciado), en lugar de rechazo directo.
- Quedarse con 12 casos de benchmark y reemplazar una pregunta redundante.
- Excluir `uv.lock` del repositorio y acotar las versiones.
- Usar Gemini con tier gratuito cuando la cuenta de OpenAI no tenía créditos.
- Separar el stock (precondición) de la decisión de crédito en el workflow.
- La ejecución de las pruebas.


## Sugerencias rechazadas

| Sugerencia de la IA | Decisión | Por qué |
|---|---|---|
| Agregar cinco reglas de crédito (deuda vencida, cliente sin historial, pedido duplicado, validación de la solicitud, advertencia por uso de línea) | Se agregaron a la lista y luego se descartaron | Pasaban de 5 a 10 reglas y de 3 a 5 clientes, y el enunciado no las pide. Se priorizó el núcleo: hold, línea insuficiente y monto de revisión, que son los parámetros de la semilla |
| Cuatro clientes: el principal, uno con línea holgada, uno en hold y otro para variar las ventas | Se quedaron 3 clientes | Los tres perfiles ya llevan a todas las salidas (liberar, revisión por línea o por monto, hold). El cuarto solo agregaba filas de ventas |
| Guardar clientes, productos e inventario en archivos JSON dentro de `data/` | Quedaron como diccionarios en `data.py` | Se leen directo en el código, sin una capa de carga. La carpeta `data/` igual se usa para `business.db` |
| Subir `uv.lock` al repositorio | Se excluyó y se acotaron los rangos en `pyproject.toml` | El enunciado no lo pide entre los entregables. Con los rangos acotados, `uv sync` no instala versiones mayores que puedan romper el proyecto |
| Un caso 13 en el benchmark para el monto de revisión | Se mantuvieron 12 casos | El benchmark evalúa el router, y el router no mira montos: "Libera 7 KRN-900X" y "Libera 9 KRN-900X" van a la misma ruta (`tools`). El caso de monto solo ya se demuestra en las reglas y en el workflow |
| Que Finanzas reanude con un booleano `approved` validado | Se reemplazó por el contrato `FinanceDecision` (`approve` o `reject`, revisor obligatorio) | Con un booleano hay que interpretar lo que llega: en Python un texto como "no" cuenta como verdadero. Dos valores explícitos validados con pydantic no dejan dudas en la rama más crítica, la que libera un pedido |
| Opción `--retry-pending` para continuar un pedido detenido por el servicio de crédito | No se agregó | El enunciado no la pide. El mensaje de error ya indica que el pedido quedó guardado en su `id_hilo`, y el checkpoint ya se demuestra con la pausa y la reanudación de Finanzas |
| Resource MCP `case://parameters` con la semilla, el límite, la exposición y el monto de revisión | No se agregó | Publicaría el monto de revisión: quien lo conozca puede dividir un pedido grande en varios menores para que ninguno llegue a Finanzas. Además, el límite y la exposición ya los entrega `get_customer_credit`, y las dos políticas cubren el mínimo de Resources |
| Un prompt MCP en el servidor | No se agregó | El enunciado no lo pide, y el servidor expone solo lo necesario: 4 tools de solo lectura y 2 Resources |

## Errores de la IA detectados

| Error | Cómo se detectó | Corrección |
|---|---|---|
| Recomendó tratar al cliente en hold como rechazo directo, contra la tabla del enunciado (sección 04) | El estudiante pidió revisar todo contra el PDF | Hold pasó a ser excepción para Finanzas |
| Propuso "hold" como palabra clave de RAG, aunque "¿C-9999 está en hold?" pregunta por el estado actual | Revisión de las palabras clave | Pasó a la ruta `tools` |
| Redactó el caso 12 del benchmark con la palabra "ventas", que manda la pregunta a SQL | Al ejecutar el benchmark falló un caso que debía acertar | Se reemplazó la pregunta |
| En el primer diseño del workflow, revisaba el stock junto con el crédito | El estudiante preguntó si los nodos correspondían solo a la liberación de venta | El stock pasó a ser precondición en `validate_order` |
| Afirmó que `interrupt()` sin checkpoint fallaba al ejecutarse | Al probarlo: la pausa funciona; lo que falla es reanudar (`RuntimeError: Cannot use Command(resume=...) without checkpointer`) | Se corrigió la explicación en `HITOS.md` |
| En el README puso tres reanudaciones seguidas sobre el mismo `id_hilo`, y solo la primera funcionaba | Al ejecutar todos los comandos del README en orden | Un `id_hilo` distinto para cada caso |
| Integró el workflow síncrono en un `main.py` asíncrono sin prever el conflicto | El caso end-to-end falló con `RuntimeError: AgentRunner.run_sync() cannot be called when an event loop is already running` | El workflow se ejecuta con `asyncio.to_thread` |


## Cómo se validó antes de confiar

- **Contra el enunciado:** cada recomendación indicaba si venía del PDF o era propuesta propia, y se revisó todo contra el PDF cuando hubo dudas.
- **Pruebas automáticas:** 35 pruebas que no usan el LLM (router, SQL, tools, workflow y MCP por stdio). Se ejecutaron después de cada cambio.
- **Ejecución real:** cada hito se probó con el LLM real y las salidas quedaron en `EVIDENCIAS.md`. Algunos errores solo aparecieron así (SDK de MCP, event loop, `id_hilo`).
- **Comprobar antes de afirmar:** comportamientos dudosos (reanudar sin checkpoint, reanudar con otro `id_hilo`, servicio de crédito caído en todos los intentos) se probaron antes de documentarlos.

