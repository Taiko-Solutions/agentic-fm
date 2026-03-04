import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

interface SpawnResult {
  stdout: string;
  stderr: string;
  exitCode: number;
}

/**
 * Find the .venv directory by walking up from a starting directory.
 * Handles git worktrees where .venv lives at the main repo root,
 * not inside the worktree.
 */
function findVenv(startDir: string): string | null {
  let dir = startDir;
  for (let i = 0; i < 10; i++) {
    const candidate = path.join(dir, '.venv', 'bin', 'python');
    if (fs.existsSync(candidate)) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

/**
 * Invoke a Python script using the project's .venv.
 * Walks up from agentDir to find the .venv (handles worktrees).
 */
export function spawnPython(
  agentDir: string,
  args: string[],
  timeout = 30_000,
): Promise<SpawnResult> {
  return new Promise((resolve, reject) => {
    const repoRoot = findVenv(path.resolve(agentDir, '..'));
    if (!repoRoot) {
      reject(new Error(
        `.venv not found. Searched upward from ${agentDir}. ` +
        'Ensure the Python virtualenv is created at the repo root.'
      ));
      return;
    }
    const pythonBin = path.join(repoRoot, '.venv', 'bin', 'python');

    const proc = spawn(pythonBin, args, {
      cwd: repoRoot,
      timeout,
      env: {
        ...process.env,
        VIRTUAL_ENV: path.join(repoRoot, '.venv'),
      },
    });

    const stdoutChunks: string[] = [];
    const stderrChunks: string[] = [];

    proc.stdout.on('data', (data: Buffer) => {
      stdoutChunks.push(data.toString());
    });

    proc.stderr.on('data', (data: Buffer) => {
      stderrChunks.push(data.toString());
    });

    proc.on('close', (code: number | null) => {
      resolve({
        stdout: stdoutChunks.join(''),
        stderr: stderrChunks.join(''),
        exitCode: code ?? 1,
      });
    });

    proc.on('error', (err: Error) => {
      reject(err);
    });
  });
}
