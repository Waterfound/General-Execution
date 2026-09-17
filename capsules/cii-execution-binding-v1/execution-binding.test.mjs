import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createExecutionBinding,
  EXECUTION_BINDING_CONTRACT_VERSION,
  routeExecutionTask,
  SYSTEM_ROUTE_BY_TASK_CLASS,
  validateExecutionBinding
} from './execution-binding.mjs';

const NOW = '2026-09-17T11:30:00.000Z';
const checkpoint = (name, index, ref) => ({
  name,
  at: `2026-09-17T11:${String(20 + index).padStart(2, '0')}:00.000Z`,
  ...(ref ? { ref } : {})
});
const routed = [checkpoint('request_received', 0), checkpoint('route_decided', 1)];
const attached = [
  ...routed,
  checkpoint('executor_selected', 2, 'general-execution:session-42'),
  checkpoint('executor_attached', 3, 'general-execution:session-42')
];
const evidenced = [...attached, checkpoint('evidence_emitted', 4, 'workflow:run-314')];

function base(overrides = {}) {
  return {
    request_id: 'request-001',
    task_class: 'runtime_execution',
    mode: 'real_execution',
    status: 'READY_TO_EXECUTE',
    progress_percent: 0,
    executor: null,
    evidence_refs: [],
    checkpoints: routed,
    updated_at: NOW,
    ...overrides
  };
}

test('routing-fit is explicit and deterministic', () => {
  assert.equal(EXECUTION_BINDING_CONTRACT_VERSION, 1);
  assert.deepEqual(SYSTEM_ROUTE_BY_TASK_CLASS, {
    diagnosis: 'diagnostic_intelligence',
    improvement: 'continuous_improvement_intelligence',
    parallel_engineering: 'build_colony',
    runtime_execution: 'general_execution',
    cross_system_handoff: 'system_interoperability_envelope'
  });
  for (const [taskClass, expected] of Object.entries(SYSTEM_ROUTE_BY_TASK_CLASS)) {
    assert.equal(routeExecutionTask(taskClass), expected);
  }
});

test('methodology-only cannot masquerade as execution', () => {
  const binding = createExecutionBinding(base({ task_class: 'diagnosis', mode: 'methodology_only', status: 'METHODOLOGY_ONLY' }));
  assert.equal(binding.route, 'diagnostic_intelligence');
  assert.throws(() => createExecutionBinding(base({ mode: 'methodology_only', status: 'RUNNING' })), /methodology_only mode cannot claim/);
});

test('READY_TO_EXECUTE may have no executor or evidence', () => {
  const binding = createExecutionBinding(base());
  assert.equal(binding.executor, null);
  assert.equal(binding.evidence_refs.length, 0);
});

test('RUNNING requires attached executor and external evidence', () => {
  assert.throws(() => createExecutionBinding(base({ status: 'RUNNING', progress_percent: 1 })), /attached executor/);
  assert.throws(() => createExecutionBinding(base({
    status: 'RUNNING', progress_percent: 1,
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    checkpoints: attached
  })), /external evidence/);
  const valid = createExecutionBinding(base({
    status: 'RUNNING', progress_percent: 20,
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    evidence_refs: [{ kind: 'workflow_run', ref: 'github-actions:run-314' }],
    checkpoints: evidenced
  }));
  assert.equal(valid.progress_percent, 20);
});

test('COMPLETED requires 100 percent and evidence', () => {
  const completed = createExecutionBinding(base({
    status: 'COMPLETED', progress_percent: 100,
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    evidence_refs: [{ kind: 'test', ref: 'node-test:pass' }], checkpoints: evidenced
  }));
  assert.equal(completed.status, 'COMPLETED');
  assert.throws(() => createExecutionBinding(base({
    status: 'COMPLETED', progress_percent: 99,
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    evidence_refs: [{ kind: 'test', ref: 'node-test:pass' }], checkpoints: evidenced
  })), /100% progress/);
});

test('background conversational states are invalid', () => {
  for (const status of ['QUEUED', 'WAITING', 'CONTINUING']) {
    assert.throws(() => createExecutionBinding(base({ status })), /unsupported execution status/);
  }
});

test('checkpoint path is ordered and gap-free', () => {
  assert.throws(() => createExecutionBinding(base({
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    checkpoints: [...routed, checkpoint('executor_attached', 3, 'general-execution:session-42')]
  })), /ordered prefix/);
});

test('routing mismatch and conversational evidence fail closed', () => {
  const valid = createExecutionBinding(base());
  assert.throws(() => validateExecutionBinding({ ...valid, route: 'continuous_improvement_intelligence' }), /route mismatch/);
  assert.throws(() => createExecutionBinding(base({
    status: 'RUNNING', progress_percent: 5,
    executor: { kind: 'general_execution', ref: 'session-42', attached: true },
    evidence_refs: [{ kind: 'conversation_claim', ref: 'assistant-said-running' }],
    checkpoints: evidenced
  })), /unsupported evidence kind/);
});
