import asyncio
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from router import DeterministicRouter,HybridRouter,ModelRouter

CASES=json.loads((Path(__file__).parent/"benchmark_cases.json").read_text(encoding="utf-8"))


async def evaluate(strategy:str)->None:
    if strategy=="deterministic": router=DeterministicRouter()
    elif strategy=="model": router=ModelRouter()
    else: router=HybridRouter()

    hits=0
    started=time.perf_counter()
    for case in CASES:
        decision=router.route(case["q"]) if strategy=="deterministic" else await router.route(case["q"])
        ok=decision.route.value==case["expected"]
        hits+=int(ok)
        print(f"{'OK  ' if ok else 'FAIL'} expected={case['expected']:<7} got={decision.route.value:<7} conf={decision.confidence:.2f} | {case['q']}")

    elapsed=time.perf_counter()-started
    print(f"\n{strategy}: accuracy={hits/len(CASES):.0%} | {elapsed:.2f}s")


async def main()->None:
    for strategy in ["deterministic","model","hybrid"]:
        print("\n"+"="*72)
        print(strategy.upper())
        print("="*72)
        await evaluate(strategy)


if __name__=="__main__":
    asyncio.run(main())
