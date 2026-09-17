export class ContractError extends Error {
  constructor(message) { super(message); this.name = 'ContractError'; }
}

export function requireThat(condition, message) {
  if (!condition) throw new ContractError(message);
}

export function object(value, label) {
  requireThat(value !== null && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
}

export function text(value, label, max = 4000) {
  requireThat(typeof value === 'string' && value.trim().length > 0 && value.length <= max, `${label} must be nonempty text (max ${max})`);
}

export function number(value, label, min = -Number.MAX_VALUE, max = Number.MAX_VALUE) {
  requireThat(Number.isFinite(value) && value >= min && value <= max, `${label} must be finite and between ${min} and ${max}`);
}

export function list(value, label, max = 128) {
  requireThat(Array.isArray(value) && value.length <= max, `${label} must be an array (max ${max})`);
}

export function unique(values, label) {
  requireThat(new Set(values).size === values.length, `${label} must be unique`);
}

export function fields(value, allowed, label) {
  object(value, label);
  for (const key of Object.keys(value)) requireThat(allowed.includes(key), `${label}: unknown field ${key}`);
}

export function timestamp(value, label) {
  text(value, label, 30);
  requireThat(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/.test(value), `${label} must be an ISO UTC timestamp`);
  const result = Date.parse(value);
  requireThat(Number.isFinite(result) && new Date(result).toISOString().slice(0, 19) === value.slice(0, 19), `${label} is not a valid calendar timestamp`);
  return result;
}
