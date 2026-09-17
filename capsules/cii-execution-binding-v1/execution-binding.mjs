import {
  fields, list, number as boundedNumber, object, requireThat, text, timestamp, unique
} from './contracts.mjs';

export const EXECUTION_BINDING_CONTRACT_VERSION = 1;

export const SYSTEM_ROUTE_BY_TASK_CLASS = Object.freeze({
  diagnosis: 'diagnostic_intelligence',
  improvement: 'continuous_improvement_intelligence',
  parallel_engineering: 'build_colony',
  runtime_execution: 'general_execution',
  cross_system_handoff: 'system_interoperability_envelope'
});

export const EXECUTION_MODES = Object.freeze(['methodology_only', 'real_execution']);
export const EXECUTION_STATUSES = Object.freeze([
  'METHODOLOGY_ONLY',
  'NOT_STARTED',
  'READY_TO_EXECUTE',
  'RUNNING',
  'BLOCKED',
  'COMPLETED'
]);
export const EXECUTION_EVIDENCE_KINDS = Object.freeze([
  'tool_run',
  'automation',
  'executor_session',
  'workflow_run',
  'artifact',
  'commit',
  'test'
]);
export const EXECUTION_CHECKPOINT_ORDER = Object.freeze([
  'request_received',
  'route_decided',
  'executor_selected',
  'executor_attached',
  'evidence_emitted'
]);

export function routeExecutionTask(taskClass) {
  text(taskClass, 'task_class', 80);
  const route = SYSTEM_ROUTE_BY_TASK_CLASS[taskClass];
  requireThat(route, `unsupported task_class: ${taskClass}`);
  return route;
}

function validateExecutor(executor) {
  fields(executor, ['kind', 'ref', 'attached'], 'executor');
  text(executor.kind, 'executor.kind', 80);
  text(executor.ref, 'executor.ref', 500);
  requireThat(typeof executor.attached === 'boolean', 'executor.attached must be boolean');
}

function validateEvidenceRef(evidence) {
  fields(evidence, ['kind', 'ref'], 'evidence_ref');
  requireThat(EXECUTION_EVIDENCE_KINDS.includes(evidence.kind), `unsupported evidence kind: ${evidence.kind}`);
  text(evidence.ref, 'evidence_ref.ref', 1000);
}

function validateCheckpoint(checkpoint) {
  fields(checkpoint, ['name', 'at', 'ref'], 'checkpoint');
  requireThat(EXECUTION_CHECKPOINT_ORDER.includes(checkpoint.name), `unsupported checkpoint: ${checkpoint.name}`);
  timestamp(checkpoint.at, `checkpoint.${checkpoint.name}.at`);
  if (Object.hasOwn(checkpoint, 'ref')) text(checkpoint.ref, `checkpoint.${checkpoint.name}.ref`, 1000);
}

export function validateExecutionBinding(binding) {
  fields(binding, [
    'schema_version', 'request_id', 'task_class', 'route', 'mode', 'status',
    'progress_percent', 'executor', 'evidence_refs', 'checkpoints', 'updated_at'
  ], 'execution_binding');
  requireThat(binding.schema_version === EXECUTION_BINDING_CONTRACT_VERSION, 'unsupported execution binding schema_version');
  text(binding.request_id, 'request_id', 200);
  const expectedRoute = routeExecutionTask(binding.task_class);
  requireThat(binding.route === expectedRoute, `route mismatch: ${binding.task_class} must route to ${expectedRoute}`);
  requireThat(EXECUTION_MODES.includes(binding.mode), `unsupported execution mode: ${binding.mode}`);
  requireThat(EXECUTION_STATUSES.includes(binding.status), `unsupported execution status: ${binding.status}`);
  boundedNumber(binding.progress_percent, 'progress_percent', 0, 100);
  requireThat(Number.isInteger(binding.progress_percent), 'progress_percent must be an integer');
  timestamp(binding.updated_at, 'updated_at');

  requireThat(binding.executor === null || typeof binding.executor === 'object', 'executor must be null or an object');
  if (binding.executor !== null) validateExecutor(binding.executor);

  list(binding.evidence_refs, 'evidence_refs', 64);
  binding.evidence_refs.forEach(validateEvidenceRef);
  unique(binding.evidence_refs.map(item => `${item.kind}:${item.ref}`), 'execution evidence refs');

  list(binding.checkpoints, 'checkpoints', EXECUTION_CHECKPOINT_ORDER.length);
  requireThat(binding.checkpoints.length >= 2, 'execution binding requires request_received and route_decided checkpoints');
  binding.checkpoints.forEach(validateCheckpoint);
  const checkpointNames = binding.checkpoints.map(item => item.name);
  unique(checkpointNames, 'checkpoint names');
  requireThat(
    checkpointNames.every((name, index) => name === EXECUTION_CHECKPOINT_ORDER[index]),
    'checkpoints must form an ordered prefix: request_received -> route_decided -> executor_selected -> executor_attached -> evidence_emitted'
  );

  const selected = checkpointNames.includes('executor_selected');
  const attached = checkpointNames.includes('executor_attached');
  const evidenceEmitted = checkpointNames.includes('evidence_emitted');

  if (binding.mode === 'methodology_only') {
    requireThat(binding.status === 'METHODOLOGY_ONLY', 'methodology_only mode cannot claim an execution status');
    requireThat(binding.progress_percent === 0, 'methodology_only mode cannot claim execution progress');
    requireThat(binding.executor === null, 'methodology_only mode cannot attach an executor');
    requireThat(binding.evidence_refs.length === 0, 'methodology_only mode cannot emit execution evidence');
    requireThat(binding.checkpoints.length === 2, 'methodology_only mode stops after route_decided');
    return binding;
  }

  requireThat(binding.status !== 'METHODOLOGY_ONLY', 'real_execution mode cannot use METHODOLOGY_ONLY status');

  if (selected) requireThat(binding.executor !== null, 'executor_selected checkpoint requires executor metadata');
  if (binding.executor !== null) requireThat(selected, 'executor metadata requires executor_selected checkpoint');
  if (attached) requireThat(binding.executor?.attached === true, 'executor_attached checkpoint requires executor.attached=true');
  if (binding.executor?.attached === true) requireThat(attached, 'attached executor requires executor_attached checkpoint');
  if (evidenceEmitted) requireThat(binding.evidence_refs.length > 0, 'evidence_emitted checkpoint requires external evidence');
  if (binding.evidence_refs.length > 0) requireThat(evidenceEmitted, 'external evidence requires evidence_emitted checkpoint');

  const executionClaimed = binding.status === 'RUNNING' || binding.status === 'COMPLETED' || binding.progress_percent > 0;
  if (executionClaimed) {
    requireThat(binding.executor?.attached === true, 'execution/progress claim requires an attached executor');
    requireThat(binding.evidence_refs.length > 0, 'execution/progress claim requires external evidence');
  }

  if (binding.status === 'NOT_STARTED') {
    requireThat(binding.progress_percent === 0, 'NOT_STARTED requires 0% progress');
    requireThat(binding.executor === null, 'NOT_STARTED cannot have an executor selected');
    requireThat(binding.evidence_refs.length === 0, 'NOT_STARTED cannot have execution evidence');
    requireThat(binding.checkpoints.length === 2, 'NOT_STARTED stops after route_decided');
  }

  if (binding.status === 'READY_TO_EXECUTE') {
    requireThat(binding.progress_percent === 0, 'READY_TO_EXECUTE requires 0% progress');
    requireThat(binding.evidence_refs.length === 0, 'READY_TO_EXECUTE cannot claim execution evidence');
  }

  if (binding.status === 'RUNNING') {
    requireThat(binding.progress_percent < 100, 'RUNNING progress must be below 100%');
  }

  if (binding.status === 'COMPLETED') {
    requireThat(binding.progress_percent === 100, 'COMPLETED requires 100% progress');
  }

  return binding;
}

export function createExecutionBinding({
  request_id,
  task_class,
  mode,
  status,
  progress_percent = 0,
  executor = null,
  evidence_refs = [],
  checkpoints,
  updated_at
}) {
  object({ request_id, task_class, mode, status, checkpoints, updated_at }, 'execution binding input');
  return validateExecutionBinding({
    schema_version: EXECUTION_BINDING_CONTRACT_VERSION,
    request_id,
    task_class,
    route: routeExecutionTask(task_class),
    mode,
    status,
    progress_percent,
    executor,
    evidence_refs,
    checkpoints,
    updated_at
  });
}
