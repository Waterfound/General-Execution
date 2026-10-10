from general_execution.revenue_pr_process import observe_pr_process


def test_process_adapter_is_importable():
    assert callable(observe_pr_process)
