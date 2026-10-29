import asyncio
import json

from agents import RunContextWrapper
from agents.decorators import tool
from agents.tool_context import ToolContext

import rules
import sales
from context import AppContext
from data import PRODUCTS,STOCK,CUSTOMERS
from rag import search as rag_search


def _error(kind:str,message:str)->dict:
    return {"ok":False,"error_type":kind,"message":message,"recoverable":True}


@tool
async def get_product(ctx:RunContextWrapper[AppContext],sku:str)->dict:
    """Consulta un producto por SKU."""
    await asyncio.sleep(0)
    item=PRODUCTS.get(sku.upper())
    return {"ok":True,"product":item} if item else _error("not_found","SKU no encontrado")


@tool
async def get_stock(ctx:RunContextWrapper[AppContext],sku:str)->dict:
    """Consulta stock disponible por SKU."""
    await asyncio.sleep(0)
    sku=sku.upper()
    return {"ok":True,"sku":sku,"available_units":STOCK[sku]} if sku in STOCK else _error("not_found","Stock no encontrado")


@tool
async def get_customer(ctx:RunContextWrapper[AppContext],customer_id:str)->dict:
    """Consulta un cliente: estado de credito, limite, exposicion actual y linea disponible."""
    await asyncio.sleep(0)
    item=CUSTOMERS.get(customer_id.upper())
    if not item: return _error("not_found","Cliente no encontrado")
    available=round(item["credit_limit_usd"]-item["current_exposure_usd"],2)
    return {"ok":True,"customer":item,"available_credit_usd":available}


@tool
async def calculate_release(ctx:RunContextWrapper[AppContext],customer_id:str,sku:str,quantity:int)->dict:
    """Decide si un pedido se libera (RELEASE), pasa a Finanzas (REVIEW) o se rechaza (REJECT)."""
    await asyncio.sleep(0)
    return rules.calculate_release(customer_id,sku,quantity)


# SQL como capacidad: consulta fija y parametrizada; el LLM solo elige los filtros.
@tool
async def sales_summary(
    ctx:RunContextWrapper[AppContext],
    sku:str|None=None,
    customer_id:str|None=None,
    year:int|None=None,
)->dict:
    """Resume ventas historicas, filtrando opcionalmente por SKU, cliente y/o anio."""
    await asyncio.sleep(0)
    return sales.sales_summary(sku,customer_id,year)


# RAG como capacidad.
@tool
async def search_policies(
    ctx:RunContextWrapper[AppContext],
    query:str,
    top_k:int=3,
)->dict:
    """Busca politicas internas de credito y liberacion mediante recuperacion semantica."""
    await asyncio.sleep(0)
    return {"ok":True,"query":query,"results":rag_search(query,top_k)}


TOOLS=[get_product,get_stock,get_customer,calculate_release,sales_summary,search_policies]
SCHEMAS=[{"type":"function","name":t.name,"description":t.description,"parameters":t.params_json_schema,"strict":t.strict_json_schema} for t in TOOLS]
_REGISTRY={t.name:t for t in TOOLS}


def execute(name:str,arguments:str,request_id:str="manual-loop")->str:
    """Ejecuta una tool por nombre con argumentos JSON y devuelve JSON."""
    item=_REGISTRY.get(name)
    if item is None: return json.dumps(_error("unknown_tool",f"Tool no registrada: {name}"),ensure_ascii=False)
    ctx=ToolContext(context=AppContext(request_id),tool_name=name,tool_call_id=f"manual-{name}",tool_arguments=arguments)
    result=asyncio.run(item.on_invoke_tool(ctx,arguments))
    return result if isinstance(result,str) else json.dumps(result,ensure_ascii=False)
