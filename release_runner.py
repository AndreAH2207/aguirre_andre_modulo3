"""Runs the release workflow by id_hilo, with the safety checks shared by every entry point.

- Resume only an id_hilo paused in finance_review (otherwise LangGraph would start from
  scratch with an empty state and ignore the Finance answer).
- Never start a new request on an id_hilo with an order waiting for Finance (it would
  replace that order).
- If the credit service is still down after the retries, report it: the checkpoint keeps
  the order at the failed node.
"""

from pprint import pprint

from langgraph.types import Command

from release_workflow import graph


def config_for(thread_id: str) -> dict:
    # "configurable" and "thread_id" are LangGraph keys; thread_id is the id_hilo.
    return {"configurable": {"thread_id": thread_id}}


def is_waiting_for_finance(thread_id: str) -> bool:
    return "finance_review" in graph.get_state(config_for(thread_id)).next


def start_release(thread_id: str, request_text: str) -> dict:
    if is_waiting_for_finance(thread_id):
        return {"outcome": "busy"}
    return _invoke({"request_text": request_text}, thread_id)


def resume_release(thread_id: str, finance_answer: dict) -> dict:
    if not is_waiting_for_finance(thread_id):
        return {"outcome": "nothing_to_resume"}
    return _invoke(Command(resume=finance_answer), thread_id)


def _invoke(workflow_input, thread_id: str) -> dict:
    try:
        result = graph.invoke(workflow_input, config=config_for(thread_id))
    except (TimeoutError, ConnectionError):
        # RetryPolicy already retried; the checkpoint keeps the order at the failed node.
        return {"outcome": "credit_unavailable"}
    outcome = "paused" if result.get("__interrupt__") else "finished"
    return {"outcome": outcome, "result": result}


def print_outcome(run: dict, thread_id: str) -> None:
    outcome = run["outcome"]
    if outcome == "busy":
        print(
            f"\nid_hilo '{thread_id}' has an order waiting for Finance. "
            "Resume it with --resume approve|reject or use another --thread-id."
        )
    elif outcome == "nothing_to_resume":
        print(f"\nNo paused release found for id_hilo '{thread_id}'. Nothing to resume.")
    elif outcome == "credit_unavailable":
        print(
            "\nCredit service unavailable after 3 attempts. "
            f"The order is saved in id_hilo '{thread_id}'; try again later."
        )
    elif outcome == "paused":
        # __interrupt__ is a LangGraph key: the flow is paused waiting for Finance.
        print("\n=== FLOW PAUSED: WAITING FOR FINANCE / CREDIT ===")
        for item in run["result"]["__interrupt__"]:
            pprint(getattr(item, "value", item), sort_dicts=False)
        print(f"\nResume with the SAME id_hilo ('{thread_id}') and --resume approve|reject")
    else:
        result = run["result"]
        print("\n=== WORKFLOW FINISHED ===")
        print(result.get("message", "No final message"))
        print("status:", result.get("status"))
