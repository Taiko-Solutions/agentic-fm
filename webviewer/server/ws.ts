import type { ViteDevServer } from 'vite';

/**
 * Set up WebSocket handling on the Vite dev server.
 * We piggyback on Vite's existing HMR WebSocket by sending custom messages.
 */
export function setupWebSocket(_server: ViteDevServer): void {
  // Vite's HMR WebSocket is available at server.ws
  // We use it to send custom messages to the client
}

/**
 * Broadcast a message to all connected clients via Vite's HMR WebSocket.
 */
export function broadcastMessage(server: ViteDevServer, message: { type: string; data: unknown }): void {
  server.ws.send({
    type: 'custom',
    event: message.type,
    data: message.data,
  });
}
