import { test } from 'node:test';
import assert from 'node:assert/strict';
import type { OperationalPhaseDTO } from '../types.ts';
import { buildPhasesForProfile, allPhasesBelongToProfile } from './eventDayPhases.ts';

const UUID_ACT_EXT = '4c9bbb44-b123-4e75-8b16-6b324f3b4ff3';
const UUID_ACT_TEMP = '11111111-1111-4111-8111-111111111111';
const UUID_AFL_TARDIA = 'c6fba16e-0000-0000-0000-c6fbca07b0c5';
const UUID_AFL_TEMP = '22222222-2222-4222-8222-222222222222';

function phase(id: string, profileId: string, sortOrder = 0, name = id): OperationalPhaseDTO {
  return { id, operational_profile_id: profileId, name, sort_order: sortOrder, created_at: '', updated_at: '' };
}

test('buildPhasesForProfile devuelve solo fases del perfil indicado', () => {
  const ops = [
    phase(UUID_ACT_EXT, 'PROFILE-A', 1, 'ActividadExtendida'),
    phase(UUID_ACT_TEMP, 'PROFILE-A', 2, 'ActividadTemprana'),
    phase(UUID_AFL_TARDIA, 'PROFILE-B', 1, 'AfluenciaTardía'),
  ];
  const rebuilt = buildPhasesForProfile('PROFILE-B', ops);
  const ids = rebuilt.map((p) => p.operational_phase_id);
  assert.equal(ids.length, 1);
  assert.ok(ids.includes(UUID_AFL_TARDIA));
  assert.ok(!ids.includes(UUID_ACT_EXT));
  assert.ok(!ids.includes(UUID_ACT_TEMP));
  assert.ok(rebuilt.every((p) => p.start_min === null && p.end_min === null));
});

test('ActividadExtendida -> AfluenciaTardía: solo UUID de AfluenciaTardía', () => {
  const ops = [
    phase(UUID_ACT_EXT, 'prof-act', 1),
    phase(UUID_AFL_TARDIA, 'profileB', 1),
  ];
  assert.deepEqual(buildPhasesForProfile('profileB', ops).map((p) => p.operational_phase_id), [UUID_AFL_TARDIA]);
});

test('ActividadExtendida -> AfluenciaTemprana: solo UUID de AfluenciaTemprana', () => {
  const ops = [
    phase(UUID_ACT_EXT, 'prof-act', 1),
    phase(UUID_AFL_TEMP, 'prof-c', 1),
  ];
  assert.deepEqual(buildPhasesForProfile('prof-c', ops).map((p) => p.operational_phase_id), [UUID_AFL_TEMP]);
});

test('ningún UUID del perfil anterior sobrevive en la reconstrucción', () => {
  const ops = [
    phase(UUID_ACT_EXT, 'prof-a', 1),
    phase(UUID_ACT_TEMP, 'prof-a', 2),
    phase(UUID_AFL_TARDIA, 'prof-b', 1),
  ];
  const rebuilt = buildPhasesForProfile('prof-b', ops);
  for (const p of rebuilt) {
    assert.notEqual(p.operational_phase_id, UUID_ACT_EXT);
    assert.notEqual(p.operational_phase_id, UUID_ACT_TEMP);
  }
});

test('allPhasesBelongToProfile rechaza un payload mezclado A/B', () => {
  const ops = [
    phase(UUID_ACT_EXT, 'prof-a', 1),
    phase(UUID_AFL_TARDIA, 'prof-b', 1),
  ];
  const clean = buildPhasesForProfile('prof-b', ops);
  assert.equal(allPhasesBelongToProfile(clean, ops), true);

  const mezclado = [{ operational_phase_id: UUID_ACT_EXT, start_min: 0, end_min: 60 }];
  const soloB = ops.filter((o) => o.operational_profile_id === 'prof-b');
  assert.equal(allPhasesBelongToProfile(mezclado, soloB), false);
});