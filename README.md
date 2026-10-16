# AI Operations Agent · AndesSupply

Trabajo integrador del Módulo 3 (DSRP · AI Engineer).

| CASO_ID | Variante | Semilla |
|---|---|---|
| CRE-008 | Crédito | 2135 |

Proceso: liberación de venta. El sistema decide si un pedido se libera, pasa a revisión de Finanzas o se rechaza, según el stock, el estado de crédito del cliente, su línea disponible y el monto de revisión.

## Requisitos

- Python 3.11 o superior.
- Hito 1: no requiere dependencias externas ni API key.

## Ejecución

Todos los comandos se ejecutan desde esta carpeta.

```bash
# Parámetros generados por la semilla
python case_config.py

# Crear la base de ventas históricas (data/business.db)
python bootstrap_db.py

# Evaluar un pedido (Enter usa el ejemplo C-1003, KRN-900X, 9)
python main.py
```

## Estructura

| Archivo | Contenido |
|---|---|
| `case_config.py` | CASO_ID, semilla y los tres parámetros de crédito |
| `data.py` | Clientes, productos e inventario |
| `bootstrap_db.py` | Crea la tabla `sales` con las ventas históricas |
| `rules.py` | Reglas deterministas de liberación (`calculate_release`) |
| `main.py` | Punto de entrada |
| `HITOS.md` | Avance por hito |
| `EVIDENCIAS.md` | Evidencias de cada hito |
