import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  isBathroomSubtipo,
  parseBathroomUseRate,
  formatUseRate,
  INITIAL_BATHROOM_USE_RATE_PERSON_HOUR,
} from './bathroomUseRate.ts';

test('isBathroomSubtipo acepta el slug canónico y tolera mayúsculas/espacios', () => {
  assert.equal(isBathroomSubtipo('banos'), true);
  assert.equal(isBathroomSubtipo('Banos'), true);
  assert.equal(isBathroomSubtipo('  banos  '), true);
});

test('isBathroomSubtipo rechaza otros subtipos y vacíos', () => {
  for (const value of ['hidratacion', 'foodtruck', '', 'ban', null, undefined]) {
    assert.equal(isBathroomSubtipo(value), false, `esperaba false para ${String(value)}`);
  }
});

test('formatUseRate usa el valor persistido y cae al default de 0.1', () => {
  assert.equal(formatUseRate(0.25), '0.25');
  assert.equal(formatUseRate(0), '0');
  assert.equal(formatUseRate(null), String(INITIAL_BATHROOM_USE_RATE_PERSON_HOUR));
  assert.equal(formatUseRate(undefined), String(INITIAL_BATHROOM_USE_RATE_PERSON_HOUR));
});

test('parseBathroomUseRate acepta enteros y hasta 2 decimales', () => {
  assert.deepEqual(parseBathroomUseRate('0'), { ok: true, value: 0 });
  assert.deepEqual(parseBathroomUseRate('0.1'), { ok: true, value: 0.1 });
  assert.deepEqual(parseBathroomUseRate('0.25'), { ok: true, value: 0.25 });
  assert.deepEqual(parseBathroomUseRate('  1.5  '), { ok: true, value: 1.5 });
  assert.deepEqual(parseBathroomUseRate('12'), { ok: true, value: 12 });
});

test('parseBathroomUseRate rechaza vacíos, negativos y más de 2 decimales', () => {
  for (const raw of ['', '   ', '-0.1', '-1', '0.125', '1.234', 'abc', 'NaN', 'Infinity', '1e-1', '0,1']) {
    const result = parseBathroomUseRate(raw);
    assert.equal(result.ok, false, `esperaba rechazo para "${raw}"`);
    if (!result.ok) assert.ok(result.error.length > 0);
  }
});

test('parseBathroomUseRate no acepta dígitos en exceso que desbordan a Infinity', () => {
  const result = parseBathroomUseRate('9'.repeat(400));
  assert.equal(result.ok, false);
});