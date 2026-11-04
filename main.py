import argparse
import asyncio
import os
import uuid

from dotenv import load_dotenv

# IMPORTANTE: cargar .env ANTES de importar modulos que construyen modelos o clientes.
load_dotenv()

from bootstrap_db import DB_PATH,bootstrap
from case_config import print_parameters
from engine import answer_with_agent,choose_route
from release_runner import print_outcome,resume_release,start_release
from schemas import Route


def read_arguments():
    parser=argparse.ArgumentParser(description="AI Operations Agent: router + agent + release workflow")
    parser.add_argument("query",nargs="*",help="Request in natural language (asked interactively if empty)")
    parser.add_argument("--thread-id",help="id_hilo for a release request (generated if empty)")
    parser.add_argument("--resume",choices=["approve","reject"],help="Finance answer for a paused release")
    parser.add_argument("--reviewer",default="finance-demo")
    parser.add_argument("--comment")
    return parser.parse_args()


async def handle_query(query:str,thread_id:str|None,strategy:str)->None:
    decision=await choose_route(query,strategy)
    print("\n=== ROUTING ===")
    print(decision.model_dump_json(indent=2))

    if decision.route==Route.RELEASE:
        thread_id=thread_id or f"release-{uuid.uuid4().hex[:8]}"
        print(f"\nid_hilo: {thread_id}")
        # The workflow is synchronous (its extractor uses Runner.run_sync), so it runs in a
        # worker thread: run_sync cannot be called from inside a running event loop.
        print_outcome(await asyncio.to_thread(start_release,thread_id,query),thread_id)
        return

    response=await answer_with_agent(query,decision)
    print("\n=== RESPONSE ===")
    print(response.model_dump_json(indent=2))


async def main()->None:
    arguments=read_arguments()
    print_parameters()
    if not DB_PATH.exists():
        bootstrap()

    if arguments.resume:
        if not arguments.thread_id:
            print("\n--resume needs the --thread-id (id_hilo) of the paused release.")
            return
        finance_answer={"decision":arguments.resume,"reviewer":arguments.reviewer,"comment":arguments.comment}
        print(f"\nid_hilo: {arguments.thread_id}")
        print(f"Resuming with Finance answer: {finance_answer}")
        print_outcome(await asyncio.to_thread(resume_release,arguments.thread_id,finance_answer),arguments.thread_id)
        return

    query=" ".join(arguments.query).strip() or input("\nTu > ").strip() or "Libera 9 KRN-900X para C-1003"
    strategy=os.getenv("ROUTER_STRATEGY","hybrid")
    await handle_query(query,arguments.thread_id,strategy)


if __name__=="__main__":
    asyncio.run(main())
