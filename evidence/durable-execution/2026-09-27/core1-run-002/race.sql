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
INSERT INTO "portfolio_checkpoints" VALUES('durable-asp',1,'gec-0473f9529bca222eb8558cb1','sha256:0473f9529bca222eb8558cb1734f808ad599d6c7f3130bae50259148f2ec2b36','{"action_ref":"rehearsal://execution_started","authority_boundary":null,"authority_stop":false,"canonical_refs":["fixture://rehearsals/core1-v1.json","tick-observation:sha256:87aefdc4e5ed301db14aff990405733a3e46a251e289ceec49615761cb38c2fa","core-requirement:sha256:2f3088c0c806c55cb27ad3bd2d5f84ce2c17df8036b48df1ae1317ccd57e9c24","core-verification:sha256:3f94aba849e194e589ccf98639bc81a49a8785dc86111679118bcfe175a10c9d","policy:sha256:013519a606522aea1522e7dfa5887a09bdcbe7df8444892395b7ddc3a5da65cd","rule:sha256:f6e8a6f4a87bc703872f45a31801b69d0a1d618be1b055d1b86aa36f588832b0"],"evidence":[{"digest":"sha256:e90638e0ba028df737f751dbe7a8ecf85a3a561a2642004524b42161c7609c76","kind":"dispatch_admitted","locator":"fixture://core1/dispatch_admitted","schema_version":"ge.checkpoint-evidence.v1"}],"next_transition_refs":["action://observe-run"],"observed_at":"2026-09-27T02:35:44.588899+00:00","portfolio_generation":1,"portfolio_id":"durable-asp","portfolio_state_digest":"sha256:6c2f098c4c173c38de60da8c09eac8a20a57b83aafa229069e59fc8dff4b17d3","role":"active","schema_version":"ge.execution-checkpoint.v1","source_revision":"src-active","state_after":"running","state_before":"ready","summary":"Bounded CORE-1 fixture execution_started","uncertainties":[],"work_id":"ACTIVE"}');
CREATE TABLE portfolio_heads (
                    portfolio_id TEXT PRIMARY KEY,
                    state_digest TEXT NOT NULL,
                    generation INTEGER NOT NULL,
                    snapshot_digest TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    latest_checkpoint_digest TEXT
                );
INSERT INTO "portfolio_heads" VALUES('durable-asp','sha256:6c2f098c4c173c38de60da8c09eac8a20a57b83aafa229069e59fc8dff4b17d3',1,'sha256:4b7d2aa668f5f535f5eb5186a1fa65857ae47b4d49eb2c63ae2938a09ab98ff9','{"schema_version":"ge.portfolio-snapshot.v1","snapshot_digest":"sha256:4b7d2aa668f5f535f5eb5186a1fa65857ae47b4d49eb2c63ae2938a09ab98ff9","state":{"active":{"active_gate":"ACTIVE_GATE","authority_boundary":null,"authority_ref":null,"blockers":[],"checkpoint_ref":null,"evidence_required":["result"],"next_action_ref":"action://observe-run","objective":"Advance active frontier","role":"active","schema_version":"ge.portfolio-entry.v1","source_revision":"src-active","state":"running","wake_condition":null,"work_id":"ACTIVE"},"generation":1,"passive":[{"active_gate":"PASSIVE_GATE","authority_boundary":null,"authority_ref":null,"blockers":[{"detail":"PASSIVE blocked","evidence_refs":[],"kind":"external_dependency","schema_version":"ge.portfolio-blocker.v1"}],"checkpoint_ref":null,"evidence_required":[],"next_action_ref":"action://passive","objective":"Wait for PASSIVE","role":"passive","schema_version":"ge.portfolio-entry.v1","source_revision":"src-passive","state":"passive","wake_condition":{"kind":"event_received","schema_version":"ge.wake-condition.v1","value":"passive.ready"},"work_id":"PASSIVE"}],"portfolio_id":"durable-asp","previous_state_digest":"sha256:60eb45c96017f97c0108bfd5b5bc5f58cf22c99be68c2ee7372551f141c6cd6c","schema_version":"ge.portfolio-state.v1","secondary":{"active_gate":"SECONDARY_GATE","authority_boundary":null,"authority_ref":null,"blockers":[],"checkpoint_ref":null,"evidence_required":[],"next_action_ref":"action://secondary","objective":"Prepare SECONDARY","role":"secondary","schema_version":"ge.portfolio-entry.v1","source_revision":"src-secondary","state":"ready","wake_condition":null,"work_id":"SECONDARY"}},"state_digest":"sha256:6c2f098c4c173c38de60da8c09eac8a20a57b83aafa229069e59fc8dff4b17d3"}','sha256:0473f9529bca222eb8558cb1734f808ad599d6c7f3130bae50259148f2ec2b36');
COMMIT;
