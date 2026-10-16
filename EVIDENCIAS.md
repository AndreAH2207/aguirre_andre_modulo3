# Evidencias

Caso **CRE-008** · Variante **Crédito** · Semilla **2135**

## Hito 1 · Comprender y separar responsabilidades

### Escenario generado por la semilla

```
> python case_config.py
CASO_ID=CRE-008 | VARIANT=Credit | SEMILLA=2135
Main customer: C-1003
  credit limit     : USD 30,000
  current exposure : USD 10,000
Review amount      : USD 15,000
```

Al ejecutarlo dos veces se obtienen los mismos valores. C-1003 tiene 20 000 USD de línea disponible.

### Datos mínimos

| Dato | Dónde está | Contenido |
|---|---|---|
| Clientes | `data.py` → `CUSTOMERS` | C-1003 (caso principal, valores de la semilla), C-1010 (línea holgada: 120 000 / 20 000), C-9999 (en hold) |
| Productos | `data.py` → `PRODUCTS` | KRN-900X, NXS-G10, OPT-V300, CYC-3DX, TTN-M40 |
| Inventario | `data.py` → `STOCK` | 45, 120, 62, 14 y 35 unidades respectivamente |
| Ventas | `data/business.db`, tabla `sales` (se crea con `python bootstrap_db.py`) | 9 ventas de 2026 repartidas entre los 3 clientes |

### Tabla consulta → capacidad esperada → justificación

| # | Consulta | Capacidad esperada | Resultado esperado | Justificación |
|---|---|---|---|---|
| 1 | ¿Qué dice la política sobre venderle a un cliente en hold? | RAG | Cita la política de crédito | Es una regla escrita en un documento. La respuesta tiene que salir del texto de la política y citar la fuente; no es un dato que esté en una tabla. |
| 2 | ¿Quién debe aprobar un pedido que supera el monto de revisión? | RAG | Cita la política de crédito | Pregunta por un procedimiento (quién aprueba), que es información documental. Lo que se necesita es encontrar el párrafo correcto de la política, no calcular nada. |
| 3 | ¿Cuánto le hemos facturado a C-1003 en 2026? | SQL | Total de ventas históricas de C-1003 | Es una suma sobre varias ventas pasadas. El total tiene que salir de una consulta parametrizada a la tabla `sales`; un RAG no suma montos y un LLM podría inventar la cifra. |
| 4 | ¿Cuántas unidades de KRN-900X vendimos este año? | SQL | Unidades agregadas de KRN-900X | Agregación sobre el historial filtrada por SKU. Igual que la 3: dato transaccional que se calcula con SQL. |
| 5 | ¿Cuánto nos debe actualmente C-1003? | Tool | Exposición actual: 10 000 | Parece una pregunta de historia (SQL) por la palabra "debe", pero lo que pide es el saldo de hoy, que es un dato operacional del cliente. Se consulta con una tool del cliente. La dejé a propósito porque es fácil clasificarla mal. |
| 6 | ¿Hay stock de CYC-3DX? | Tool | 14 unidades | El stock cambia con cada venta. Se consulta en el momento con una tool; no puede estar en un documento ni en el prompt. |
| 7 | Libera 4 KRN-900X para C-1003 | Regla | RELEASE | El pedido es 9 802 USD; con la exposición queda en 19 802, bajo el límite de 30 000, y no llega al monto de revisión de 15 000. Son comparaciones de números, así que las resuelve `calculate_release` en Python. |
| 8 | Libera 9 KRN-900X para C-1003 | Regla | REVIEW: insufficient credit line | El pedido es 22 054,50 USD; la exposición quedaría en 32 054,50 y supera el límite de 30 000. La regla lo detecta y el pedido pasa a revisión de Finanzas. Un LLM no debe decidir si 32 054,50 es mayor que 30 000. |
| 9 | Libera 15 CYC-3DX para C-1003 | Regla | REJECT: insufficient stock | Hay 14 unidades y se piden 15. Se rechaza antes de mirar el crédito, porque no tiene sentido pedir aprobación para algo que no se puede despachar. |
| 10 | ¿Puedo liberar el pedido? | Aclaración | Pedir cliente, producto y cantidad | No dice qué cliente, qué producto ni cuántas unidades. Sin esos datos no se puede aplicar ninguna regla, así que lo correcto es preguntar en vez de suponer. |

### Verificación de las reglas

Resultados de `calculate_release` (archivo `rules.py`) con los datos de la semilla:

| Llamada | decision | Motivo |
|---|---|---|
| `calculate_release("C-1003", "KRN-900X", 4)` | RELEASE | — |
| `calculate_release("C-1003", "KRN-900X", 7)` | REVIEW | Pedido de 17 153,50 alcanza el monto de revisión |
| `calculate_release("C-1003", "KRN-900X", 9)` | REVIEW | Línea insuficiente y monto de revisión |
| `calculate_release("C-1003", "CYC-3DX", 15)` | REJECT | Stock insuficiente (14 disponibles) |
| `calculate_release("C-9999", "NXS-G10", 1)` | REVIEW | Cliente en hold |
| `calculate_release("C-1010", "TTN-M40", 6)` | REVIEW | Solo monto de revisión (19 263,60) |
| `calculate_release("C-0000", "KRN-900X", 1)` | error `not_found` | Cliente no encontrado |
| `calculate_release("C-1003", "XXX", 1)` | error `not_found` | SKU no encontrado |
| `calculate_release("C-1003", "KRN-900X", 0)` | error `invalid_quantity` | Cantidad inválida |

### Ejecución de `main.py`

Con Enter en los tres campos se usa el pedido de ejemplo (C-1003, KRN-900X, 9):

```
> python main.py
CASO_ID=CRE-008 | VARIANT=Credit | SEMILLA=2135
Main customer: C-1003
  credit limit     : USD 30,000
  current exposure : USD 10,000
Review amount      : USD 15,000

Customer >
SKU >
Quantity >

=== RELEASE DECISION ===
{
  "ok": true,
  "decision": "REVIEW",
  "order_amount_usd": 22054.5,
  "reasons": [
    "Insufficient credit line: exposure + order = 32,054.50 exceeds limit 30,000.00.",
    "Order of 22,054.50 reaches review amount 15,000.00."
  ]
}
```

Si la cantidad no es un número entero (por ejemplo "abc"), el programa responde `Quantity must be a whole number.` y termina sin evaluar.
