import fs from 'node:fs';
import type { ViteDevServer } from 'vite';
import { broadcastMessage } from './ws';

/**
 * Watch CONTEXT.json for changes and broadcast via WebSocket.
 */
export function setupFileWatcher(server: ViteDevServer, contextPath: string): void {
  try {
    fs.watch(contextPath, { persistent: false }, (eventType) => {
      if (eventType === 'change') {
        try {
          const data = fs.readFileSync(contextPath, 'utf-8');
          broadcastMessage(server, {
            type: 'context-updated',
            data: JSON.parse(data),
          });
        } catch {
          // File might be in the middle of being written
        }
      }
    });
  } catch {
    // File doesn't exist yet — that's fine
    // We'll try to set up the watcher when the directory exists
    const dir = contextPath.substring(0, contextPath.lastIndexOf('/'));
    try {
      fs.watch(dir, { persistent: false }, (_, filename) => {
        if (filename === 'CONTEXT.json') {
          // Recursively set up the file watcher now that the file exists
          setupFileWatcher(server, contextPath);
        }
      });
    } catch {
      // Directory doesn't exist either — no watcher
    }
  }
}
