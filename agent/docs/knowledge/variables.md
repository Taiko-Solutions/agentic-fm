# Variables

**NOTE:** Items marked with **(step)** are script steps. Items marked with **(function)** are calculation functions used inside expressions. This distinction matters: script steps become `<Step>` elements in fmxmlsnippet output, while functions appear inside `<Calculation><![CDATA[...]]></Calculation>` blocks.

## Variable Scopes

FileMaker has three distinct variable scopes. The prefix character determines the scope — there is no keyword like `var` or `let`.

| Prefix | Scope | Lifetime | Example |
| ------ | ----- | -------- | ------- |
| `$` | Script-local | Current script call only | `$invoiceTotal` |
| `$$` | Global | Entire FileMaker session | `$$USER.ACCOUNT` |
| `~` | Calculation-local | Single `Let()` evaluation | `~lineTotal` |
| `$$~` | Private global | Session; documented as internal | `$$~PRIVATE.CACHE` |

Variables are created on first assignment. There is no declaration step and no type declaration — FileMaker infers the type from the value.

## `$` — Script-Local Variables

Local variables exist only for the duration of a single script execution. When the script exits — whether via `Exit Script` **(step)**, the end of the script, or an error — all `$` variables are deallocated automatically.

- **Sub-scripts do not inherit locals.** A `$variable` set in script A is not visible inside a script called via `Perform Script` **(step)**. Each script call has its own isolated local scope.
- Use locals for all intermediate values, counters, flags, and working data within a single script.
- Locals are the default choice. Reach for globals only when state must survive across script calls.

## `$$` — Global Variables

Global variables persist for the entire FileMaker session — from the moment the user opens the file until they close it (or until the variable is explicitly cleared). They are visible from any script, calculation, or layout object in the session.

### Common gotcha: stale globals from previous runs

Because globals persist across script calls, a global set in one script run is still present in the next. This causes subtle bugs when:

- A script sets `$$STATUS` to `"error"` and exits early without cleaning up. The next script run starts with `$$STATUS = "error"` from the previous run.
- A global accumulator (e.g., `$$LOG`) grows unboundedly across script runs because it is never cleared.
- A workflow sets a global to signal state to another script, but that signal fires unexpectedly because it was never cleared after the first use.

**Best practice:** Scripts that use globals for inter-script communication should clear them at the start or at the end:

```
#// Clear at start — defensive
Set Variable [ $$RESULT ; Value: "" ]

#// ...script work...

Set Variable [ $$RESULT ; Value: $computedValue ]
Perform Script [ "Consumer Script" ]

#// Clear after use — clean handoff
Set Variable [ $$RESULT ; Value: "" ]
```

### When to use globals vs locals

Use globals when:
- State must be shared between scripts that run in sequence (one script sets a value, the next reads it)
- A value must survive a `Perform Script` call and be visible to the calling script afterward
- A UI state (e.g., which panel is active, a selected record ID) must persist while the user navigates layouts

Use locals for everything else. Globals consume session memory and can cause hard-to-debug state contamination. A script that works in isolation may behave unexpectedly when called after another script that left globals in a dirty state.

### `$$` naming convention

Global variable names use ALL_CAPS with dots as namespace separators:

```
$$USER.ACCOUNT
$$USER.PRIVILEGE_SET
$$APP.MODE
```

This visually distinguishes globals from locals in script code and signals that the variable is shared state.

## `~` — Calculation-Local Variables (Let)

The `~` prefix marks variables scoped to a single `Let()` **(function)** evaluation. They exist only for the duration of that one calculation and are invisible outside it.

```
Let ( [
    ~subtotal = unitPrice * quantity ;
    ~discount = ~subtotal * $discountRate
] ;

    ~subtotal - ~discount
)
```

`~` variables:
- Are not accessible from script steps — they exist only within the `Let()` expression
- Are ideal for intermediate calculation values that have no meaning outside the expression
- Should use camelCase after the `~` prefix: `~lineTotal`, `~isTrailing`

## `$$~` — Private Globals

The `$$~` prefix convention marks a global that is intended for internal workflow use and should be cleaned up when the workflow is done. It communicates intent to other developers: this is not a long-lived application-level global.

```
$$~PRIVATE.CACHE
$$~TEMP.RECORD_ID
```

Use `$$~` for globals that span multiple scripts in a single workflow execution but should not persist after the workflow completes. Always clear them explicitly at the workflow's exit point.

## Performance Considerations

- Global variables remain allocated for the entire session. Avoid storing large text blobs, complete JSON payloads, or container data in globals.
- Prefer passing data via `Exit Script [ Result: ... ]` and `Get ( ScriptResult )` **(function)** rather than shuttling data through globals between scripts. This keeps data flow explicit and eliminates global cleanup requirements.
- If a script must cache a large lookup result in a global, document the cache key and provide a clear path for invalidation.

## The `Let()` Function and Variable Declaration

`Let()` is the only place `~` variables can be declared. In a script context, all variable assignment goes through `Set Variable` **(step)**. There is no way to declare a `~` variable from a script step — `~` is strictly a calculation-layer construct.

```
#// Script step — use $ or $$ only
Set Variable [ $result ; Value: Let ( [
    ~base = Table::amount ;
    ~tax  = ~base * 0.1
] ; ~base + ~tax ) ]
```

The `~` variables above exist only during the `Let()` evaluation on the right side of the `Set Variable`. The result is stored in `$result`.

## References

| Name               | Type     | Local doc                                                           | Claris help                                                                                         |
| ------------------ | -------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Set Variable       | step     | `agent/docs/filemaker/script-steps/set-variable.md`                 | [set-variable](https://help.claris.com/en/pro-help/content/set-variable.html)                       |
| Exit Script        | step     | `agent/docs/filemaker/script-steps/exit-script.md`                  | [exit-script](https://help.claris.com/en/pro-help/content/exit-script.html)                         |
| Perform Script     | step     | `agent/docs/filemaker/script-steps/perform-script.md`               | [perform-script](https://help.claris.com/en/pro-help/content/perform-script.html)                   |
| Let                | function | `agent/docs/filemaker/functions/logical/let.md`                     | [let](https://help.claris.com/en/pro-help/content/let.html)                                         |
| Get ( ScriptResult ) | function | `agent/docs/filemaker/functions/get/get-scriptresult.md`          | [get-scriptresult](https://help.claris.com/en/pro-help/content/get-scriptresult.html)               |
