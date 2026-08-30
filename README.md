# airflow-batch-credit-scoring

Daily batch credit scoring on Airflow: the full customer base is re-scored every night from the `credit_features` table built by [credit-scoring-dbt](https://github.com/Gblack98/credit-scoring-dbt).

```
list_chunks ──▶ score_chunk (mapped, ×N) ──▶ drift_gate (PSI) ──▶ publish
```

- `scoring/model.py`: versioned logistic model, the coefficients are code and get reviewed in a PR. `model_version` is stored next to every score.
- `scoring/stability.py`: Population Stability Index between today's and yesterday's scores. Above 0.25 the run fails and nothing is published, so a broken upstream feature never reaches a lending decision.
- `dags/daily_credit_scoring.py`: chunked dynamic task mapping with capped parallelism, read-only scoring, atomic publish.

## Tests

```bash
pip install -r requirements.txt
pytest
```

Covers score bounds and monotonicity (riskier behavior ⇒ lower score), band mapping, PSI on identical / slightly shifted / drifted distributions, first-run empty baseline, and DAG structure.
