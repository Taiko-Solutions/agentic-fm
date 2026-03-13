# FileMaker Paste Dependency Order

When pasting FileMaker fmxmlsnippet objects into a solution via the clipboard, the order in which objects are installed matters. Each category of object may reference objects from the categories that precede it. Pasting out of order will result in broken references, missing lookups, or silent failures.

## Correct installation order

1. **Custom Functions** — referenced by field auto-enter calculations, field validation calculations, and script step calculations. Must exist before any object that calls them by name.
2. **Tables** — required before fields can be defined, since fields belong to a table.
3. **Fields** — may include auto-enter calculations and validation rules that reference custom functions and other fields. Tables and fields are often installed together as a unit.
4. **Value Lists** — may be based on field values and must reference tables and fields that already exist. If a value list references related data, missing relationships may cause broken value lists.
5. **Scripts** — script steps reference layouts, fields, value lists, scripts, and custom functions. All referenced objects must exist before the script is pasted.
6. **Layout Objects** — buttons, portals, fields on layouts, and other UI elements reference table occurrences, fields, value lists, and scripts by name or ID. All referenced objects must already exist.
7. **Script Steps** — when inserting individual steps into an existing script, the same rule applies: any field, layout, value list, or script referenced in a step must already exist in the solution.
8. **Custom Menus** — custom menu overrides reference scripts by name. Scripts must exist before menus are installed.

## Objects that cannot be copy/pasted

Some FileMaker objects cannot be transferred via copy/paste and must be created manually in the target solution:

**Relationships** — defined in the Relationships graph. When a script depends on a relationship for context (e.g., portal filtering, related field access, Go to Related Records), that relationship must be established separately before the script will function correctly.

**Layouts** — whole layouts cannot be copy/pasted between solutions. If a script references a layout (e.g., Go to Layout, Go to Related Records) that does not exist in the target solution, the reference will appear as missing and the script step will fail at runtime. Layouts must be recreated manually in the target solution before any script that navigates to them is installed.

## Practical notes

- **Custom functions first, always.** A field auto-enter calculation or script calculation that calls a custom function will break silently if the function does not exist yet.
- **Tables and fields together.** FileMaker's XML export typically includes fields within the table definition. When pasting a table block, the fields come along. If pasting fields separately, the table must already exist.
- **Scripts reference each other.** When a set of scripts includes callers and callees (Perform Script), paste all scripts first, then verify references resolve. FileMaker will accept the paste even if the target script does not yet exist — the reference will appear broken until the missing script is re-connected.
- **Layout objects are the most fragile.** They carry the most inter-object references (fields, value lists, scripts, table occurrences). Scripts must be installed before layout objects — buttons and script triggers reference scripts by name.
- **Custom menus last.** Menu overrides point to scripts by name; pasting menus before scripts means every override will be unresolved.

## Agent guidance

When an agent is asked to generate or install multiple object types in a single session, it should sequence its output and instructions to the developer in this order. If the developer pastes objects out of order and reports broken references, the likely cause is a dependency that was not yet present. Diagnose by checking which category the broken reference belongs to and whether its prerequisite category has been installed.
