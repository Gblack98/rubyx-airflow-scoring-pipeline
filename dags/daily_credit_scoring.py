"""Daily batch credit scoring.

chunk ids -> score chunks in parallel (mapped tasks) -> PSI drift gate -> publish

The whole customer base is re-scored every night; the PSI gate compares
today's score distribution against yesterday's published one and withholds
publication on drift, so a broken upstream feature never reaches lending
decisions.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow.decorators import dag, task

DB_PATH = os.environ.get("SCORING_DB_PATH", "/data/scoring.duckdb")
CHUNK_SIZE = int(os.environ.get("SCORING_CHUNK_SIZE", "50000"))
MAX_PARALLEL_CHUNKS = 8


@dag(
    dag_id="daily_credit_scoring",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["team:risk", "domain:credit-scoring", "batch", "ml"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=10)},
)
def daily_credit_scoring():
    @task
    def list_chunks() -> list[dict]:
        """Split the customer base into offset windows for mapped scoring."""
        import duckdb

        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            total = con.execute("SELECT count(*) FROM credit_features").fetchone()[0]
        finally:
            con.close()
        return [
            {"offset": offset, "limit": CHUNK_SIZE}
            for offset in range(0, total, CHUNK_SIZE)
        ]

    @task(max_active_tis_per_dag=MAX_PARALLEL_CHUNKS)
    def score_chunk(chunk: dict) -> list[dict]:
        import duckdb

        from scoring.model import score_customer

        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            rows = con.execute(
                "SELECT * FROM credit_features ORDER BY customer_id "
                "LIMIT ? OFFSET ?",
                [chunk["limit"], chunk["offset"]],
            ).fetch_arrow_table().to_pylist()
        finally:
            con.close()
        return [score_customer(row).__dict__ for row in rows]

    @task
    def drift_gate(scored_chunks: list[list[dict]]) -> list[dict]:
        """Fail the run (and skip publish) if scores drifted vs yesterday."""
        import duckdb

        from scoring.stability import enforce_stability

        scores = [row for chunk in scored_chunks for row in chunk]
        con = duckdb.connect(DB_PATH, read_only=True)
        try:
            baseline = [
                row[0]
                for row in con.execute(
                    "SELECT score FROM customer_scores"
                ).fetchall()
            ]
        except duckdb.CatalogException:
            baseline = []  # first run: nothing published yet
        finally:
            con.close()

        psi = enforce_stability(baseline, [row["score"] for row in scores])
        print(f"PSI vs yesterday: {psi:.4f} ({len(scores)} customers scored)")
        return scores

    @task
    def publish(scores: list[dict]) -> int:
        import duckdb

        con = duckdb.connect(DB_PATH)
        try:
            con.execute("""
                CREATE OR REPLACE TABLE customer_scores (
                    customer_id VARCHAR PRIMARY KEY,
                    probability_of_default DOUBLE,
                    score INTEGER,
                    risk_band VARCHAR,
                    model_version VARCHAR,
                    scored_at TIMESTAMP DEFAULT current_timestamp
                )
            """)
            con.executemany(
                "INSERT INTO customer_scores "
                "(customer_id, probability_of_default, score, risk_band, model_version) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        row["customer_id"],
                        row["probability_of_default"],
                        row["score"],
                        row["risk_band"],
                        row["model_version"],
                    )
                    for row in scores
                ],
            )
        finally:
            con.close()
        return len(scores)

    publish(drift_gate(score_chunk.expand(chunk=list_chunks())))


daily_credit_scoring()
