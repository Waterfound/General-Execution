from general_execution.vercel_sandbox import _sandbox_id


class NameOnlySandbox:
    name = "sbx-general-execution-20260915"


def test_current_vercel_name_is_accepted_as_stable_identity():
    assert _sandbox_id(NameOnlySandbox()) == "sbx-general-execution-20260915"
