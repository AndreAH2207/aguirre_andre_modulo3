import asyncio
import os

from dotenv import load_dotenv

# IMPORTANTE: cargar .env ANTES de importar modulos que construyen modelos o clientes.
load_dotenv()

from bootstrap_db import DB_PATH,bootstrap
from case_config import print_parameters
from engine import answer


async def main()->None:
    print_parameters()
    if not DB_PATH.exists():
        bootstrap()

    strategy=os.getenv("ROUTER_STRATEGY","hybrid")
    query=input("\nTu > ").strip() or "Libera 9 KRN-900X para C-1003"

    decision,response=await answer(query,strategy)

    print("\n=== ROUTING ===")
    print(decision.model_dump_json(indent=2))
    print("\n=== RESPONSE ===")
    print(response.model_dump_json(indent=2))


if __name__=="__main__":
    asyncio.run(main())
