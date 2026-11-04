import argparse
from pprint import pprint

from dotenv import load_dotenv
from langchain_core.runnables.graph import NodeStyles

# Load .env before importing release_workflow, which builds the agent with build_model().
load_dotenv()

from case_config import print_parameters
from release_runner import config_for, print_outcome, resume_release, start_release
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


def main() -> None:
    arguments = read_arguments()

    if arguments.diagram:
        print(graph.get_graph().draw_mermaid(node_colors=DIAGRAM_STYLES))
        return

    print_parameters()
    print(f"id_hilo: {arguments.thread_id}")

    if arguments.resume:
        finance_answer = {
            "decision": arguments.resume,
            "reviewer": arguments.reviewer,
            "comment": arguments.comment,
        }
        print(f"Resuming with Finance answer: {finance_answer}")
        run = resume_release(arguments.thread_id, finance_answer)
    else:
        run = start_release(arguments.thread_id, arguments.request)

    print_outcome(run, arguments.thread_id)

    if arguments.show_state:
        snapshot = graph.get_state(config_for(arguments.thread_id))
        print("\n=== PERSISTED STATE ===")
        pprint(snapshot.values, sort_dicts=False)
        print("next:", snapshot.next)


if __name__ == "__main__":
    main()
