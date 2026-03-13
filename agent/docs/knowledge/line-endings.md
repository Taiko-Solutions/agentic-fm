# Line Endings and the Paragraph Character (¶)

## What ¶ is

FileMaker's native line ending is the **carriage return** (CR), inherited from its Mac legacy origins:

```
Code ( ¶ ) = 13        // CR, not LF, not CRLF
Char ( 13 ) = ¶
```

`¶` is not a display symbol — it is the actual character with ASCII code 13, used everywhere FileMaker stores multi-line text: field values, variable values, value lists, and dialog messages.

## Using ¶ in calculations

`¶` is a valid **unquoted literal** in a calculation expression, but only as a single character. This is one of FileMaker's few non-string, non-operator bare tokens.

| Expression | Valid? | Notes |
|-----------|--------|-------|
| `"text" & ¶ & other` | ✅ | Single unquoted ¶ is a valid literal |
| `"text" & ¶¶ & other` | ❌ | Two unquoted ¶ is not valid syntax — parser error |
| `"text" & "¶¶" & other` | ✅ | Two ¶ inside a quoted string — valid |
| `"text¶¶" & other` | ✅ **preferred** | Embed in adjacent string — fewest tokens |

**The common mistake:** writing `& ¶¶ &` to get a blank line between two values. This is a syntax error. The correct forms are `& "¶¶" &` or, when one side is a string literal, embedding the returns inside it: `"label:¶¶" & value`.

### When to embed vs. when to quote

- **Embed** when the ¶ is adjacent to a string literal that is already there:
  ```
  // Good
  "Error: " & $code & "¶¶" & "Please try again."

  // Also good — fewer concatenation operators
  "Error: " & $code & ¶ & ¶ & "Please try again."  // valid but verbose
  ```
- **Quote** when the ¶ is between two non-literal expressions:
  ```
  $label & "¶¶" & $value
  ```
- **Never** leave multiple ¶ unquoted between `&` operators.

## Literal returns in the calculation dialog

When typing directly inside FileMaker's calculation dialog and you press the **Return or Enter key inside a quoted string**, FileMaker does **not** insert a CR. It inserts a space:

```
Code ( "
" ) = 32     // that looks like an empty line but is Code 32 — a space
```

This is unexpected. The calculation editor treats Enter as a formatting key (for indentation), not a character insertion. The result is a space character silently embedded in your string. Always use `¶` or `Char ( 13 )` — never a literal keypress — to represent a line break in a calculation.

## Converting line endings for external systems

FileMaker's CR-only line endings are not compatible with most external systems:

| System expectation | Encoding | Conversion |
|-------------------|---------|-----------|
| Unix / macOS files, HTTP bodies, JSON | LF — `Char ( 10 )` | `Substitute ( text ; ¶ ; Char ( 10 ) )` |
| Windows files | CRLF — `Char ( 13 ) & Char ( 10 )` | `Substitute ( text ; ¶ ; Char ( 13 ) & Char ( 10 ) )` |
| FileMaker internal | CR — `Char ( 13 )` = `¶` | no conversion needed |

For **text-to-text** conversion (transforming a text value in a variable or field), FileMaker has no built-in function — use `Substitute` in a calculation, or a custom function if the conversion is used in many places.

For **text-to-file** conversion (producing a container value ready for export or Insert File), use `TextEncode ( text ; encoding ; lineEndings )`. It returns container data — not text — with the specified character encoding and line endings:

| `lineEndings` value | Output line ending |
|---|---|
| `1` | Unchanged |
| `2` | CR — `Char ( 13 )` |
| `3` | LF — `Char ( 10 )` |
| `4` | CRLF — `Char ( 13 ) & Char ( 10 )` |

```
#// Write a FileMaker text value to a data file with Unix line endings
Set Variable [ $encoded ; Value: TextEncode ( $text ; "utf-8" ; 3 ) ]
Write to Data File [ File ID: $fileID ; Data source: $encoded ; Write as: UTF-8 ; Append line feed: Off ]
```

`TextEncode` **can** be assigned to a script variable — the variable holds container data, not text. `GetAsText` on the result returns the auto-assigned filename (`utf-8.txt`), and `GetContainerAttribute` returns meaningful values (`filename`, `fileSize`). What it cannot do is participate in text concatenation — `Substitute` remains the correct tool for in-calculation text-to-text conversion.

**`TextDecode` normalizes back to CR.** Calling `TextDecode ( $encoded ; "utf-8" )` on a `TextEncode` result returns text with FileMaker's native CR (Code 13) line endings, regardless of what encoding was used. The external line endings are not preserved in the returned text value.

**`Read from Data File` does NOT normalize.** When a file written via `TextEncode` (LF) is read back with `Read from Data File` using UTF-8 encoding, the returned variable contains LF (Code 10) line endings. Always normalise with `Substitute` after reading if the script needs to process the text using FileMaker line-structure operations.

### Incoming text from external sources

Text imported from files or received from HTTP responses may contain LF (`Char ( 10 )`) or CRLF (`Char ( 13 ) & Char ( 10 )`). FileMaker does not normalise these automatically. Comparisons and `PatternCount` against `¶` will miss them. Normalise on arrival:

```
// Normalise CRLF and bare LF to ¶ before processing
Substitute (
    Substitute ( $rawText ; Char ( 13 ) & Char ( 10 ) ; ¶ ) ;
    Char ( 10 ) ; ¶
)
```

Always normalise before any text processing that relies on line structure (splitting lists, counting lines, etc.).

## Quick reference

| Want | Use |
|------|-----|
| One line break | `¶` or `Char ( 13 )` |
| Two line breaks (blank line) | `"¶¶"` or `Char ( 13 ) & Char ( 13 )` |
| Unix LF | `Char ( 10 )` |
| Windows CRLF | `Char ( 13 ) & Char ( 10 )` |
| Code of ¶ | `13` |
| Code of LF | `10` |

## References

| Name | Type | Local doc | Claris help |
|------|------|-----------|-------------|
| Char | function | `agent/docs/filemaker/functions/text/char.md` | [char](https://help.claris.com/en/pro-help/content/char.html) |
| Code | function | `agent/docs/filemaker/functions/text/code.md` | [code](https://help.claris.com/en/pro-help/content/code.html) |
| Substitute | function | `agent/docs/filemaker/functions/text/substitute.md` | [substitute](https://help.claris.com/en/pro-help/content/substitute.html) |
| TextEncode | function | `agent/docs/filemaker/functions/container/textencode.md` | [textencode](https://help.claris.com/en/pro-help/content/textencode.html) |
| TextDecode | function | `agent/docs/filemaker/functions/container/textdecode.md` | [textdecode](https://help.claris.com/en/pro-help/content/textdecode.html) |
| Read from Data File | step | `agent/docs/filemaker/script-steps/read-from-data-file.md` | [read-from-data-file](https://help.claris.com/en/pro-help/content/read-from-data-file.html) |
