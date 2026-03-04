/**
 * Parse pipe-delimited index files from /api/index/:name
 * These are pre-parsed by the server into string[][] arrays.
 */

import { fetchIndex } from '@/api/client';

export interface IndexEntry {
  columns: string[];
}

/** Fetch and cache an index file */
const cache = new Map<string, string[][]>();

export async function getIndex(name: string): Promise<string[][]> {
  const cached = cache.get(name);
  if (cached) return cached;

  const rows = await fetchIndex(name);
  cache.set(name, rows);
  return rows;
}

/** Clear the index cache (e.g. when context refreshes) */
export function clearIndexCache(): void {
  cache.clear();
}

/** Search an index for rows matching a term in any column */
export async function searchIndex(
  name: string,
  term: string,
): Promise<string[][]> {
  const rows = await getIndex(name);
  const lower = term.toLowerCase();
  return rows.filter(row => row.some(col => col.toLowerCase().includes(lower)));
}
