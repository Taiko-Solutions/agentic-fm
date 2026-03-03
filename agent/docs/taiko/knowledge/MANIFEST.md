# Taiko Knowledge Base Manifest

Taiko-specific architectural patterns and development decisions. These documents define how Taiko Solutions builds FileMaker solutions — they complement the general FileMaker knowledge in `agent/docs/knowledge/`.

All paths are relative to `agent/docs/taiko/knowledge/`.

---

| File | Description | Keywords |
|------|-------------|----------|
| `clew-pattern.md` | Error handling system using Loop/Exit Loop If as pseudo try-catch; error.* custom functions; errorTrace JSON propagation; error constants; validation patterns | error, try, catch, clew, error handling, throw, exit loop, error.Throw, error.WasThrown, error.GetTrace, error.InSubscript, error.ThrowIf, error.ThrowIfLast, error.CreateVarsFromKeys, error.ThrowIfMissingParam, error.ThrowIfWrongContext, errorTrace, _error_ |
| `three-layer-architecture.md` | Three-layer architecture: Interface (UI, no data changes), Controller (business logic, transactions, Go to Layout), Data (tables, fields, relationships); unidirectional flow; anti-patterns | architecture, layer, interface, controller, data, separation, responsibility, Go to Layout, .Controller, business logic, three layer, 3 capas |
| `utility-transactional.md` | Non-destructive editing pattern with global fields in a Utility table, modal card window, and transactional controller with automatic rollback; Utility Manager, Initialize Shadow, and Transactional scripts | transaction, utility, global fields, card window, modal, rollback, revert transaction, open transaction, commit transaction, non-destructive, edit, create, shadow, Utility Manager, Initialize Shadow, AsJSON |
| `logging-system.md` | Error logging to a Log table with Create Log Clew script; optional transaction logging to Registro table; retry capability from logged records; Geist-to-Clew normalization for cross-framework compatibility | log, logging, error log, registro, retry, reintentar, Create Log Clew, error.NormalizeFromGeist, Geist, transaction log |
