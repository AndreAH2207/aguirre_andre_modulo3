import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "business.db"

SALES = [
    ("2026-01-20", "C-9999", "NXS-G10", 5, 3426.25),
    ("2026-02-10", "C-1003", "KRN-900X", 3, 7351.50),
    ("2026-03-05", "C-1010", "TTN-M40", 8, 25684.80),
    ("2026-04-22", "C-1003", "OPT-V300", 6, 9454.80),
    ("2026-05-11", "C-9999", "OPT-V300", 3, 4727.40),
    ("2026-06-18", "C-1010", "CYC-3DX", 2, 8240.90),
    ("2026-07-15", "C-1003", "NXS-G10", 10, 6852.50),
    ("2026-08-27", "C-1010", "OPT-V300", 12, 18909.60),
    ("2026-09-03", "C-1003", "KRN-900X", 2, 4901.00),
]


def bootstrap() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute(
            """
            CREATE TABLE sales(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                net_revenue_usd REAL NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO sales(sale_date,customer_id,sku,quantity,net_revenue_usd) VALUES (?,?,?,?,?)",
            SALES,
        )
        conn.commit()
    print(f"SQLite ready: {DB_PATH} ({len(SALES)} sales)")


if __name__ == "__main__":
    bootstrap()
