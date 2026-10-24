# Hitos

Caso **CRE-008** · Variante **Crédito** · Semilla **2135**

## Hito 1 · Comprender y separar responsabilidades

### Qué se construyó

- `case_config.py`: CASO_ID, semilla y los tres parámetros de crédito. Se sortean en orden fijo con `random.Random(2135)`: límite de crédito (30 000), exposición actual (10 000) y monto de revisión (15 000). Se imprimen al ejecutar el archivo.
- `data.py`: clientes, productos e inventario. C-1003 toma su límite y exposición de la semilla; C-1010 y C-9999 tienen valores fijos.
- `bootstrap_db.py`: crea `data/business.db` con 9 ventas históricas en la tabla `sales`.
- `rules.py`: la función `calculate_release(customer_id, sku, quantity)` decide si un pedido se libera (`RELEASE`), pasa a Finanzas (`REVIEW`) o se rechaza (`REJECT`). Orden de evaluación: existencia → stock → hold → línea → monto de revisión. Las causas de revisión se juntan en `reasons`.
- `main.py`: punto de entrada. Imprime CASO_ID, semilla y parámetros, crea la base si no existe, pide cliente, SKU y cantidad, y muestra la decisión de `calculate_release`. Todavía no usa LLM, por eso pide los datos por separado en vez de una pregunta en lenguaje natural.
- `pyproject.toml` y `.env.example`. Por ahora no hay dependencias, porque el Hito 1 usa solo Python estándar.
- 10 solicitudes de ejemplo clasificadas a mano (ver `EVIDENCIAS.md`).

### Qué falló

- Primero la exposición se sorteaba como porcentaje del límite. Con la semilla 2135 salía 88 %, y C-1003 quedaba con solo 3 600 USD disponibles. Así el monto de revisión (15 000) nunca podía activarse, porque cualquier pedido de ese tamaño ya excedía la línea antes. El parámetro existía, pero no influía en ninguna decisión.
- La suma de ventas de C-1010 salía como `52835.299999999996` por la forma en que se guardan los decimales. Lo corregí redondeando con `Decimal` (`_round_usd`), porque `round()` también falla en casos como 2.675.
- En la terminal de Git Bash los textos con tilde se veían mal ("Cr�dito"). Saqué las tildes del código para que la salida sea legible en el video.

### Qué aprendí

- La mayoría de las decisiones de este caso son comparaciones de números (pedido contra stock, exposición más pedido contra límite, pedido contra monto de revisión). No necesitan un modelo y es mejor que no lo usen, porque una regla en Python siempre da el mismo resultado y se puede probar.
- Que la semilla genere valores no basta: hay que verificar que esos valores cambien alguna decisión.
- Una misma pregunta puede parecer de un tipo y ser de otro. "¿Cuánto nos debe C-1003?" suena a historial (SQL), pero es el saldo actual (Tool).

### Qué decisión cambió después de probar

- La exposición pasó de porcentaje del límite a monto fijo sorteado de una lista (5 000 a 25 000). Con eso C-1003 tiene 20 000 disponibles, y los tres parámetros cambian alguna decisión (ver tabla de verificación en `EVIDENCIAS.md`).
- Cliente en hold: al principio lo trataba como rechazo directo. Lo cambié a revisión de Finanzas, porque el enunciado (sección 04, fila D) lo pone como excepción con aprobación humana.
- Los datos estaban en archivos JSON; los pasé a diccionarios en `data.py`, que es más simple de leer y de modificar durante la demo. La carpeta `data/` queda para la base de ventas.

### Evidencia

- Tabla "consulta → capacidad esperada → justificación" en `EVIDENCIAS.md`.
- `python case_config.py` ejecutado dos veces con los mismos valores.
- Resultados de `calculate_release` para cada tipo de salida en `EVIDENCIAS.md`.
- Ejecución de `python main.py` con un pedido de ejemplo en `EVIDENCIAS.md`.

### Preguntas de razonamiento

**¿Qué decisiones NO necesitan un LLM?**
Todas las que comparan números o revisan estados: si hay stock suficiente, si el cliente está en hold, si exposición + pedido supera el límite y si el pedido alcanza el monto de revisión. También calcular el monto del pedido (precio × cantidad). Las resuelve `calculate_release` en Python. El LLM sirve para entender la solicitud en lenguaje natural y sacar de ahí el cliente, el SKU y la cantidad, pero no para decidir si se libera.

**¿Qué dato cambia frecuentemente y no debería vivir en un prompt?**
El stock y la exposición de cada cliente. El stock baja con cada venta y la exposición sube con cada pedido liberado y baja con cada pago. Si estuvieran escritos en un prompt, el agente respondería con valores viejos. Se tienen que consultar en el momento con una tool. Lo mismo pasa con los parámetros de la semilla: viven en `case_config.py`, no en un texto.

**¿Qué información es documental y qué información es transaccional?**
Documental: las políticas, por ejemplo qué hacer con un cliente en hold o quién aprueba un pedido grande. Cambian poco, están escritas en texto y se consultan con RAG citando la fuente. Transaccional: las ventas históricas, el stock y la exposición de cada cliente. Son números que se registran con cada operación y se consultan con SQL (historial) o con tools (estado actual).

## Hito 2 · Router + RAG + SQL + Tools

### Qué se construyó

- `router.py`: tres routers (`DeterministicRouter`, `ModelRouter`, `HybridRouter`) con 5 destinos: `rag`, `sql`, `tools`, `direct` y `clarify`. Se elige con `ROUTER_STRATEGY` en el `.env` (por defecto `hybrid`, umbral 0,90). Las palabras clave se adaptaron a crédito y la consulta se normaliza sin tildes antes de compararla.
- `rag.py` + `docs/`: dos políticas (`credit_policy.md` y `release_policy.md`), divididas por secciones `##`, buscadas con embeddings y citadas con `source_ref`. La política no escribe la cifra del monto de revisión: el valor vive solo en `case_config.py`.
- `tools.py`: seis tools: `get_product`, `get_stock`, `get_customer` (con línea disponible), `calculate_release` (llama a `rules.py`), `sales_summary` (SQL parametrizado, con filtros opcionales de SKU, cliente y año) y `search_policies` (RAG).
- `engine.py`: el router elige la ruta y el agente solo recibe las tools de esa ruta. `main.py` ahora recibe una pregunta en lenguaje natural.
- `benchmark.py` y `benchmark_cases.json`: 12 casos de evaluación del router.
- `tests/`: 7 pruebas del router y 7 de SQL y tools, que no necesitan API.

### Qué falló

- La cuenta de OpenAI no tenía créditos (error 429 `insufficient_quota`). Todo lo que usa el LLM quedó sin poder ejecutarse.
- Al pasar a Gemini, `gemini-2.5-flash` ya no estaba disponible para cuentas nuevas (error 404). Después, `gemini-3.8-flash` agotó su cuota gratuita de 20 solicitudes diarias con un solo benchmark.
- El router por reglas manda "¿Explica que es la exposición crediticia?" a `tools` en vez de `direct`, porque contiene "exposicion" y la regla de tools se revisa antes que la de preguntas conceptuales. El híbrido no lo corrige: la confianza de la regla (0,92) supera el umbral, así que nunca consulta al modelo.
- El router por modelo (`gemini-3.1-flash-lite`) manda "¿Puedo liberar el pedido?" a `tools` aunque no tiene cliente ni SKU. En este caso las reglas sí aciertan (`clarify`).
- El caso 12 del benchmark se redactó primero con la palabra "ventas" ("riesgo crediticio en ventas B2B") y el router lo mandaba a SQL. Lo cambié por "¿Por qué las empresas B2B venden a plazo?".

### Qué aprendí

- Ningún router es mejor en todo. Las reglas son instantáneas y no gastan cuota, pero fallan con seguridad. El modelo entiende mejor el significado, pero es lento (137 s para 12 consultas) y también se equivoca. El híbrido solo mejora los casos donde las reglas dudan; si la regla está segura y equivocada, el error pasa.
- El orden de las reglas importa tanto como las palabras clave: la misma palabra puede llevar a rutas distintas según qué regla se revise primero.
- Depender de un proveedor externo es un riesgo real: en un solo día me quedé sin saldo, con un modelo retirado y con la cuota agotada.

### Qué decisión cambió después de probar

- Proveedor: de OpenAI a Gemini con tier gratuito, usando la opción `openai_compatible` de `model_factory.py`. Se desactivó el tracing del SDK, que intenta enviar trazas a OpenAI.
- Modelo: de `gemini-3.8-flash` a `gemini-3.1-flash-lite`, por la cuota diaria.
- "hold" pasó de palabra clave de RAG a palabra clave de tools: "¿C-9999 está en hold?" pregunta por el estado actual del cliente, no por la política.
- `uv.lock` se excluyó del repositorio y se acotaron los rangos de versiones en `pyproject.toml`.

### Evidencia

En `EVIDENCIAS.md`, sección Hito 2: benchmark de los tres routers, errores del router explicados, 3 pruebas RAG (incluida una que no usa RAG), 3 SQL, 3 tools y ejecuciones del agente de punta a punta.

### Preguntas de razonamiento

**¿Por qué una consulta de ventas históricas no debería resolverse con RAG?**
Porque la respuesta es un cálculo sobre muchas filas (sumar montos, contar ventas), no un párrafo que se pueda recuperar. RAG trae los textos más parecidos a la pregunta; no suma ni filtra por cliente o año. Con SQL el resultado es exacto y siempre el mismo: "¿Cuánto le hemos facturado a C-1003 en 2026?" da 28 559,80 desde `sales_summary`.

**¿Qué ocurre si el router tiene baja confianza?**
En el router híbrido, si la regla devuelve una confianza menor a 0,90, la decisión pasa al modelo. Pasa con "¿Por qué las empresas B2B venden a plazo?": ninguna regla aplica, queda en `direct` con 0,55 y el modelo confirma `direct`. El problema es el caso contrario: una regla equivocada pero con confianza alta no se revisa.

**¿Cuál es el costo de enviar toda pregunta a todas las herramientas?**
Más llamadas al modelo y más tokens, porque el agente tiene que decidir entre seis tools en vez de una o cuatro. También más riesgo: con todas disponibles, el agente podría usar RAG para una pregunta de ventas o llamar a `calculate_release` cuando solo se preguntó por stock. Por eso `engine.py` le da a cada ruta solo sus tools (`_tools_for`).

## Hito 3 · Workflow con estado

### Qué se construyó

- `release_workflow.py`: workflow de liberación de venta en LangGraph, con 7 nodos y 2 aristas condicionales:
  1. `extract_request`: el LLM convierte el texto en cliente, SKU y cantidad. Es el único paso probabilístico.
  2. `validate_order`: precondiciones del pedido (cliente y SKU existen, hay stock). No es una decisión de crédito.
  3. `fetch_credit_profile`: consulta el servicio de crédito (estado, límite, exposición).
  4. `compute_exposure`: calcula línea disponible y exposición proyectada, sin decidir nada.
  5. `evaluate_release`: la decisión de crédito (hold, línea, monto de revisión).
  6. `finance_review`: el pedido queda retenido para Finanzas / crédito.
  7. `issue_release`: emite el resultado (liberado, retenido, rechazado o bloqueado).
- Arista condicional 1, después de `validate_order`: si el pedido está bloqueado o rechazado, va directo a `issue_release` sin consultar el crédito.
- Arista condicional 2, después de `evaluate_release`: `REVIEW` va a `finance_review`; `RELEASE` va directo a `issue_release`.
- `release_state.py`: `ReleaseRequest` (contrato de extracción con campos opcionales) y `ReleaseState` (14 campos explícitos).
- `rules.py` separado en `validate_order` (precondiciones) y `evaluate_release` (crédito). La tool `calculate_release` llama a las dos y da los mismos resultados que antes.
- `build_credit_memo()`: arma el memo con lo que Finanzas necesita para decidir.
- `workflow_demo.py`: ejecuta una solicitud y muestra el resultado, el memo de crédito y, con `--diagram`, el diagrama del grafo.

### Qué falló

En la ejecución no hubo fallos: las 20 pruebas pasan y las cuatro rutas funcionan con el LLM real. Los problemas aparecieron en el diseño, antes de programar. Para cada uno, qué hubiera pasado si se dejaba así:

**1. Stock mezclado con el crédito.** El primer diseño revisaba el stock en el mismo paso que el hold, la línea y el monto.
- Qué hubiera pasado: un pedido sin stock igual consultaba el servicio de crédito, una llamada inútil a una dependencia externa. En el Hito 4 ese servicio tiene retry, así que se podía reintentar una consulta que no hacía falta. Además el stock, que decide logística, quedaba presentado como un criterio de crédito.
- Corrección: el stock pasó a `validate_order`, como precondición del pedido. Si falla, la primera arista condicional lleva directo a `issue_release`. La prueba `test_insufficient_stock_exits_before_credit_check` comprueba que el State no tiene `credit_status`, es decir, que nunca se consultó el crédito.

**2. Extracción con campos obligatorios.** La primera versión del contrato de extracción tenía cliente, SKU y cantidad como campos obligatorios.
- Qué hubiera pasado: ante "Libera el pedido de C-1003 por favor", el modelo está obligado a llenar SKU y cantidad. O inventa valores (y se evalúa un pedido que nadie pidió) o la validación falla y la ejecución se cae con un error.
- Corrección: los campos son opcionales y, si falta alguno, el flujo termina como `blocked` pidiendo los datos. Con esa solicitud, el modelo devolvió SKU y cantidad vacíos y el flujo se bloqueó.

**3. Reglas duplicadas.** La opción directa era repetir el cálculo dentro de los nodos del workflow, además de tenerlo en la tool `calculate_release`.
- Qué hubiera pasado: si en el video se cambia el monto de revisión o una regla en un lugar y no en el otro, el agente y el workflow darían respuestas distintas para el mismo pedido.
- Corrección: las reglas viven solo en `rules.py`. La tool y el workflow llaman a las mismas funciones.

**4. `interrupt()` en este hito.** Lo consideré para `finance_review`.
- Qué hubiera pasado: lo probé en un grafo mínimo. Sin checkpoint, `interrupt()` sí pausa el flujo, pero al reanudar falla con `RuntimeError: Cannot use Command(resume=...) without checkpointer`. La pausa no serviría de nada: Finanzas no podría aprobar ni rechazar.
- Corrección: `interrupt()` queda para el Hito 4, junto con el checkpoint. En este hito `finance_review` deja el pedido como `pending_review`.

**5. Fichas completas en el State.** La opción directa era guardar en el State las fichas completas de `cliente` y `producto`.
- Qué hubiera pasado: estado, límite y exposición quedarían dos veces (en la ficha y en sus campos), y cualquier cambio en `data.py` cambiaría lo que viaja por el workflow. Desde el Hito 4, todo eso se guardaría en el checkpoint mientras el pedido espera a Finanzas.
- Corrección: el State tiene 14 campos explícitos, solo los que usa la decisión.

### Qué aprendí

- Un workflow sirve cuando hay pasos con distinta naturaleza: uno probabilístico (extraer), consultas a fuentes (servicio de crédito), cálculos y una decisión. Separarlos permite saber en qué paso falló algo.
- Las aristas condicionales también sirven para no hacer trabajo de más: un pedido sin stock no tiene por qué consultar el servicio de crédito.
- Para que el workflow y la tool decidan igual, la regla tiene que vivir en un solo lugar.

### Qué decisión cambió después de probar

- `finance_review` queda sin `interrupt()` en este hito. `interrupt()` necesita checkpoint, que es parte del Hito 4; en este hito el nodo solo deja el pedido como `pending_review`.
- El State no guarda las fichas completas de cliente y producto: solo los campos que usa la decisión.
- Los nodos se nombraron según los pasos de un analista de crédito (validar pedido, consultar perfil de crédito, calcular exposición, evaluar, revisión de Finanzas, emitir resultado) en lugar de nombres genéricos.

### Evidencia

En `EVIDENCIAS.md`, sección Hito 3: diagrama del workflow, ejecución de la ruta directa, las otras tres rutas y las pruebas automáticas.

### Campos del State

| Campo | Lo escribe | Para qué sirve |
|---|---|---|
| `request_text` | Entrada | El texto original de la solicitud; lo lee el extractor |
| `customer_id` | `extract_request` | Cliente del pedido |
| `sku` | `extract_request` | Producto del pedido |
| `quantity` | `extract_request` | Unidades del pedido |
| `order_amount_usd` | `validate_order` | Precio × cantidad. Es el monto que comparan las reglas de línea y de monto de revisión |
| `credit_status` | `fetch_credit_profile` | `ok` o `hold` |
| `credit_limit_usd` | `fetch_credit_profile` | Límite de crédito del cliente (para C-1003 viene de la semilla) |
| `current_exposure_usd` | `fetch_credit_profile` | Lo que el cliente ya debe (para C-1003 viene de la semilla) |
| `available_credit_usd` | `compute_exposure` | Límite − exposición. Es lo primero que mira Finanzas |
| `projected_exposure_usd` | `compute_exposure` | Exposición + pedido. Es el valor que la regla compara con el límite |
| `decision` | `validate_order` o `evaluate_release` | `RELEASE`, `REVIEW` o `REJECT`. Controla la segunda arista condicional |
| `reasons` | `validate_order` o `evaluate_release` | Motivos legibles de la decisión |
| `status` | Todos los nodos | En qué etapa va el pedido. Controla la primera arista condicional y el mensaje final |
| `message` | `extract_request` o `issue_release` | Respuesta final para el usuario |

### Preguntas de razonamiento

**¿Por qué no basta una cadena de if/else en este caso?**
Las reglas sí son if/else, y viven en `rules.py`. Lo que el workflow agrega es el proceso alrededor: pasos con naturaleza distinta (un LLM, un servicio externo, cálculos, una decisión), un camino que se corta antes cuando el pedido no es válido, y un punto donde el proceso espera a una persona. En el Hito 4 ese punto tiene que poder pausarse, guardar el estado y continuar después; una cadena de if/else no puede detenerse a esperar y retomar donde quedó.

**¿Qué información necesita sobrevivir de un nodo a otro?**
Los datos del pedido (cliente, SKU, cantidad y monto), los datos de crédito con los que se decidió (estado, límite, exposición, disponible y proyectada), y la decisión con sus motivos. Si el pedido va a Finanzas, todo eso es lo que forma el memo: la persona tiene que ver exactamente los valores que usó la regla.

**¿Qué campo del State sería innecesario o peligroso guardar?**
Innecesario: la ficha completa del cliente o del producto. Del producto solo se usa el precio, y la ficha del cliente duplicaría el estado, el límite y la exposición, que ya se guardan aparte. Además ata el workflow a la estructura de `data.py`. Peligroso: la clave de la API o la respuesta cruda del LLM. Desde el Hito 4, el State se guarda en el checkpoint, y cualquier secreto quedaría escrito en la base de datos.
