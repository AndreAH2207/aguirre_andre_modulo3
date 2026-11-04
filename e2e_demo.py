"""End-to-end case for C-1003: router + RAG + SQL (MCP) + tools (MCP) + workflow with pause and resume.

Every step goes through the same entry point as main.py (choose_route, then the agent or the
release workflow). The id_hilo is new on every run, so the case can be repeated.
"""

import asyncio
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

from bootstrap_db import bootstrap
from case_config import print_parameters
from main import handle_query
from release_runner import print_outcome, resume_release

STEPS = [
    ("1. Policy (RAG)", "¿Qué dice la política sobre pedidos que superan el monto de revisión?"),
    ("2. Sales history (SQL via MCP)", "¿Cuánto le hemos facturado a C-1003 en 2026?"),
    ("3. Current credit and stock (tools via MCP)", "¿Cuánta línea de crédito disponible tiene C-1003 y cuánto stock hay de KRN-900X?"),
    ("4. Release request (workflow: rules, exception, pause)", "Libera 9 KRN-900X para C-1003"),
]


async def main() -> None:
    print_parameters()
    bootstrap()
    strategy = os.getenv("ROUTER_STRATEGY", "hybrid")
    thread_id = f"e2e-{uuid.uuid4().hex[:8]}"

    for title, query in STEPS:
        print("\n" + "#" * 78)
        print(f"# {title}\n# Query: {query}")
        print("#" * 78)
        await handle_query(query, thread_id, strategy)

    print("\n" + "#" * 78)
    print("# 5. Finance approves the exception (same id_hilo)")
    print("#" * 78)
    finance_answer = {"decision": "approve", "reviewer": "ana.finanzas", "comment": "Buen historial de pago"}
    print(f"id_hilo: {thread_id}")
    print(f"Resuming with Finance answer: {finance_answer}")
    print_outcome(await asyncio.to_thread(resume_release, thread_id, finance_answer), thread_id)


if __name__ == "__main__":
    asyncio.run(main())
