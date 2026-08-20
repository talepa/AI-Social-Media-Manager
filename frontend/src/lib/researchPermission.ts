const STORAGE_KEY = "atelier_auto_expand";

export type ExpandPermission = "ask" | "always";

export function getExpandPermission(): ExpandPermission {
  if (typeof window === "undefined") return "ask";
  const v = localStorage.getItem(STORAGE_KEY);
  return v === "always" ? "always" : "ask";
}

export function setExpandPermission(mode: ExpandPermission) {
  localStorage.setItem(STORAGE_KEY, mode);
}
