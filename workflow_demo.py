import argparse
from pprint import pprint

from dotenv import load_dotenv
from langchain_core.runnables.graph import NodeStyles

# Load .env before importing release_workflow, which builds the agent with build_model().
load_dotenv()

from case_config import print_parameters
from release_workflow import build_credit_memo, graph

# Dark boxes, light blue borders, white text.
DIAGRAM_STYLES = NodeStyles(
    default="fill:#1e293b,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
    first="fill:#0f172a,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
    last="fill:#0f172a,stroke:#7dd3fc,stroke-width:2px,color:#ffffff",
)


def read_arguments():
    parser = argparse.ArgumentParser(description="Demo: LangGraph sale release workflow")
    parser.add_argument("--request", default="Libera 4 KRN-900X para C-1003")
    parser.add_argument("--show-state", action="store_true")
    parser.add_argument("--diagram", action="store_true", help="Print the workflow as a Mermaid diagram")
    return parser.parse_args()


def main() -> None:
    arguments = read_arguments()

    if arguments.diagram:
        print(graph.get_graph().draw_mermaid(node_colors=DIAGRAM_STYLES))
        return

    print_parameters()
    result = graph.invoke({"request_text": arguments.request})

    print("\n=== WORKFLOW FINISHED ===")
    print(result.get("message", "No final message"))
    print("status:", result.get("status"))

    if result.get("status") == "pending_review":
        print("\n=== CREDIT MEMO FOR FINANCE ===")
        pprint(build_credit_memo(result), sort_dicts=False)

    if arguments.show_state:
        print("\n=== FINAL STATE ===")
        pprint(result, sort_dicts=False)


if __name__ == "__main__":
    main()
