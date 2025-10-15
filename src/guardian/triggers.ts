export type Trigger = {
  name: string;
  threshold: number;
};

export function evaluateTrigger(
  value: number,
  trigger: Trigger,
): 'fire' | 'hold' {
  return value >= trigger.threshold ? 'fire' : 'hold';
}
