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
