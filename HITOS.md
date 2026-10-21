# Hitos

Caso **CRE-008** · Variante **Crédito** · Semilla **2135**

## Hito 1 · Comprender y separar responsabilidades

### Qué se construyó

- `case_config.py`: CASO_ID, semilla y los tres parámetros de crédito. Se sortean en orden fijo con `random.Random(2135)`: límite de crédito (30 000), exposición actual (10 000) y monto de revisión (15 000). Se imprimen al ejecutar el archivo.
- `data.py`: clientes, productos e inventario. C-1003 toma su límite y exposición de la semilla; C-1010 y C-9999 tienen valores fijos.
- `bootstrap_db.py`: crea `data/business.db` con 9 ventas históricas en la tabla `sales`.
- `rules.py`: la función `calculate_release(customer_id, sku, quantity)` decide si un pedido se libera (`RELEASE`), pasa a Finanzas (`REVIEW`) o se rechaza (`REJECT`). Orden de evaluación: existencia → stock → hold → línea → monto de revisión. Las causas de revisión se juntan en `reasons`.
- `main.py`: punto de entrada, como en clase. Imprime CASO_ID, semilla y parámetros, crea la base si no existe, pide cliente, SKU y cantidad, y muestra la decisión de `calculate_release`. Todavía no usa LLM, por eso pide los datos por separado en vez de una pregunta en lenguaje natural.
- `pyproject.toml` y `.env.example` con el formato de clase. Por ahora no hay dependencias, porque el Hito 1 usa solo Python estándar.
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
- Cliente en hold: al principio lo trataba como rechazo directo, igual que el código de clase. Lo cambié a revisión de Finanzas, porque el enunciado (sección 04, fila D) lo pone como excepción con aprobación humana.
- Los datos estaban en archivos JSON; los pasé a diccionarios en `data.py`, como en el código de clase. La carpeta `data/` queda para la base de ventas.

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

- `router.py`: los tres routers de clase (`DeterministicRouter`, `ModelRouter`, `HybridRouter`) con 5 destinos: `rag`, `sql`, `tools`, `direct` y `clarify`. Se elige con `ROUTER_STRATEGY` en el `.env` (por defecto `hybrid`, umbral 0,90). Las palabras clave se adaptaron a crédito y la consulta se normaliza sin tildes antes de compararla.
- `rag.py` + `docs/`: dos políticas (`credit_policy.md` y `release_policy.md`), divididas por secciones `##`, buscadas con embeddings y citadas con `source_ref`. La política no escribe la cifra del monto de revisión: el valor vive solo en `case_config.py`.
- `tools.py`: seis tools con los nombres de clase: `get_product`, `get_stock`, `get_customer` (con línea disponible), `calculate_release` (llama a `rules.py`), `sales_summary` (SQL parametrizado, con filtros opcionales de SKU, cliente y año) y `search_policies` (RAG).
- `engine.py`: el router elige la ruta y el agente solo recibe las tools de esa ruta. `main.py` ahora recibe una pregunta en lenguaje natural, como en clase.
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

- Proveedor: de OpenAI (como en clase) a Gemini con tier gratuito, usando la opción `openai_compatible` que ya tenía el `model_factory.py` de clase. Se desactivó el tracing del SDK, que intenta enviar trazas a OpenAI.
- Modelo: de `gemini-3.8-flash` a `gemini-3.1-flash-lite`, por la cuota diaria.
- "hold" pasó de palabra clave de RAG a palabra clave de tools: "¿C-9999 está en hold?" pregunta por el estado actual del cliente, no por la política.
- `uv.lock` se excluyó del repositorio, como en clase, y se acotaron los rangos de versiones en `pyproject.toml`.

### Evidencia

En `EVIDENCIAS.md`, sección Hito 2: benchmark de los tres routers, errores del router explicados, 3 pruebas RAG (incluida una que no usa RAG), 3 SQL, 3 tools y ejecuciones del agente de punta a punta.

### Preguntas de razonamiento

**¿Por qué una consulta de ventas históricas no debería resolverse con RAG?**
Porque la respuesta es un cálculo sobre muchas filas (sumar montos, contar ventas), no un párrafo que se pueda recuperar. RAG trae los textos más parecidos a la pregunta; no suma ni filtra por cliente o año. Con SQL el resultado es exacto y siempre el mismo: "¿Cuánto le hemos facturado a C-1003 en 2026?" da 28 559,80 desde `sales_summary`.

**¿Qué ocurre si el router tiene baja confianza?**
En el router híbrido, si la regla devuelve una confianza menor a 0,90, la decisión pasa al modelo. Pasa con "¿Por qué las empresas B2B venden a plazo?": ninguna regla aplica, queda en `direct` con 0,55 y el modelo confirma `direct`. El problema es el caso contrario: una regla equivocada pero con confianza alta no se revisa.

**¿Cuál es el costo de enviar toda pregunta a todas las herramientas?**
Más llamadas al modelo y más tokens, porque el agente tiene que decidir entre seis tools en vez de una o cuatro. También más riesgo: con todas disponibles, el agente podría usar RAG para una pregunta de ventas o llamar a `calculate_release` cuando solo se preguntó por stock. Por eso `engine.py` le da a cada ruta solo sus tools (`_tools_for`).
