# Decisiones de diseño

Caso **CRE-008** · Variante **Crédito** · Semilla **2135**

Cada decisión incluye: el problema, las alternativas consideradas, la decisión tomada, su trade-off, el riesgo que queda y qué cambiaría en producción.

## 1. Router híbrido

**Problema.** Cada solicitud debe llegar a la capacidad correcta (política, historial, estado actual, liberación, respuesta directa o aclaración) sin enviarla a todas las herramientas.

**Alternativas.**
- Solo reglas por palabras clave: instantáneo, gratis y auditable, pero se equivoca con preguntas que no calzan con las palabras.
- Solo modelo: entiende mejor el significado, pero cada consulta cuesta una llamada y tarda.
- Híbrido: reglas primero, y el modelo solo cuando las reglas tienen confianza menor a 0,90.

**Decisión.** Router híbrido (`ROUTER_STRATEGY=hybrid`), con 6 destinos: `rag`, `sql`, `tools`, `release`, `direct` y `clarify`.

**Trade-off.** En el benchmark de 12 casos, el híbrido tardó 2,31 s frente a 14,29 s del modelo solo (con `gemini-3.1-flash-lite`), y el modelo solo se consulta cuando las reglas dudan. A cambio, hereda los errores de las reglas cuando estas están seguras: "¿Explica que es la exposición crediticia?" va a `tools` con confianza 0,92 y el modelo nunca se consulta.

**Riesgo.** Una regla equivocada con confianza alta no se revisa. Además, la ruta `release` inicia un proceso con efectos sobre la decisión de crédito, y la decide una palabra clave ("libera").

**En producción.** Revisar las palabras clave con los errores registrados, bajar la confianza de las reglas que fallan para que pasen al modelo, y medir el router con un benchmark más grande y periódico.

## 2. Reglas de crédito en Python, no en el LLM

**Problema.** La decisión de liberar, enviar a revisión o rechazar compara números: exposición más pedido contra el límite, pedido contra el monto de revisión, cantidad contra stock.

**Alternativas.**
- Que el LLM decida con las políticas en el prompt.
- Reglas en Python, y el LLM solo para entender la solicitud.

**Decisión.** Las reglas viven en `rules.py` (`validate_order` y `evaluate_release`). La tool, el workflow y el servidor MCP llaman a las mismas funciones. El LLM solo extrae cliente, SKU y cantidad, y redacta respuestas.

**Trade-off.** Las reglas siempre dan el mismo resultado y se prueban sin API. A cambio, cualquier criterio nuevo requiere cambiar código: el sistema no "entiende" una política nueva solo por escribirla en `docs/`.

**Riesgo.** Si la política escrita y `rules.py` dejan de coincidir, el RAG citaría una regla distinta de la que se aplica. Por eso la política no escribe la cifra del monto de revisión, que vive solo en `case_config.py`.

**En producción.** Las reglas se mantendrían versionadas con la política, con pruebas que comprueben que ambas dicen lo mismo, y los umbrales vendrían de la configuración del ERP.

## 3. Stock como precondición y hold como excepción para Finanzas

**Problema.** Hay que decidir qué casos se rechazan directamente y cuáles pasan a una persona.

**Alternativas.**
- Rechazar directamente a un cliente en hold.
- Enviar el hold a Finanzas, como indica el enunciado ("Cliente en hold / línea insuficiente", con aprobación de Finanzas / crédito).
- Revisar el stock como parte de la evaluación de crédito.

**Decisión.** Cliente o SKU inexistente y stock insuficiente se rechazan en `validate_order`, antes de consultar el crédito. Hold, línea insuficiente y monto de revisión pasan a Finanzas, y los motivos se acumulan.

**Trade-off.** Un pedido sin stock nunca consulta el servicio de crédito (una llamada menos y nada que reintentar). A cambio, Finanzas podría aprobar un pedido de un cliente en hold.

**Riesgo.** Que Finanzas apruebe excepciones a clientes en hold sin un control adicional.

**En producción.** Un cliente en hold requeriría una aprobación de mayor nivel, o al menos un comentario obligatorio, y el stock se consultaría al módulo de inventario del ERP.

## 4. State explícito y pequeño

**Problema.** El workflow necesita que ciertos datos pasen de un nodo a otro y queden guardados mientras el pedido espera a Finanzas.

**Alternativas.**
- Guardar en el State las fichas completas de cliente y producto.
- Guardar solo los campos que usa la decisión.

**Decisión.** El State tiene campos explícitos: pedido, datos de crédito con los que se decidió, decisión con motivos, contexto para Finanzas, respuesta de Finanzas y estado. No guarda fichas completas.

**Trade-off.** El State es fácil de explicar y no depende de la estructura de `data.py`. A cambio, si un nodo nuevo necesita otro dato, hay que agregar el campo explícitamente.

**Riesgo.** Los valores guardados son los del momento de la evaluación. Si la exposición del cliente cambia mientras el pedido espera, Finanzas decide con datos antiguos.

**En producción.** Guardar también la fecha de la evaluación, y volver a consultar la exposición al reanudar para avisar a Finanzas si cambió.

## 5. Retry solo en el servicio de crédito

**Problema.** Hay fallos técnicos que se resuelven solos (un servicio que tarda) y decisiones de negocio que darían lo mismo aunque se repitan.

**Alternativas.**
- Retry en todos los nodos.
- Retry solo en la dependencia externa.

**Decisión.** `RetryPolicy` solo en `fetch_credit_profile`: hasta 3 intentos, solo ante `TimeoutError` o `ConnectionError`. Las reglas no tienen retry. Si el servicio sigue caído, el checkpoint guarda el pedido en ese nodo.

**Trade-off.** El retry solo se aplica donde puede cambiar el resultado. A cambio, los fallos del proveedor del LLM (extractor y RAG) no se reintentan.

**Riesgo.** Una cuota agotada del proveedor detiene la liberación en el primer paso.

**En producción.** Retry con espera para el proveedor del LLM en el extractor, un modelo alternativo de respaldo, y alertas cuando el servicio de crédito agota los reintentos.

## 6. Respuesta de Finanzas validada

**Problema.** Al reanudar, la respuesta de Finanzas controla la rama más crítica del proceso: liberar o no una excepción de crédito.

**Alternativas.**
- Interpretar la respuesta como verdadero o falso.
- Un contrato con decisión explícita (`approve` o `reject`) y, si la respuesta no es válida, rechazar por defecto, lanzar un error o volver a pausar.

**Decisión.** Contrato `FinanceDecision`: `decision` solo acepta `approve` o `reject`, `reviewer` es obligatorio y `comment` es opcional. Una respuesta inválida vuelve a pausar el flujo con el error.

**Trade-off.** Nunca se aprueba por error (un texto como "no" no cuenta como aprobado) y el pedido no se pierde. A cambio, el nodo de pausa tiene un bucle y se ejecuta de nuevo en cada reanudación.

**Riesgo.** `reviewer` es un nombre escrito, no un usuario verificado: cualquiera que ejecute `--resume` puede aprobar.

**En producción.** Autenticar a quien aprueba, verificar su permiso para el monto y el tipo de excepción, y registrar la aprobación en el ERP.

## 7. MCP con mínimo privilegio

**Problema.** Otras aplicaciones necesitan las mismas capacidades de crédito sin importar el código del proyecto.

**Alternativas.**
- Exponer todo, incluido SQL libre y la aprobación de excepciones.
- Exponer solo capacidades de lectura.

**Decisión.** El servidor MCP expone 4 tools de solo lectura (`get_customer_credit`, `get_stock`, `calculate_release`, `sales_summary`) y 2 resources de política. En el flujo principal, cada ruta del agente ve solo sus tools. Lo que no se expone, a propósito:

| Capacidad | Por qué no |
|---|---|
| SQL libre (`ejecutar_sql(sql)`) | Cualquier consumidor podría leer, modificar o borrar toda la base |
| Aprobar o rechazar excepciones de crédito | Es la decisión de Finanzas / crédito dentro del workflow. Expuesta, cualquier cliente MCP podría liberar un pedido |
| Fichas completas de clientes | `get_customer_credit` entrega solo los datos de crédito, no la ficha (por ejemplo, no el nombre) |
| Escrituras (cambiar stock o exposición) | Ningún consumidor necesita escribir para decidir una liberación |
| Parámetros de la semilla, como resource | Publicaría el monto de revisión: quien lo conozca podría dividir un pedido grande en varios menores para evitar la revisión. El límite y la exposición ya se obtienen por cliente con `get_customer_credit` |

**Trade-off.** Un consumidor no puede dañar datos ni liberar pedidos. A cambio, para aprobar una excepción hay que pasar por el workflow; ninguna otra aplicación puede hacerlo por MCP.

**Riesgo.** El servidor no autentica a sus clientes: quien pueda ejecutarlo puede leer el crédito de cualquier cliente.

**En producción.** Autorización por tool y por cliente, registro de cada llamada y transporte con autenticación.
