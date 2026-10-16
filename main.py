import json

from bootstrap_db import DB_PATH, bootstrap
from case_config import print_parameters
from rules import calculate_release


def main() -> None:
    print_parameters()

    if not DB_PATH.exists():
        bootstrap()

    # Hito 1: no LLM yet, so the order fields are entered one by one.
    customer_id = input("\nCustomer > ").strip() or "C-1003"
    sku = input("SKU > ").strip() or "KRN-900X"
    quantity = input("Quantity > ").strip() or "9"

    if not quantity.isdigit():
        print("\nQuantity must be a whole number.")
        return

    result = calculate_release(customer_id, sku, int(quantity))

    print("\n=== RELEASE DECISION ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
