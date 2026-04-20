# Cross-TO Record Pointer in Loops — Capture to Variables First

## Rule

**MANDATORY**: When looping over records of table A and creating/modifying records in table B inside the same iteration, **capture all needed source values to local `$*` variables BEFORE switching to B's layout**. Never rely on cross-TO reads (`A__TO::field`) from B's layout.

## Why this matters

FileMaker maintains a "current record" pointer per TO per window. In theory that pointer persists across layout switches, so `OtroTO::campo` from a layout in B should return the value of the active record of A.

**In practice, the pointer behaves unpredictably inside migration loops**:

- `Go to Layout [B]` → `New Record` in B fires auto-enter calcs that may reference TOs, touching the foundset state.
- `Commit Records` on B may flush relationship caches.
- `Go to Layout [A]` back + `Go to Record [Next]` — the "Next" is applied correctly in A's foundset, but inside the next iteration when we hop back to B, the cross-TO read of A's fields may still read the **first** record of A's foundset rather than the current one.

Observed in task 944.8 S4 (Borneo post-deploy): the loop over `BRO__Brokers` created 74 records in `CLI__Clientes`, but all 74 copied fields from broker #1 because the cross-TO read `BRO__Brokers::<campo>` from the `Clientes` layout resolved to the first broker, not the iteration's current one. The fix (variables capture) made each record unique immediately.

## The pattern

```
Go to Layout [A]
Show All Records
Go to Record [ First ]
Loop
    # 1. Capture EVERYTHING needed from A into local variables — while A is the active layout.
    Insert Calculated Result [ $A_Id      ; A__TO::Id      ]
    Insert Calculated Result [ $A_Campo1  ; A__TO::Campo1  ]
    Insert Calculated Result [ $A_Campo2  ; A__TO::Campo2  ]
    # ... tantas variables como campos origen necesites ...

    # 2. Hop to B, create/modify using ONLY $A_* variables — no cross-TO reads.
    Go to Layout [B]
    New Record
    Set Field [ B__TO::Id      ; $A_Id      ]
    Set Field [ B__TO::Campo1  ; $A_Campo1  ]
    Set Field [ B__TO::Campo2  ; $A_Campo2  ]
    Commit Records

    # 3. Back to A and advance.
    Go to Layout [A]
    Go to Record [ Next ; Exit after last ]
End Loop
```

## Why NOT this (anti-pattern)

```
Go to Layout [A]
Go to Record [ First ]
Loop
    Go to Layout [B]
    New Record
    Set Field [ B__TO::Id     ; A__TO::Id     ]   # ← cross-TO read: UNRELIABLE
    Set Field [ B__TO::Campo1 ; A__TO::Campo1 ]   # ← idem
    Commit Records
    Go to Layout [A]
    Go to Record [ Next ; Exit after last ]
End Loop
```

Looks reasonable. Works in trivial tests. **Fails silently in migration-scale loops** — B gets the same values from A's first record every iteration. No error raised. The idempotency guard then marks the migration DONE, leaving you with corrupt duplicated data.

## When this applies

- Post-deployment migration scripts that copy/duplicate records.
- Batch scripts that loop over tabla A and insert into tabla B (import, dedup, normalization, etc.).
- Any script with a loop where at least **one** step between reading A and writing B changes layout to a different base TO.

## When this does NOT apply

- Single-layout loops (no `Go to Layout` inside the Loop) — FM's current-record pointer in the loop's TO is always correct.
- Loops that only modify fields of A itself — the active record of A is already correct.
- Related-record access via a proper relationship graph — if `cli_BRO__Brokers` is related to `CLI__Clientes` by a proper FK, `cli_BRO__Brokers::campo` from `Clientes` resolves via the relationship and works correctly. This doc is about **unrelated** cross-TO access.

## Heuristic

If your loop body contains at least **one `Go to Layout` that crosses base tables**, capture to variables. No exceptions.

## Related

- `agent/docs/taiko/knowledge/trigger-suppression.md` — pair this pattern with TriggersDisable for any multi-layout loop.
- `agent/docs/taiko/knowledge/transaction-navigation.md` — navigation constraints within open transactions (complementary).
- Example: `MigrationV08_FusionEmpresas` in task 944.8 (Borneo). The v5 of the script uses this capture-first pattern for 53 fields per broker.
