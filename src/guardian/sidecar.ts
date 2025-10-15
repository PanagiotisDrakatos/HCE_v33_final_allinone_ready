export class AdminToggles {
  private readonly flags = new Map<string, boolean>();

  set(name: string, enabled: boolean) {
    this.flags.set(name, enabled);
  }

  isEnabled(name: string): boolean {
    return this.flags.get(name) ?? false;
  }
}
