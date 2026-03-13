import type { FMContext } from './types';

/** Simple reactive context store using callbacks */
type Listener = () => void;

let _context: FMContext | null = null;
const listeners = new Set<Listener>();

export function getContext(): FMContext | null {
  return _context;
}

export function setContext(ctx: FMContext | null): void {
  _context = ctx;
  listeners.forEach(fn => fn());
}

export function subscribe(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
