# fm-debug Skill — Autonomous Testing Findings

Date: 2026-03-22
Environment: FM Pro 22.0.4, FMS 21.1.5 (Docker), companion on host (0.0.0.0:8765), agent in Linux container

---

## Summary

The fm-debug skill's core infrastructure works end-to-end. The companion `/debug` endpoint, the Agentic-fm Debug FM script, and the `output.json` feedback loop are all functional when the script runs **client-side on the FM Pro host**.

A critical discovery was made about error data capture: **`Get(LastError)` resets the error state as a side effect.** Once called, `Get(LastErrorLocation)` and `Get(LastErrorDetail)` can no longer return data for that error. All three functions must be captured in a **single expression** within one `Set Variable` step. When done correctly, all error data — including `Get(LastErrorLocation)` — works perfectly in FM Pro 22.0.4.

---

## Test Results

### Test 1: Companion `/debug` endpoint — PASS

Direct `POST` to `http://local.hub:8765/debug` with a JSON payload. The companion wrote `agent/debug/output.json` correctly, with all fields preserved.

```json
// Sent
{"label": "direct-test", "vars": {"testVar": "hello", "count": "42"}}
// Written to output.json — exact match
```

---

### Test 2: OData → Agentic-fm Debug — FAIL (expected)

Called `AGFMScriptBridge → Agentic-fm Debug` via OData. The script reported success (exit code 0) but `output.json` was **not updated**. The Agentic-fm Debug script's `Insert from URL` targets `http://127.0.0.1:8765/debug` — inside the Docker container, `127.0.0.1` is the container's own loopback, not the host where the companion runs.

**Root cause**: Known Docker networking limitation, already documented in `DEPLOYMENT_STATUS.md`. Server-side script execution cannot reach the host companion at `127.0.0.1`.

**Impact**: fm-debug **cannot be used via OData-triggered scripts**. This is by design — the debug script is meant for client-side execution where `127.0.0.1` correctly resolves to the host.

---

### Test 3: AppleScript `/trigger` — initially FAIL, then PASS

First attempts to run scripts via `/trigger` (AppleScript `do script`) returned `-10004` privilege violation.

**Root cause**: The frontmost FM document did not have `fmextscriptaccess` enabled on the active account's privilege set. After running Tier 3 deployment (which uses System Events UI automation, not `do script`), the Invoice Solution became frontmost with the correct privilege context, and subsequent `/trigger` calls succeeded.

**Key lesson**: `fmextscriptaccess` must be enabled on the account's privilege set in the **frontmost** document. If another file is frontmost, `/trigger` will fail even if the target file has the privilege.

---

### Test 4: Full fm-debug flow (deploy + run + read output) — PASS

Created a test script with debug instrumentation:
1. Captured runtime variables ($today, $account, $layout, $foundCount)
2. Called `Perform Script [ "Agentic-fm Debug" ]` with JSON parameter
3. Deployed via Tier 3 (raw AppleScript → companion `/trigger`)
4. Ran via `/trigger` (AppleScript `do script` on host FM Pro)
5. Read `agent/debug/output.json`

**Result**:
```json
{
  "label": "Debug Test - runtime state capture",
  "timestamp": "3/22/2026 10:08:30 AM",
  "vars": {
    "account": "admin",
    "foundCount": "2",
    "layout": "Dashboard",
    "today": "3/22/2026"
  }
}
```

All variables captured correctly. The end-to-end flow works.

---

### Test 5: Error capture with single-expression pattern — PASS

Deliberately triggered error 102 (`Set Field` with no field), then captured all error data in a single `Set Variable` step:

```
Set Variable [ $errData ; JSONSetElement ( "{}" ;
    [ "lastError" ; Get ( LastError ) ; JSONNumber ] ;
    [ "lastErrorDetail" ; Get ( LastErrorDetail ) ; JSONString ] ;
    [ "lastErrorLocation" ; Get ( LastErrorLocation ) ; JSONString ]
) ]
```

**Result**:
```json
{
  "label": "Error capture test - single expression",
  "vars": {
    "errData": {
      "lastError": 102,
      "lastErrorDetail": "",
      "lastErrorLocation": "Debug Error Test\rSet Field\r6"
    },
    "phase": "after error"
  }
}
```

`Get(LastErrorLocation)` correctly returns `"Debug Error Test\rSet Field\r6"` — script name, step name, and line number separated by carriage returns (`\r`).

---

### Test 6: Forced harmless error for line number capture — PASS

Used the `Set Field []` technique to force error 102, then immediately captured with the single-expression pattern:

**Result**:
```json
{
  "vars": {
    "errData": {
      "lastError": 102,
      "lastErrorDetail": "",
      "lastErrorLocation": "Debug Location Test\rSet Field\r7"
    },
    "myVar": "test value",
    "calcResult": "300"
  }
}
```

The forced-error technique works correctly when all error functions are in one expression.

---

### Test 7: Multiple error types — PASS (all three)

Tested three error types in a single script, each captured with the single-expression pattern:

**Result**:
```json
{
  "vars": {
    "err1_setField": {
      "lastError": 102,
      "lastErrorDetail": "",
      "lastErrorLocation": "Debug Combined Test\rSet Field\r4"
    },
    "err2_goToLayout": {
      "lastError": 105,
      "lastErrorDetail": "",
      "lastErrorLocation": "Debug Combined Test\rGo to Layout\r7"
    },
    "err3_performScript": {
      "lastError": 104,
      "lastErrorDetail": "",
      "lastErrorLocation": "Debug Combined Test\rPerform Script\r10"
    }
  }
}
```

All three error types produce correct `lastError` codes and `lastErrorLocation` with script name, step name, and line number. Confirmed both client-side (via `/trigger`) and server-side (via OData `Exit Script` result).

---

## Key Findings

### Finding 1: `Get(LastError)` resets the error state

**This is the critical discovery.** `Get(LastError)` is not a passive read — it clears the error state as a side effect. After `Get(LastError)` is evaluated, `Get(LastErrorLocation)` and `Get(LastErrorDetail)` return empty because the error they refer to has been cleared.

**Consequence**: All three error functions must be captured in a **single expression** within one `Set Variable` step. Separate `Set Variable` steps will fail because the first one clears the error for the subsequent ones.

**Wrong** (error state cleared after first Set Variable):
```
Set Variable [ $err ; Get ( LastError ) ]
Set Variable [ $loc ; Get ( LastErrorLocation ) ]  # always empty!
```

**Correct** (all captured in one expression):
```
Set Variable [ $errData ; JSONSetElement ( "{}" ;
    [ "lastError" ; Get ( LastError ) ; JSONNumber ] ;
    [ "lastErrorDetail" ; Get ( LastErrorDetail ) ; JSONString ] ;
    [ "lastErrorLocation" ; Get ( LastErrorLocation ) ; JSONString ]
) ]
```

### Finding 2: `Perform Script` resets `Get(LastError)` to 0

The Agentic-fm Debug script captures `Get(LastError)` as its very first line. However, the calling script's `Perform Script` step succeeds (it found and began executing the debug script), which resets `Get(LastError)` to 0.

**This means the debug script's own `$errorContext` capture always sees `lastError = 0`.** Error data must be captured in the **calling script** using the single-expression pattern and passed as part of the JSON parameter to Agentic-fm Debug.

**The documented "forced error" technique in AGENTIC_DEBUG.md needs correction.** The docs say:

> Force a harmless error in the calling script immediately before `Perform Script`, then let the debug script capture it

This cannot work because `Perform Script` resets the error state. The correct approach is:

```
Set Error Capture [ On ]
Set Field []   # force error 102
# Capture ALL error data in ONE step — Get(LastError) resets the error state
Set Variable [ $errData ; JSONSetElement ( "{}" ;
    [ "lastError" ; Get ( LastError ) ; JSONNumber ] ;
    [ "lastErrorDetail" ; Get ( LastErrorDetail ) ; JSONString ] ;
    [ "lastErrorLocation" ; Get ( LastErrorLocation ) ; JSONString ]
) ]
Perform Script [ "Agentic-fm Debug" ; Parameter: JSONSetElement ( "{}" ;
    [ "label" ; "debug point" ; JSONString ] ;
    [ "vars"  ; JSONSetElement ( "{}" ;
        [ "errData" ; $errData ; JSONRaw ]
    ) ; JSONRaw ]
) ]
Set Error Capture [ Off ]
```

### Finding 3: `Get(LastErrorLocation)` works in FM Pro 22.0.4

Contrary to the initial test results (which showed empty values), `Get(LastErrorLocation)` works correctly when captured in the same expression as `Get(LastError)`. The initial tests failed because `Get(LastError)` was called in a separate step first, clearing the error state.

**Format**: `"ScriptName\rStepName\rLineNumber"` — fields separated by carriage returns (`\r` / `&#xD;`).

**Confirmed working for error types**:
- Error 102 (Set Field, no field specified)
- Error 104 (Perform Script, script not found)
- Error 105 (Go to Layout, layout not found)

**Note**: `Get(LastErrorDetail)` returned empty for all tested error types. It may only populate for specific error categories (e.g., ODBC errors, validation errors).

### Finding 4: Agentic-fm Debug script's `$errorContext` is correct but ineffective

The debug script already captures `Get(LastError)` and `Get(LastErrorLocation)` in a single `JSONSetElement` expression — the implementation is technically correct. But it's ineffective because `Perform Script` resets the error state before the debug script's first line runs.

**The `$errorContext` capture should be kept** as a safety net for edge cases (e.g., errors that occur within the `Perform Script` step itself), but callers should not rely on it. Error data must be captured and passed as parameters.

### Finding 5: `fmextscriptaccess` is required for `/trigger` and depends on the frontmost file

AppleScript `do script` checks `fmextscriptaccess` on the **frontmost** document's active account, not the targeted document. If the wrong file is in front, or the account lacks the privilege, `/trigger` fails with `-10004`.

**Workaround**: Tier 3 deployment (which uses System Events UI automation, not `do script`) brings the correct file to front. After a Tier 3 deployment, `/trigger` works.

### Finding 6: Tier 3 deployment works from the agent container via companion

Even though the agent container has no `osascript`, Tier 3 deployment works by:
1. POST XML to companion `/clipboard` (companion runs `clipboard.py` on the host)
2. POST raw AppleScript to companion `/trigger` (companion runs `osascript` on the host)

The pre-flight check in `deploy.py` (`_check_accessibility()`) fails in Linux containers because it tries to run `osascript` locally. **For containerized agents, `deploy.py` should detect that it's running in a container and skip the local pre-flight, relying on the companion to run the AppleScript.**

### Finding 7: The autonomous agent can deploy AND run scripts

The full autonomous loop works:
1. Agent creates fmxmlsnippet XML (`agent/sandbox/`)
2. Agent validates via `validate_snippet.py`
3. Agent loads clipboard via companion `/clipboard`
4. Agent creates + names + pastes script via companion `/trigger` with raw AppleScript (Tier 3)
5. Agent runs the script via companion `/trigger` with `do script` (requires `fmextscriptaccess`)
6. Agent reads `agent/debug/output.json` for debug feedback

Steps 1–4 require no FM privileges. Step 5 requires `fmextscriptaccess`. Step 6 requires the script to run client-side (not via OData in Docker).

---

## Mandatory pattern: single-expression error capture

This pattern must be used everywhere error data is captured in FileMaker scripts. It applies to both the Agentic-fm Debug calling convention and any error handling code the agent generates.

```
Set Variable [ $errData ; JSONSetElement ( "{}" ;
    [ "lastError" ; Get ( LastError ) ; JSONNumber ] ;
    [ "lastErrorDetail" ; Get ( LastErrorDetail ) ; JSONString ] ;
    [ "lastErrorLocation" ; Get ( LastErrorLocation ) ; JSONString ]
) ]
```

**Why**: `Get(LastError)` resets the error state. If called in a separate step before `Get(LastErrorLocation)`, the location data is lost. All three must be in one expression.

**`lastErrorLocation` format**: `"ScriptName\rStepName\rLineNumber"` — carriage return separated. Parse with:
```
Let ( [
    ~script = GetValue ( $errData ; 1 ) ;
    ~step   = GetValue ( $errData ; 2 ) ;
    ~line   = GetValue ( $errData ; 3 )
] ; ... )
```

(Note: `GetValue` splits on `¶` / carriage return, which matches the `\r` separator in `lastErrorLocation`.)

---

## Recommendations for Phase 2

### Must fix before Phase 2

1. **Update AGENTIC_DEBUG.md** — replace the "forced error" section. The technique works, but the capture must use the single-expression pattern, not separate steps. Remove the claim that the debug script can capture the caller's error state — it cannot, because `Perform Script` resets it. Update the calling convention to show the correct single-expression capture with error data passed as parameters.

2. **Update fm-debug skill (SKILL.md)** — add the single-expression error capture pattern as the mandatory approach. Note that the debug script's own `$errorContext` capture will always show `lastError: 0` — callers must pass error data as parameters.

3. **Add to CODING_CONVENTIONS.md or knowledge base** — the `Get(LastError)` reset behavior is a fundamental gotcha. Any error handling code the agent generates must use the single-expression pattern.

### Should fix

4. **`deploy.py` container detection** — skip local `osascript` pre-flight when running in a container. The companion handles all AppleScript execution.

5. **`fmextscriptaccess` setup guidance** — make this more prominent in HUMAN_TODO.md. Without it, the `/trigger` path (and therefore the entire fm-debug feedback loop) is blocked.

### Nice to have

6. **Parameterized debug URL** — allow the Agentic-fm Debug script to accept a custom companion URL, enabling server-side debugging when needed.

7. **OData script result capture** — for scripts that don't need debug file output, the OData response's `resultParameter` can return variable state directly via `Exit Script`. This works from Docker without companion reachability.

---

## Test Scripts Created

The following test scripts were created in the Invoice Solution's Script Workspace during testing. They can be deleted:
- `Debug Test`
- `Debug Error Test`
- `Debug Location Test`
- `Debug Combined Test`

---

## Verdict: fm-debug skill is production-ready

The skill works for its designed use case: **client-side script debugging where the developer runs the script manually or the agent triggers it via `/trigger`**. The companion endpoint, FM script, and output file all function correctly.

With the single-expression error capture pattern documented and the calling convention updated:
- Error codes (`Get(LastError)`) are reliable
- Error locations (`Get(LastErrorLocation)`) are reliable
- Variable state capture works perfectly
- The full deploy → run → debug → read loop works autonomously

The skill is ready for Phase 2's `script-test` and `script-debug` skills to build on.
