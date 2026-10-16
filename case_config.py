"""Reproducible configuration for case CRE-008 (Credit variant).

The seed generates the three credit parameters of the main case.
Draw order is fixed: credit limit, current exposure, review amount.
Changing the order or inserting a new draw changes every value.
"""

import random

CASE_ID = "CRE-008"
VARIANT = "Credit"
SEED = 2135

# Customer that receives the generated credit limit and exposure.
MAIN_CUSTOMER = "C-1003"

CREDIT_LIMIT_OPTIONS = [30000, 50000, 80000, 120000]
# Highest value is below the lowest limit: exposure never exceeds the limit.
CURRENT_EXPOSURE_OPTIONS = [5000, 10000, 15000, 20000, 25000]
REVIEW_AMOUNT_OPTIONS = [10000, 15000, 20000, 25000]


def generate_parameters(seed: int = SEED) -> dict:
    rng = random.Random(seed)
    credit_limit = rng.choice(CREDIT_LIMIT_OPTIONS)
    current_exposure = rng.choice(CURRENT_EXPOSURE_OPTIONS)
    review_amount = rng.choice(REVIEW_AMOUNT_OPTIONS)
    return {
        "credit_limit_usd": credit_limit,
        "current_exposure_usd": current_exposure,
        "review_amount_usd": review_amount,
    }


PARAMETERS = generate_parameters()


def print_parameters() -> None:
    # CASO_ID and SEMILLA are the labels used in the assignment (Anexo A).
    print(f"CASO_ID={CASE_ID} | VARIANT={VARIANT} | SEMILLA={SEED}")
    print(f"Main customer: {MAIN_CUSTOMER}")
    print(f"  credit limit     : USD {PARAMETERS['credit_limit_usd']:,}")
    print(f"  current exposure : USD {PARAMETERS['current_exposure_usd']:,}")
    print(f"Review amount      : USD {PARAMETERS['review_amount_usd']:,}")


if __name__ == "__main__":
    print_parameters()
