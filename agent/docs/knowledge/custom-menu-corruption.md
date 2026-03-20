# Custom Menu Corruption and `<Unknown>` Errors

## The Problem: Recover Reports `<Unknown>` on Custom Menus

When running **Recover** on a FileMaker file, the consistency check may report `<Unknown>` errors associated with custom menus. These are not necessarily true file corruption — they are typically caused by a specific configuration mistake in the custom menu hierarchy.

## Custom Menu Hierarchy

FileMaker custom menus have three levels:

1. **Custom Menu Sets** — the top level. A menu set is either the standard FileMaker menus or a custom set. A menu set contains one or more custom menus.
2. **Custom Menus** — each menu (e.g., File, Edit, Records) within a menu set.
3. **Menu Items** — individual items within a custom menu. Each menu item has a type:
   - **Command** — executes an action
   - **Submenu** — opens a nested menu
   - **Separator** — visual divider

Menu items can be **based on an existing command** (inheriting the default FileMaker behavior for that command) with optional overrides for name, keyboard shortcut, and action.

## The Configuration That Causes `<Unknown>`

When a custom menu item is **based on an existing command** but does **not** have all three override checkboxes checked:

- Override default **title/name**
- Override default **keyboard shortcut**
- Override default **action**

...then the Recover process flags it as `<Unknown>`. The Manage Custom Menus dialog does not warn about this — it happily accepts the configuration. The inconsistency only surfaces during a Recover operation.

## The Fix

For every custom menu item that has **"Based on existing command"** checked:

1. **Uncheck** "Based on existing command" entirely, **OR**
2. **Check all three** "Override default behavior" options (title, shortcut, and action)

Option 1 is the safer approach when you are defining a fully custom action. Option 2 is appropriate when you want to start from an existing command but customize all aspects of it.

## Key Takeaway: Recover Errors Are Not Always Corruption

FileMaker's Recover tool is stricter than the runtime engine. A file can run perfectly in production while Recover flags issues that are really configuration problems, not data corruption. Custom menu `<Unknown>` errors are a prime example — the menus work fine at runtime, but the internal representation does not meet Recover's validation rules.

This distinction matters when evaluating file health: an `<Unknown>` error in Recover should prompt investigation of the custom menu configuration, not an immediate assumption that the file is corrupt and needs to be rebuilt.

## Prevention

When creating custom menus (either manually or via fmxmlsnippet):

- If the menu item is fully custom (not based on any existing command), **uncheck** "Based on existing command."
- If the menu item is based on an existing command, **always override all three behaviors** — even if you want to keep the default for one of them. Set the override to the same value as the default rather than leaving it unchecked.
- After creating or modifying custom menus, run a Recover (on a copy) to verify no `<Unknown>` flags appear.

## References

| Name | Type | Local doc | Claris help |
|------|------|-----------|-------------|
| Recover | feature | — | [recovering-files](https://help.claris.com/en/pro-help/content/recovering-files.html) |
