# Field References

**NOTE:** Items marked with **(step)** are script steps. Items marked with **(function)** are calculation functions used inside expressions. This distinction matters: script steps become `<Step>` elements in fmxmlsnippet output, while functions appear inside `<Calculation><![CDATA[...]]></Calculation>` blocks.

## The Problem with String-Based Field References

Several FileMaker script steps and functions accept field names as **text strings** rather than direct field references. When a field name is passed as a literal string (e.g., `"Invoices::Status"`), the script breaks silently if that field is later renamed. No error is raised -- the step simply fails to find the field.

## GetFieldName() for Refactoring Safety

`GetFieldName ( field )` **(function)** accepts a direct field reference and returns its fully qualified name as text at runtime. By wrapping field references in `GetFieldName()`, the calculation dialog validates the reference at design time and automatically updates the name if the field is renamed.

Using `GetFieldName()` is the **preferred** approach whenever a field name is passed as a string parameter. Literal strings are acceptable when the developer intentionally needs a dynamic or runtime-determined field name, but the default should favor `GetFieldName()` to protect less experienced developers from composing brittle code.

### When to use GetFieldName()

Use `GetFieldName()` any time a field name is passed as a **string parameter** rather than selected from a field picker:

- `Set Field By Name` **(step)** -- the first parameter (target field name) should use `GetFieldName()`
- `GetField()` **(function)** -- the field name parameter benefits from `GetFieldName()` when the target is known at design time
- `ExecuteSQL` **(function)** -- field names passed as arguments to dynamically construct a query should use `GetFieldName()` where possible
- `FieldNames()` **(function)** -- returns all field names; not directly applicable, but when comparing results against a known field, use `GetFieldName()` for the comparison value
- Any variable or parameter that holds a field name for later use in a dynamic context

### When NOT to use GetFieldName()

- When the field name is genuinely dynamic (e.g., user-selected from a value list at runtime)
- When iterating over `FieldNames()` output and the specific field is unknown at design time
- Inside `ExecuteSQL` SQL strings -- SQL column names are not FileMaker field references and cannot use `GetFieldName()` directly
- When the developer explicitly chooses a literal string for a specific reason

## Pattern: List of Field Names

A common use case is building a list of field names for multi-field operations (searching, clearing, validating).

### Brittle (breaks on rename)

```
Set Variable [ $fields ; Value:
	List (
		"Admin::Search Global" ;
		"Admin::Logo Global"
	)
]
```

If `Search Global` is renamed to `SearchText Global`, this silently fails.

### Preferred (rename-safe)

```
Set Variable [ $fields ; Value:
	List (
		GetFieldName ( Admin::Search Global ) ;
		GetFieldName ( Admin::Logo Global )
	)
]
```

The calculation dialog validates each field reference. If any field is renamed, the reference updates automatically.

## Pattern: Set Field By Name

### Brittle

```
Set Field By Name [ "Invoices::Status" ; "Sent" ]
```

### Preferred

```
Set Field By Name [ GetFieldName ( Invoices::Status ) ; "Sent" ]
```

## Pattern: GetField with Known Target

### Brittle

```
Set Variable [ $value ; Value: GetField ( "Invoices::Status" ) ]
```

### Preferred

```
Set Variable [ $value ; Value: GetField ( GetFieldName ( Invoices::Status ) ) ]
```

## Pattern: Dynamic Field in a Loop

When iterating over a list of field names to perform operations:

```
Set Variable [ $fieldList ; Value:
	List (
		GetFieldName ( Invoices::Date ) ;
		GetFieldName ( Invoices::Total ) ;
		GetFieldName ( Invoices::Status )
	)
]
Set Variable [ $i ; Value: 1 ]
Loop
	Set Variable [ $currentField ; Value: GetValue ( $fieldList ; $i ) ]
	Exit Loop If [ IsEmpty ( $currentField ) ]
	Set Field By Name [ $currentField ; "" ]
	Set Variable [ $i ; Value: $i + 1 ]
End Loop
```

## References

| Name | Type | Local doc | Claris help |
|------|------|-----------|-------------|
| Set Field By Name | step | `agent/docs/filemaker/script-steps/set-field-by-name.md` | [set-field-by-name](https://help.claris.com/en/pro-help/content/set-field-by-name.html) |
| GetFieldName | function | `agent/docs/filemaker/functions/logical/getfieldname.md` | [getfieldname](https://help.claris.com/en/pro-help/content/getfieldname.html) |
| GetField | function | `agent/docs/filemaker/functions/logical/getfield.md` | [getfield](https://help.claris.com/en/pro-help/content/getfield.html) |
| ExecuteSQL | function | `agent/docs/filemaker/functions/logical/executesql.md` | [executesql](https://help.claris.com/en/pro-help/content/executesql.html) |
| FieldNames | function | `agent/docs/filemaker/functions/design/fieldnames.md` | [fieldnames](https://help.claris.com/en/pro-help/content/fieldnames.html) |
