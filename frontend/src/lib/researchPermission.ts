const EXPAND_KEY = "atelier_auto_expand";
const MODE_SWITCH_KEY = "atelier_auto_mode_switch";

export type ExpandPermission = "ask" | "always";
export type ModeSwitchPermission = "ask" | "always";

export function getExpandPermission(): ExpandPermission {
  if (typeof window === "undefined") return "ask";
  const v = localStorage.getItem(EXPAND_KEY);
  return v === "always" ? "always" : "ask";
}

export function setExpandPermission(mode: ExpandPermission) {
  localStorage.setItem(EXPAND_KEY, mode);
}

export function getModeSwitchPermission(): ModeSwitchPermission {
  if (typeof window === "undefined") return "ask";
  const v = localStorage.getItem(MODE_SWITCH_KEY);
  return v === "always" ? "always" : "ask";
}

export function setModeSwitchPermission(mode: ModeSwitchPermission) {
  localStorage.setItem(MODE_SWITCH_KEY, mode);
}
