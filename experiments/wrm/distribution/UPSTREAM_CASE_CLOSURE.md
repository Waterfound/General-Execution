# RMA-DIST-001 — verified source-bound RCA

Upstream PowerShell issue #19621 and merged fix PR #19622 establish an independent diagnosis: the HTTP 429 Retry-After branch erroneously checked status 409. The local Python reenactment reproduces the decision change (5s to 2s), not the original PowerShell runtime.

Two executable files are committed to this branch: upstream_guard.py and test_upstream_guard.py. **5/5 tests locally PASS on exact GitHub-matching blobs**. The separately preserved broader analyzer passed 18/18; a deliberately reverted guard caused 9 failures. The isolated local composition with the existing RMA-DIST candidates passed **78/78**, without merge. No remote CI or actual customer acceptance is claimed.

Existing patched PowerShell is a complete substitute for this specific case. Commercial decision: KILL_CURRENT_DIFFERENTIATOR. Buyer validation, received revenue and unattended execution remain unverified. All three current RMA-DIST terminal predicates remain NOT_MET.

Next: a present-day paid RCA workflow with lawful representative traces, independent accepted output, competing tools and permissible acquisition. CR-001 retains product ownership. No Work, expenses, publication, accounts, payments, production or scheduler.
