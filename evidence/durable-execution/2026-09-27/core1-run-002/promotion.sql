BEGIN TRANSACTION;
CREATE TABLE portfolio_checkpoints (
                    portfolio_id TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    checkpoint_id TEXT NOT NULL UNIQUE,
                    checkpoint_digest TEXT NOT NULL UNIQUE,
                    checkpoint_json TEXT NOT NULL,
                    PRIMARY KEY (portfolio_id, generation),
                    FOREIGN KEY (portfolio_id)
                        REFERENCES portfolio_heads(portfolio_id)
                );
INSERT INTO "portfolio_checkpoints" VALUES('durable-asp',1,'gec-c99adf44a0e86d56082c6559','sha256:c99adf44a0e86d56082c6559c5cde718b702b9d9a519e0dc03f164a7075ad12f','{"action_ref":"rehearsal://verification_passed","authority_boundary":null,"authority_stop":false,"canonical_refs":["fixture://rehearsals/core1-v1.json","tick-observation:sha256:a0c95117c19b5143409fc61bf552cfa55deb3ad868db3654f542321f36a9852f","core-requirement:sha256:2f3088c0c806c55cb27ad3bd2d5f84ce2c17df8036b48df1ae1317ccd57e9c24","core-verification:sha256:3f94aba849e194e589ccf98639bc81a49a8785dc86111679118bcfe175a10c9d","policy:sha256:013519a606522aea1522e7dfa5887a09bdcbe7df8444892395b7ddc3a5da65cd","rule:sha256:4e75d185666f9d7c7771b11b017a2a6ae79da79d95533d981df4dc235db20356"],"evidence":[{"digest":"sha256:50ac10aa095331cb04067de2e7c8d5f865879aed1fc9540128a5761530aaa85e","kind":"verifier_pass","locator":"fixture://core1/verifier_pass","schema_version":"ge.checkpoint-evidence.v1"}],"next_transition_refs":[],"observed_at":"2026-09-27T02:35:44.588899+00:00","portfolio_generation":1,"portfolio_id":"durable-asp","portfolio_state_digest":"sha256:59661641cca310f71bf8df4a86814c5dc14972e3d9e3c14ceed4cf4f52a1104c","role":"active","schema_version":"ge.execution-checkpoint.v1","source_revision":"src-active","state_after":"complete","state_before":"verifying","summary":"Bounded CORE-1 fixture verification_passed","uncertainties":[],"work_id":"ACTIVE"}');
CREATE TABLE portfolio_heads (
                    portfolio_id TEXT PRIMARY KEY,
                    state_digest TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    latest_checkpoint_digest TEXT
                );
INSERT INTO "portfolio_heads" VALUES('durable-asp','sha256:59661641cca310f71bf8df4a86814c5dc14972e3d9e3c14ceed4cf4f52a1104c',1,'sha256:1cae502766b0d929199f589e433e46c6e6c2dcc7febb1175536534319b9e82ae','{"schema_version":"ge.portfolio-snapshot.v1","snapshot_digest":"sha256:1cae502766b0d929199f589e433e46c6e6c2dcc7febb1175536534319b9e82ae","state":{"active":{"active_gate":"SECONDARY_GATE","authority_boundary":null,"authority_ref":null,"blockers":[],"checkpoint_ref":null,"evidence_required":[],"next_action_ref":"action://secondary","objective":"Prepare SECONDARY","role":"active","schema_version":"ge.portfolio-entry.v1","source_revision":"src-secondary","state":"ready","wake_condition":null,"work_id":"SECONDARY"},"generation":1,"passive":[{"active_gate":"PASSIVE-B_GATE","authority_boundary":null,"authority_ref":null,"blockers":[{"detail":"PASSIVE-B blocked","evidence_refs":[],"kind":"external_dependency","schema_version":"ge.portfolio-blocker.v1"}],"checkpoint_ref":null,"evidence_required":[],"next_action_ref":"action://passive-b","objective":"Wait for PASSIVE-B","role":"passive","schema_version":"ge.portfolio-entry.v1","source_revision":"src-passive-b","state":"passive","wake_condition":{"kind":"event_received","schema_version":"ge.wake-condition.v1","value":"passive-b.ready"},"work_id":"PASSIVE-B"}],"portfolio_id":"durable-asp","previous_state_digest":"sha256:a2c4e8d9cd1d47c6364665a3577b46c5b91ced129e1c9447ed72e353d88b013c","schema_version":"ge.portfolio-state.v1","secondary":{"active_gate":"PASSIVE-A_GATE","authority_boundary":null,"authority_ref":null,"blockers":[],"checkpoint_ref":null,"evidence_required":[],"next_action_ref":"action://woken-passive","objective":"Wait for PASSIVE-A","role":"secondary","schema_version":"ge.portfolio-entry.v1","source_revision":"src-passive-a","state":"ready","wake_condition":null,"work_id":"PASSIVE-A"}},"state_digest":"sha256:59661641cca310f71bf8df4a86814c5dc14972e3d9e3c14ceed4cf4f52a1104c"}','sha256:c99adf44a0e86d56082c6559c5cde718b702b9d9a519e0dc03f164a7075ad12f');
COMMIT;
