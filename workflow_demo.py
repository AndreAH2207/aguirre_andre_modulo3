import argparse
from pprint import pprint

from dotenv import load_dotenv
from langchain_core.runnables.graph import NodeStyles

# Load .env before importing release_workflow, which builds the agent with build_model().
load_dotenv()

from langgraph.types import Command

from case_config import print_parameters
from release_workflow import graph

# Dark boxes, light blue borders, white text.
DIAGRAM_STYLES = NodeStyles(
    default="fill:#1e293b,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
    first="fill:#0f172a,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
    last="fill:#0f172a,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
)


def read_arguments():
    parser = argparse.ArgumentParser(description="Demo: LangGraph sale release workflow")
    parser.add_argument("--thread-id", default="release-001", help="id_hilo of the release process")
    parser.add_argument("--request", default="Libera 4 KRN-900X para C-1003")
    parser.add_argument("--resume", choices=["approve", "reject"], help="Finance answer for a paused release")
    parser.add_argument("--reviewer", default="finance-demo")
    parser.add_argument("--comment")
    parser.add_argument("--show-state", action="store_true")
    parser.add_argument("--diagram", action="store_true", help="Print the workflow as a Mermaid diagram")
    return parser.parse_args()


def print_result(result: dict) -> None:
    # __interrupt__ is a LangGraph key: the flow is paused waiting for Finance.
    interrupts = result.get("__interrupt__", ())
    if interrupts:
        print("\n=== FLOW PAUSED: WAITING FOR FINANCE / CREDIT ===")
        for item in interrupts:
            pprint(getattr(item, "value", item), sort_dicts=False)
        print("\nResume with the SAME --thread-id and --resume approve|reject")
        return

    print("\n=== WORKFLOW FINISHED ===")
    print(result.get("message", "No final message"))
    print("status:", result.get("status"))


def main() -> None:
    arguments = read_arguments()

    if arguments.diagram:
        print(graph.get_graph().draw_mermaid(node_colors=DIAGRAM_STYLES))
        return

    print_parameters()
    # "configurable" and "thread_id" are LangGraph keys; thread_id is the id_hilo.
    config = {"configurable": {"thread_id": arguments.thread_id}}
    print(f"id_hilo: {arguments.thread_id}")

    waiting_for_finance = "finance_review" in graph.get_state(config).next

    if arguments.resume:
        # Without a paused flow in this id_hilo there is nothing to resume: LangGraph would
        # start the graph from scratch with an empty state and ignore the Finance answer.
        if not waiting_for_finance:
            print(f"\nNo paused release found for id_hilo '{arguments.thread_id}'. Nothing to resume.")
            return
        finance_answer = {
            "decision": arguments.resume,
            "reviewer": arguments.reviewer,
            "comment": arguments.comment,
        }
        print(f"Resuming with Finance answer: {finance_answer}")
        workflow_input = Command(resume=finance_answer)
    else:
        # A new request on a paused id_hilo would replace the order waiting for Finance.
        if waiting_for_finance:
            print(
                f"\nid_hilo '{arguments.thread_id}' has an order waiting for Finance. "
                "Resume it with --resume approve|reject or use another --thread-id."
            )
            return
        workflow_input = {"request_text": arguments.request}

    try:
        result = graph.invoke(workflow_input, config=config)
    except (TimeoutError, ConnectionError):
        # RetryPolicy already retried; the checkpoint keeps the order at the failed node.
        print(
            "\nCredit service unavailable after 3 attempts. "
            f"The order is saved in id_hilo '{arguments.thread_id}'; try again later."
        )
        return

    print_result(result)

    if arguments.show_state:
        snapshot = graph.get_state(config)
        print("\n=== PERSISTED STATE ===")
        pprint(snapshot.values, sort_dicts=False)
        print("next:", snapshot.next)


if __name__ == "__main__":
    main()
