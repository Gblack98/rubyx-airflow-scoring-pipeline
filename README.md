# airflow-batch-credit-scoring

Daily batch credit scoring on Airflow: the full customer base is re-scored every night from the `credit_features` table built by [credit-scoring-dbt](https://github.com/Gblack98/credit-scoring-dbt).

```
list_chunks ──▶ score_chunk (mapped, ×N) ──▶ drift_gate (PSI) ──▶ publish
```

- `scoring/model.py` — versioned logistic model: coefficients are code (PR-reviewed), `model_version` lands next to every score for auditability
- `scoring/stability.py` — Population Stability Index between today's and yesterday's score distributions; **PSI > 0.25 fails the run and withholds publication** — a broken upstream feature never reaches lending decisions
- `dags/daily_credit_scoring.py` — chunked dynamic task mapping (capped parallelism), read-only scoring, atomic publish

## Tests

```bash
pip install -r requirements.txt
pytest
```

Covers score bounds and monotonicity (riskier behavior ⇒ lower score), band mapping, PSI on identical / slightly shifted / drifted distributions, first-run empty baseline, and DAG structure.
