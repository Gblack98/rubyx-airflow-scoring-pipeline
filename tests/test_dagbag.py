from pathlib import Path

from airflow.models import DagBag
from airflow.models.mappedoperator import MappedOperator

DAGS_DIR = Path(__file__).resolve().parent.parent / "dags"


def test_dagbag_imports_without_errors():
    dagbag = DagBag(dag_folder=str(DAGS_DIR), include_examples=False)
    assert dagbag.import_errors == {}
    dag = dagbag.dags["daily_credit_scoring"]
    assert isinstance(dag.get_task("score_chunk"), MappedOperator)
    assert dag.get_task("publish").upstream_task_ids == {"drift_gate"}
    # never two concurrent full-base scoring runs
    assert dag.max_active_runs == 1
