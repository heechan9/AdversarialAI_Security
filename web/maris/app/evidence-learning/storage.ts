import { parseSession, type Session } from "./state";
export const STORAGE_KEY = "paulguard.evidence-learning.v1";
export type StoragePort = Pick<Storage, "getItem" | "setItem" | "removeItem">;
export function saveSession(storage: StoragePort, state: Session): void {
  const raw = JSON.stringify(state);
  parseSession(raw);
  storage.setItem(STORAGE_KEY, raw);
}
export function loadSession(storage: StoragePort): Session | null {
  const raw = storage.getItem(STORAGE_KEY);
  return raw === null ? null : parseSession(raw);
}
export function clearSession(storage: StoragePort): void { storage.removeItem(STORAGE_KEY); }
