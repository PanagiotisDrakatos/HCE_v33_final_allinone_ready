import { AdminToggles } from '../../src/guardian/sidecar.js';
import { evaluateTrigger, type Trigger } from '../../src/guardian/triggers.js';

describe('Guardian triggers', () => {
  it('fires when value meets threshold', () => {
    const trigger: Trigger = { name: 'pnlVelocity', threshold: 10 };
    expect(evaluateTrigger(12, trigger)).toBe('fire');
  });

  it('holds when value is below the threshold', () => {
    const trigger: Trigger = { name: 'pnlVelocity', threshold: 10 };
    expect(evaluateTrigger(9, trigger)).toBe('hold');
  });
});

describe('Admin toggles', () => {
  it('disables feature by default', () => {
    const toggles = new AdminToggles();
    expect(toggles.isEnabled('riskNeutralPyramiding')).toBe(false);
  });

  it('enables feature after set', () => {
    const toggles = new AdminToggles();
    toggles.set('riskNeutralPyramiding', true);
    expect(toggles.isEnabled('riskNeutralPyramiding')).toBe(true);
  });
});
