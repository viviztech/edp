from app.workers.crm_exports import _safe


def test_csv_formula_prefixes_are_escaped() -> None:
    for value in ("=SUM(A1:A2)", "+cmd", "-1+2", "@IMPORT", "\t=SUM(A1:A2)", "  @IMPORT"):
        assert _safe(value).startswith("'")


def test_regular_csv_values_are_unchanged() -> None:
    assert _safe("Lead name") == "Lead name"
    assert _safe(None) == ""
