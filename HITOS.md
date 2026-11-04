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
- 10 solicitudes de ejemplo clasificadas a mano.

### Qué falló

- Primero la exposición se sorteaba como porcentaje del límite. Con la semilla 2135 salía 88 %, y C-1003 quedaba con solo 3 600 USD disponibles. Así el monto de revisión (15 000) nunca podía activarse, porque cualquier pedido de ese tamaño ya excedía la línea antes. El parámetro existía, pero no influía en ninguna decisión.
- La suma de ventas de C-1010 salía como `52835.299999999996` por la forma en que se guardan los decimales. Lo corregí redondeando con `Decimal` (`_round_usd`), porque `round()` también falla en casos como 2.675.
- En la terminal de Git Bash los textos con tilde se veían mal ("Cr�dito"). Saqué las tildes del código para que la salida sea legible en el video.

### Qué aprendí

- La mayoría de las decisiones de este caso son comparaciones de números (pedido contra stock, exposición más pedido contra límite, pedido contra monto de revisión). No necesitan un modelo y es mejor que no lo usen, porque una regla en Python siempre da el mismo resultado y se puede probar.
- Que la semilla genere valores no basta: hay que verificar que esos valores cambien alguna decisión.
- Una misma pregunta puede parecer de un tipo y ser de otro. "¿Cuánto nos debe C-1003?" suena a historial (SQL), pero es el saldo actual (Tool).

### Qué decisión cambió después de probar

- La exposición pasó de porcentaje del límite a monto fijo sorteado de una lista (5 000 a 25 000). Con eso C-1003 tiene 20 000 disponibles, y los tres parámetros cambian alguna decisión.
- Cliente en hold: al principio lo trataba como rechazo directo. Lo cambié a revisión de Finanzas, porque el enunciado (sección 04, fila D) lo pone como excepción con aprobación humana.
- Los datos estaban en archivos JSON; los pasé a diccionarios en `data.py`, que es más simple de leer y de modificar durante la demo. La carpeta `data/` queda para la base de ventas.

### Evidencia

En `EVIDENCIAS.md`:

- A.1: escenario de la semilla (mismos valores en cada ejecución), datos mínimos y primer commit de datos y reglas.
- A.2: tabla "consulta → capacidad esperada → justificación".
- 1.4: resultados de `calculate_release` para cada tipo de salida.

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
- El router falló dos casos del benchmark: las reglas mandan "¿Explica que es la exposición crediticia?" a `tools`, y el modelo manda "¿Puedo liberar el pedido?" a `tools` aunque no tiene cliente ni SKU. Por qué ocurrió cada uno: `EVIDENCIAS.md` 1.6.
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

En `EVIDENCIAS.md`:

- 1.6: benchmark de 12 casos con los tres routers, errores y caso de baja confianza.
- 2.1: 3 consultas RAG, incluida una que no usa RAG.
- 2.2: 3 consultas SQL.
- 2.3: pruebas de tools.

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

- `interrupt()` pasó al Hito 4 y el State quedó con campos explícitos, por los problemas 4 y 5 de "Qué falló".
- Los nodos se nombraron según los pasos de un analista de crédito (validar pedido, consultar perfil de crédito, calcular exposición, evaluar, revisión de Finanzas, emitir resultado) en lugar de nombres genéricos.

### Evidencia

En `EVIDENCIAS.md`:

- A.3: diagrama del workflow.
- 2.4: ejecución reproducible de la ruta directa y las otras salidas del workflow.
- A.4: explicación de cada campo del State.

### Preguntas de razonamiento

**¿Por qué no basta una cadena de if/else en este caso?**
Las reglas sí son if/else, y viven en `rules.py`. Lo que el workflow agrega es el proceso alrededor: pasos con naturaleza distinta (un LLM, un servicio externo, cálculos, una decisión), un camino que se corta antes cuando el pedido no es válido, y un punto donde el proceso espera a una persona. En el Hito 4 ese punto tiene que poder pausarse, guardar el estado y continuar después; una cadena de if/else no puede detenerse a esperar y retomar donde quedó.

**¿Qué información necesita sobrevivir de un nodo a otro?**
Los datos del pedido (cliente, SKU, cantidad y monto), los datos de crédito con los que se decidió (estado, límite, exposición, disponible y proyectada), y la decisión con sus motivos. Si el pedido va a Finanzas, todo eso es lo que forma el memo: la persona tiene que ver exactamente los valores que usó la regla.

**¿Qué campo del State sería innecesario o peligroso guardar?**
Innecesario: la ficha completa del cliente o del producto. Del producto solo se usa el precio, y la ficha del cliente duplicaría el estado, el límite y la exposición, que ya se guardan aparte. Además ata el workflow a la estructura de `data.py`. Peligroso: la clave de la API o la respuesta cruda del LLM. Desde el Hito 4, el State se guarda en el checkpoint, y cualquier secreto quedaría escrito en la base de datos.

## Hito 4 · Retry, checkpoint y Human-in-the-Loop

### Qué se construyó

- **Checkpoint persistente:** `SqliteSaver` en `data/workflow_checkpoints.db`. Cada paso del workflow queda guardado bajo su `id_hilo`.
- **Retry:** `RetryPolicy` solo en `fetch_credit_profile`, la consulta al servicio de crédito, que es la única dependencia externa. Hasta 3 intentos, espera inicial de 0,2 s que se duplica, y solo ante `TimeoutError` o `ConnectionError`. Con `SIMULATE_CREDIT_TIMEOUT=1`, el primer intento falla a propósito.
- **Pausa humana:** `interrupt()` en `finance_review`, con el memo de crédito como contenido. El flujo queda detenido hasta que Finanzas / crédito responde.
- **Respuesta de Finanzas validada:** contrato `FinanceDecision` con `decision` (`approve` o `reject`), `reviewer` obligatorio y `comment` opcional. Si la respuesta no es válida, el nodo vuelve a pausar con un mensaje de error; nunca aprueba por defecto.
- **Estados finales nuevos:** `released_by_exception` (Finanzas aprobó) y `rejected_by_finance` (Finanzas rechazó).
- **`workflow_demo.py`:** opciones `--thread-id` (el `id_hilo`), `--resume approve|reject`, `--reviewer` y `--comment`. Muestra el log de flujo pausado y, con `--show-state`, el estado persistido.

### Qué falló

**1. Reanudar con un `id_hilo` sin pedido pausado.**
- Qué pasó: lo probé sin ningún control. LangGraph no encontró nada guardado, ignoró la respuesta de Finanzas y arrancó el workflow desde cero con un State vacío. El primer nodo falló con `KeyError: 'request_text'`. La aprobación nunca llegó al pedido que estaba esperando.
- Corrección: el demo solo reanuda si el `id_hilo` está detenido en `finance_review`. Si no, responde `No paused release found for id_hilo '...'. Nothing to resume.`
- El primer control que escribí solo revisaba si había algún paso pendiente. Falló con el `id_hilo` de la prueba anterior, porque el intento fallido había dejado guardado un paso pendiente en `extract_request`. Lo corregí para que revise específicamente `finance_review`.

**2. Nueva solicitud sobre un `id_hilo` con un pedido pausado.**
- Qué pasó: pausé "9 KRN-900X para C-1003" y envié "6 TTN-M40 para C-1010" con el mismo `id_hilo`. El workflow arrancó de nuevo y el pedido que esperaba a Finanzas pasó a ser el de C-1010. El de C-1003 se perdió sin aviso.
- Qué hubiera pasado en producción: una excepción de crédito pendiente desaparece por un error al escribir el `id_hilo`.
- Corrección: si el `id_hilo` tiene un pedido esperando a Finanzas, el demo no inicia una solicitud nueva y pide reanudarlo o usar otro `id_hilo`.

**3. Servicio de crédito caído en todos los intentos.**
- Qué pasó: el retry hizo los 3 intentos y luego el `TimeoutError` llegó sin capturar, así que el demo terminaba con un traceback.
- Corrección: el demo captura el error y responde que el servicio no está disponible y que el pedido quedó guardado en su `id_hilo`. El checkpoint confirma que el pedido quedó en `fetch_credit_profile`.

**4. Respuesta de Finanzas sin validar.**
- Qué hubiera pasado: si la respuesta se interpretara como verdadero o falso, un texto como "no" contaría como aprobado, porque en Python todo texto no vacío es verdadero. Se liberaría un pedido que Finanzas quiso rechazar.
- Corrección: el contrato `FinanceDecision` solo acepta `approve` o `reject`. La prueba `test_invalid_finance_answer_pauses_again` envía `"no"` y comprueba que el flujo vuelve a pausar.

### Qué aprendí

- Retry y reglas de negocio son cosas distintas. El retry tiene sentido cuando repetir puede dar otro resultado (un servicio que se recupera). Una regla da siempre el mismo resultado con los mismos datos, así que repetirla no sirve.
- Con checkpoint, el `id_hilo` es la identidad del pedido. Equivocarse de `id_hilo` no es un detalle: puede reanudar el pedido equivocado o perder uno pendiente.
- Al reanudar, el nodo con la pausa se ejecuta otra vez desde el inicio. Todo lo que hay antes de `interrupt()` tiene que poder repetirse sin efectos.

### Qué decisión cambió después de probar

- Agregué los dos controles de `id_hilo` después de ver, probándolo, que LangGraph no protege esos casos (problemas 1 y 2 de "Qué falló").
- Se descartó agregar una opción para continuar un pedido que quedó detenido por el servicio de crédito; el demo solo informa que quedó guardado.

### Evidencia

En `EVIDENCIAS.md`:

- 1.5: log de flujo pausado, reanudación aprobada y rechazada con el mismo `id_hilo`, y controles de `id_hilo`.
- 1.3: fallo transitorio provocado con retry, y servicio caído en los 3 intentos.
- 1.4: regla de negocio rechazada sin retry.
- A.4: campos nuevos del State (`finance_decision`, `reviewer`, `finance_comment`).

### Preguntas de razonamiento

**¿Qué error merece retry y cuál no?**
Merece retry un error técnico transitorio del servicio de crédito, como un `TimeoutError` o un `ConnectionError`: el servicio puede recuperarse y el segundo intento puede funcionar. No merecen retry las reglas de negocio (stock insuficiente, cliente en hold, línea insuficiente, monto de revisión), los datos faltantes ni una respuesta inválida de Finanzas. Con los mismos datos dan siempre el mismo resultado, y reintentarlas solo gasta tiempo. Por eso el `RetryPolicy` está en un único nodo y solo para esos dos tipos de error.

**¿Qué se pierde si no existe checkpoint?**
El pedido que espera a Finanzas. La revisión puede tardar horas, y sin checkpoint el estado (monto, exposición, motivos) vive solo en la memoria del proceso: si el proceso termina, se pierde. Además no se puede reanudar: sin checkpoint, LangGraph rechaza la reanudación con `RuntimeError: Cannot use Command(resume=...) without checkpointer`. Habría que empezar de nuevo, volver a llamar al LLM y al servicio de crédito, y los datos podrían haber cambiado respecto de lo que vio Finanzas. Lo mismo pasa si el servicio de crédito falla en los 3 intentos: con checkpoint, el pedido queda guardado en el nodo que falló.

**¿Por qué un side effect antes de `interrupt()` puede ser peligroso?**
Porque al reanudar, el nodo se vuelve a ejecutar desde el principio, y en este diseño puede ejecutarse varias veces más si Finanzas envía una respuesta inválida. Si antes de la pausa se enviara un aviso a Finanzas o se sumara el pedido a la exposición del cliente, eso ocurriría dos o tres veces: avisos duplicados o una exposición inflada. Por eso `finance_review` solo arma el memo antes de pausar, que es un cálculo sin efectos.

**¿Qué pasa si se reanuda con otro `id_hilo`?**
LangGraph no encuentra nada guardado en ese `id_hilo`: ignora la respuesta de Finanzas, arranca el workflow desde cero y falla en el primer nodo. El pedido real sigue pausado en su propio `id_hilo`, sin respuesta. Y en el caso inverso, una solicitud nueva en el `id_hilo` de un pedido pausado lo reemplaza. Lo probé (problemas 1 y 2 de "Qué falló"), y por eso `release_runner.py` controla ambos casos antes de ejecutar.

## Hito 5 · MCP: desacoplar capacidades

### Qué se construyó

- `mcp_server.py`: servidor MCP por stdio con capacidades de solo lectura.
  - 4 tools: `get_customer_credit` (estado, límite, exposición y línea disponible), `get_stock`, `calculate_release` (decisión de liberación, sin aprobar nada) y `sales_summary` (SQL parametrizado con filtros de SKU, cliente y año).
  - 2 resources: `policy://credit` y `policy://release`, con las políticas de `docs/`.
- `mcp_client_demo.py`: cliente MCP sin LLM. Lista tools y resources, llama a tres tools y lee una política.
- `mcp_agent.py`: agente conectado al mismo servidor, con el modelo del proyecto. Responde una consulta compuesta usando varias tools.
- `sales.py`: la consulta de ventas salió de `tools.py` a una función compartida. La usan el agente del Hito 2 y el servidor MCP, así que hay una sola consulta SQL.
- `tests/test_mcp.py`: 6 pruebas que levantan el servidor real por stdio y lo consultan con un cliente sin LLM.

Lo que el servidor **no** expone, y por qué, está en `DECISIONES.md` (decisión 7).

### Qué falló

**1. Resultados sin formato estructurado.**
- Qué pasó: con las tools declaradas sin opciones, el servidor devolvía el resultado solo como texto JSON y `structured_content` llegaba vacío (`None`). Fallaron 4 de las 6 pruebas de MCP con `TypeError: 'NoneType' object is not subscriptable`.
- Qué hubiera pasado: el cliente y el agente tendrían que interpretar texto en vez de recibir campos, y cualquier cambio en el formato del texto rompería a los consumidores.
- Corrección: cada tool se declara con `structured_output=True`.

**2. El servidor no arrancaba.**
- Qué pasó: con ese cambio, el servidor se cerraba al iniciar con `InvalidSignature: Function get_customer_credit: return type <class 'dict'> is not serializable for structured output`. Las pruebas fallaban con `MCPError` de conexión, porque el proceso del servidor moría antes de responder.
- Corrección: el tipo de retorno pasó de `dict` a `dict[str, Any]`, que es lo que exige esta versión del SDK (MCP 2.3.0) para la salida estructurada.

### Qué aprendí

- Antes de MCP, cualquier aplicación que quisiera saber si un pedido se libera tenía que importar los módulos de Python del proyecto. Con MCP, la capacidad tiene un contrato (nombre, argumentos y resultado) y cualquier consumidor la usa sin conocer el código.
- El mínimo privilegio se decide por capacidad, no por archivo: el servidor puede usar `rules.py` completo, pero solo expone la decisión, no la aprobación.
- Con stdio, el servidor no puede imprimir nada en la salida estándar, porque esa salida es el canal del protocolo.

### Qué decisión cambió después de probar

- Tools declaradas con salida estructurada y tipo `dict[str, Any]`, después de los dos fallos anteriores.
- Antes de construir, se descartó publicar los parámetros de la semilla como resource, por el riesgo de que alguien divida pedidos para quedar bajo el monto de revisión.

### Evidencia

En `EVIDENCIAS.md`:

- 2.5: `list_tools` + `call_tool` sin LLM, y pruebas del servidor por stdio.
- 2.6: misma capacidad usada luego por el agente, con una consulta compuesta.
- A.5: diagrama antes y después de MCP.

### Preguntas de razonamiento

**¿Qué problema de acoplamiento existe antes de MCP?**
Antes, el agente del Hito 2 y el workflow importan directamente `data.py`, `rules.py` y la base de ventas. Cualquier otra aplicación que quisiera la misma decisión de crédito (por ejemplo, un tablero de Finanzas) tendría que importar esos mismos archivos, usar el mismo lenguaje y depender de su estructura interna. Si cambia un nombre de función o un campo de `data.py`, se rompen todos los consumidores. Con MCP, los consumidores dependen del contrato de las tools, no del código.

**¿Por qué no deberíamos exponer `ejecutar_sql(sql)`?**
Porque el consumidor decidiría la consulta completa: podría leer cualquier tabla, modificar datos o borrarlos, y si el consumidor es un agente, el SQL lo escribiría un LLM. Además ya no habría un contrato: cada consumidor dependería de cómo están hechas las tablas. `sales_summary` expone una sola consulta fija y parametrizada; el consumidor solo elige los filtros.

**¿Qué capacidad NO expondrías por MCP y por qué?**
La aprobación de excepciones de crédito. Es una decisión que corresponde a Finanzas / crédito, y en el diseño ocurre dentro del workflow con pausa y `id_hilo`. Expuesta como tool, cualquier cliente MCP, incluido un agente, podría liberar un pedido de un cliente en hold o sin línea. `calculate_release` dice qué se debe hacer con el pedido, pero no lo aprueba.

**¿Qué gana otra aplicación al consumir el mismo servidor?**
Obtiene exactamente la misma decisión, con las mismas reglas y los mismos motivos, sin copiar código. Se comprobó: el cliente sin LLM y el agente obtienen `REVIEW` para 9 KRN-900X de C-1003, con los mismos dos motivos. Si mañana cambia una regla en `rules.py`, todos los consumidores la reciben a la vez.

## Hito 6 · Integración y reflexión

### Qué se construyó

- **Ruta `release` en el router:** "Libera…" con cliente y SKU ya no va a la ruta `tools`, sino al workflow de liberación (reglas, retry, pausa para Finanzas e `id_hilo`). El router tiene 6 destinos: `rag`, `sql`, `tools`, `release`, `direct` y `clarify`.
- **MCP dentro del flujo principal:** las rutas `tools` y `sql` del agente consumen el servidor MCP. Cada ruta ve solo sus tools: `sql` solo `sales_summary`; `tools` solo `get_customer_credit` y `get_stock`.
- **Contexto para Finanzas:** nuevo nodo `gather_review_context` antes de la pausa. Agrega al memo el historial de ventas del cliente (SQL) y las secciones de política aplicables (RAG). Es informativo: la decisión ya la tomaron las reglas y no cambia.
- **Fuentes en la respuesta final:** el mensaje de un pedido revisado por Finanzas cita `[RULES:rules.py]`, `[SQL:sales]` y las secciones `[RAG:...]` usadas.
- **`release_runner.py`:** los controles de `id_hilo` y de servicio caído, compartidos por `main.py`, `workflow_demo.py` y el caso end-to-end.
- **`main.py` como punto de entrada único:** recibe la consulta, la enruta, y responde con el agente o ejecuta el workflow. Acepta `--thread-id` y `--resume approve|reject`.
- **`e2e_demo.py`:** caso completo reproducible para C-1003: política (RAG), facturación (SQL por MCP), línea y stock (MCP), liberación con pausa y reanudación aprobada.

### Qué falló

**1. El workflow no se podía ejecutar desde `main.py`.**
- Qué pasó: la primera ejecución del caso end-to-end falló en el paso de liberación con `RuntimeError: AgentRunner.run_sync() cannot be called when an event loop is already running`. El workflow es síncrono (su extractor usa `Runner.run_sync`) y `main.py` es asíncrono.
- Corrección: `main.py` ejecuta el workflow en un hilo aparte con `asyncio.to_thread`.

**2. Aviso de Windows al terminar el caso end-to-end (sin resolver).**
- Qué pasa: al final aparece `Cancelling an overlapped future failed ... OSError: [WinError 6] Controlador no válido`.
- Lo que se comprobó: sale después de que todo terminó correctamente, y el programa finaliza con código 0. No aparece con una sola conexión MCP, ni al abrir y cerrar dos conexiones sin LLM. Una pausa al cerrar cada conexión no lo eliminó y se revirtió.
- Queda como limitación conocida: es un aviso del cierre de procesos en Windows y no afecta los resultados.

**3. El RAG a veces cita solo el título de la política.**
- Qué pasa: en una ejecución, una de las fuentes fue `[RAG:credit_policy.md#Política de crédito]`, que es solo el título del documento. La división por secciones deja el título como un fragmento propio.
- Queda como limitación: no cambia ninguna decisión, pero agrega una fuente poco útil al memo.

### Qué aprendí

- Integrar no es solo llamar a cada pieza: aparecieron problemas que no existían por separado, como mezclar código síncrono y asíncrono.
- Que el router decida cuándo empieza el workflow mantiene esa decisión en un lugar que se evalúa con el benchmark. Si `main.py` detectara "libera" por su cuenta, la decisión quedaría fuera de toda prueba.
- El LLM no es estable: con la misma consulta y el mismo modelo, el router por modelo mandó "¿Puedo liberar el pedido?" a `tools` en el Hito 2 y a `clarify` en el Hito 6. Las reglas dieron siempre el mismo resultado.

### Qué decisión cambió después de probar

- La liberación pasó de la ruta `tools` (que solo calculaba la decisión) a una ruta propia que ejecuta el workflow con pausa real.
- La ruta `tools` del agente dejó de tener `calculate_release`: consultar el estado y liberar un pedido son caminos distintos.
- El workflow se ejecuta en un hilo aparte, después del error con el event loop.

### Evidencia

- `EVIDENCIAS.md` A.6: caso completo reproducible.
- `EVIDENCIAS.md` 1.6, 1.5 y 2.6: benchmark con la ruta `release`, liberación y reanudación desde `main.py`, y filtro de tools MCP por ruta.
- `EVIDENCIAS.md` A.3: diagrama del workflow integrado.
- `DECISIONES.md`, `USO_IA.md` y `VIDEO_LINK.txt`.

### Limitaciones

| Limitación | Efecto |
|---|---|
| Datos en memoria y SQLite local | No hay conexión a un ERP o CRM: stock, clientes y exposición son datos de ejemplo |
| El servicio de crédito es simulado | Lee `data.py`; el fallo transitorio se provoca con una variable de entorno |
| Aprobar una excepción no actualiza la exposición | Un segundo pedido del mismo cliente se evalúa con la exposición anterior |
| Sin usuarios ni permisos | Cualquiera que ejecute `--resume` puede aprobar: el campo `reviewer` registra un nombre, pero no lo verifica |
| Proveedor gratuito con cuota | `gemini-3.1-flash-lite` tiene un límite diario de solicitudes; con la cuota agotada fallan el router por modelo, el agente, el extractor y el RAG |
| Palabras clave del router | Errores con confianza alta, como "exposición crediticia" → `tools`, que el híbrido no corrige |
| RAG por secciones | Puede citar el título del documento como fuente (ver "Qué falló") |
| Aviso de Windows al cerrar | Aparece al final del caso end-to-end; no afecta los resultados |

### Riesgos

| Riesgo | Por qué importa | Mitigación actual |
|---|---|---|
| Aprobaciones sin autenticación | En crédito, liberar una excepción es la decisión más sensible del proceso | `FinanceDecision` exige `reviewer` y una decisión explícita; falta verificar identidad |
| El LLM extrae un cliente, SKU o cantidad equivocados | Se evaluaría un pedido distinto del pedido real | Cliente y SKU se validan contra los datos; si faltan, el flujo se bloquea. Una cantidad mal leída sí pasaría |
| Equivocarse de `id_hilo` | Se reanuda el pedido equivocado o se reemplaza uno pendiente | `release_runner.py` controla los dos casos |
| Dependencia de un proveedor externo | Sin el LLM no se puede iniciar una liberación | El retry solo cubre el servicio de crédito, no al proveedor del LLM |

### Preguntas de razonamiento

**¿Qué parte es probabilística y qué parte determinista?**
Probabilístico: el router por modelo (cuando las reglas dudan), la extracción de cliente, SKU y cantidad en el workflow, la búsqueda semántica del RAG y la redacción de las respuestas del agente. Determinista: el router por reglas, las reglas de liberación (`rules.py`), los cálculos de exposición, la consulta SQL, las aristas condicionales del workflow, el retry y la validación de la respuesta de Finanzas. La decisión de liberar, revisar o rechazar es siempre determinista; el LLM solo interpreta la solicitud y redacta.

**¿Qué cambiaría si esto operara con SAP/ERP/CRM reales?**
`data.py` y `business.db` se reemplazarían por consultas al ERP (stock, maestro de clientes, exposición desde cuentas por cobrar), y `fetch_credit_profile` llamaría al módulo de crédito real; ahí el retry deja de ser una simulación. Aprobar una excepción tendría que registrar la liberación en el ERP con una escritura idempotente después de la pausa, nunca antes. Finanzas aprobaría desde su propia aplicación, con usuarios autenticados, y el servidor MCP necesitaría autorización por tool. El checkpoint pasaría de un archivo SQLite a una base compartida.

**¿Cuál es el mayor riesgo del diseño actual?**
Que cualquier persona que ejecute `--resume approve` libera una excepción de crédito. El sistema registra un nombre de revisor, pero no verifica quién es ni si tiene permiso. Las reglas son correctas y el flujo se pausa donde debe, pero el último control (que decida una persona autorizada) no está protegido.

**¿Qué simplificarías si tuvieras que mantenerlo un año?**
Dejaría un solo camino para las capacidades operacionales: `tools.py` conserva tools locales (producto, stock, cliente, liberación) que el flujo principal ya no usa, porque esas consultas pasan por MCP. También dejaría un solo router (el híbrido) en lugar de tres estrategias configurables, y revisaría las palabras clave con los errores registrados en el benchmark.
