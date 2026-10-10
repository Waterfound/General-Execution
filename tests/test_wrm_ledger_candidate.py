from general_execution.wrm_ledger_candidate import summarize

def test_unknown_revenue():
    assert summarize({'checks': []})['first_revenue'] is None
