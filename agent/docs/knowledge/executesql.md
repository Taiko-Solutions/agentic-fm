# ExecuteSQL

**NOTE:** Items marked with **(function)** are calculation functions used inside expressions. Items marked with **(step)** are script steps.

## What ExecuteSQL Is (and Is Not)

`ExecuteSQL` **(function)** executes a SQL `SELECT` query against the FileMaker internal SQL engine and returns a text result. It is **not** the same as the `Execute SQL` **(step)**, which sends SQL to external ODBC data sources. The function:

- Supports **only** `SELECT` — no `INSERT`, `UPDATE`, `DELETE`, `CREATE TABLE`, or any DDL/DML. Those statements are available only through ODBC/JDBC drivers, not through the calculation function.
- Operates **independently of layout context** — it queries the base table behind a table occurrence, ignoring the current found set, sort order, and layout. No layouts or relationships are required.
- Queries **table occurrences** (TOs) from the relationship graph, not base tables directly. The TO must exist in the current file's graph. However, the query evaluates as if the base table were selected — it does **not** filter through the relationship.
- Returns results for **all records** with access privileges, not just the current found set.
- Does **not** require fields to be on any layout.

## Syntax

```
ExecuteSQL ( sqlQuery ; fieldSeparator ; rowSeparator { ; arguments... } )
```

- `fieldSeparator` — delimiter between columns. Default (empty string `""`) is comma.
- `rowSeparator` — delimiter between rows. Default (empty string `""`) is carriage return (Char 13).
- `arguments` — optional positional parameters substituted for `?` placeholders in the query.

The `?` placeholder can appear anywhere in the `SELECT` statement — not just in `WHERE`. Use them to avoid SQL injection and to pass FileMaker values cleanly into queries.

## Case Sensitivity

**SQL queries in ExecuteSQL are case-sensitive for data comparison.** `WHERE LastName = 'smith'` will not match `'Smith'`. This is different from FileMaker's native Find, which is case-insensitive.

To perform case-insensitive comparisons, wrap the column in `UPPER()` or `LOWER()`:

```
ExecuteSQL (
    "SELECT FirstName, LastName FROM Contacts WHERE UPPER(LastName) LIKE ?" ;
    "" ; "" ;
    "SM%"
)
```

Table and column **names** are case-insensitive (`"my table"` = `"My Table"`). SQL keywords are also case-insensitive (`SELECT` = `select`).

## Date, Time, and Timestamp Formats

ExecuteSQL accepts **only** the SQL-92 ISO format with no braces:

| Type | Format | Example |
|------|--------|---------|
| Date | `DATE 'YYYY-MM-DD'` | `DATE '2024-01-15'` |
| Time | `TIME 'HH:MM:SS'` | `TIME '14:30:00'` |
| Timestamp | `TIMESTAMP 'YYYY-MM-DD HH:MM:SS'` | `TIMESTAMP '2024-01-15 14:30:00'` |

The ODBC/JDBC brace format (`{D '2024-01-15'}`) is **not** accepted by ExecuteSQL — it is only valid when connecting through ODBC/JDBC drivers.

Date fields return results in `YYYY-MM-DD` format by default. To get a localized format like `MM/DD/YYYY`, wrap the column with `COALESCE(dateField, '')` or use `STRVAL()`.

Date arithmetic is limited: you can add or subtract **days only** (e.g., `hire_date + 30`). There is no built-in month or year arithmetic — use FileMaker's `Date()` function to construct boundary dates and pass them as `?` arguments.

## The `?` Return Value — Error Handling

When a query fails (syntax error, semantic error, missing field), ExecuteSQL returns the literal string `"?"`. There is no built-in error detail.

To diagnose:

1. Wrap the query in `EvaluationError ( Evaluate ( $query ) )` in the Data Viewer.
2. Error code **8309** = semantics error (logical problem — wrong field name, type mismatch).
3. Error code **8310** = syntax error (malformed SQL).
4. Store the query in a `$variable` and inspect it in the Data Viewer before passing it to ExecuteSQL.

## Reserved Words as Field or Table Names

If a FileMaker field or TO name collides with a SQL reserved keyword, you **must** quote it with double quotes in the query:

```
ExecuteSQL (
    "SELECT \"date\", \"order\", amount FROM Sales WHERE \"date\" >= ?" ;
    "" ; "" ;
    "2024-01-01"
)
```

Common collisions: `date`, `time`, `timestamp`, `order`, `group`, `user`, `value`, `key`, `name`, `index`, `level`, `read`, `set`, `table`, `column`, `select`, `check`, `default`, `current`, `first`, `last`, `next`, `right`, `left`, `month`, `year`, `day`, `hour`, `minute`, `second`.

The full reserved keyword list contains 200+ words. When in doubt, quote the identifier.

## Empty Strings vs. NULL

FileMaker does not store data for empty strings. This means:

```
SELECT * FROM test WHERE c = ''    -- returns NO records (always)
SELECT * FROM test WHERE c <> ''   -- returns NO records (always)
```

To find empty fields, use `IS NULL`:

```
SELECT * FROM test WHERE c IS NULL
```

To find non-empty fields, use `IS NOT NULL`.

## System Tables

ExecuteSQL can query three built-in virtual tables:

### `FileMaker_Tables`

Returns one row per **table occurrence** on the relationship graph:

| Column | Description |
|--------|-------------|
| `TableName` | TO name |
| `TableId` | TO unique ID |
| `BaseTableName` | Base table name |
| `BaseFileName` | FM filename containing the base table |
| `ModCount` | Number of schema changes committed |

### `FileMaker_Fields`

Returns one row per field for **all table occurrences**:

| Column | Description |
|--------|-------------|
| `TableName` | TO name |
| `FieldName` | Field name |
| `FieldType` | SQL data type (not FileMaker data type) |
| `FieldId` | Field unique ID |
| `FieldClass` | `Normal`, `Summary`, or `Calculated` |
| `FieldReps` | Number of repetitions |
| `ModCount` | Number of schema changes committed |

### `FileMaker_BaseTableFields` (v19.4.1+)

Same columns as `FileMaker_Fields` but returns fields for **base tables only** (no TO duplication). Uses `BaseTableName` instead of `TableName`.

## System Columns: ROWID and ROWMODID

Every table has two hidden system columns:

- `ROWID` — the record's unique ID (same as `Get ( RecordID )`).
- `ROWMODID` — the record's modification count (same as `Get ( RecordModificationCount )`).

```
SELECT ROWID, ROWMODID, Name FROM Contacts WHERE ROWMODID > 3
```

These are useful for change tracking and conflict detection without adding dedicated fields.

## Concatenation Operators

Two concatenation operators are available in ExecuteSQL queries:

- `||` (double pipe) — **recommended**, works reliably in all cases.
- `+` — works but is less predictable; can be confused with numeric addition.

```
SELECT LastName || ', ' || FirstName FROM Contacts
```

The `-` operator moves trailing blanks to the end rather than removing them. `FirstName - LastName` with `'ROBERT '` and `'JONES '` yields `'ROBERTJONES  '`.

## Aggregate Functions Cannot Be Nested Inside Other Functions

You **cannot** wrap an aggregate function inside another function. This is a FileMaker SQL limitation that returns error 8309:

```
# WRONG — returns ?
SELECT ROUND(SUM(Salary), 0) FROM Payroll

# CORRECT — nest the scalar function inside the aggregate
SELECT SUM(ROUND(Salary, 0)) FROM Payroll
```

## HAVING Must Repeat the Aggregate

ExecuteSQL does not allow using a column alias in the `HAVING` clause. You must repeat the full aggregate expression:

```
# WRONG — alias not recognized in HAVING
SELECT salespersonID, SUM(amount) AS total
FROM Sales
GROUP BY salespersonID
HAVING total > 150000

# CORRECT — repeat the aggregate
SELECT salespersonID, SUM(amount) AS total
FROM Sales
GROUP BY salespersonID
HAVING SUM(amount) > 150000
```

## No TOP, LIMIT, or ROWNUM

ExecuteSQL has **no row-limiting clause** within the function. Every matching record is returned. To get the first N values from the result, use FileMaker's `GetValue()` function on the result text:

```
Let (
    ~result = ExecuteSQL ( "SELECT Name FROM Contacts ORDER BY Name" ; "" ; "" ) ;
    GetValue ( ~result ; 1 )
)
```

Note: The `OFFSET` and `FETCH FIRST` clauses **do** exist in FileMaker's SQL implementation but are documented only for ODBC/JDBC use. They may work in ExecuteSQL in some versions but are not officially supported there — test before relying on them.

## JOIN Limitations

- `INNER JOIN` and `LEFT OUTER JOIN` are supported.
- `RIGHT OUTER JOIN` is **not** supported.
- `FULL OUTER JOIN` is **not** supported.
- Implicit joins (comma-separated tables in `FROM` with `WHERE` conditions) work and are equivalent to `INNER JOIN`.
- Self-joins require table aliases.

## Available SQL Functions

### String Functions

`CHR()`, `COALESCE()`, `LEFT()`, `LENGTH()`, `LOWER()`, `LTRIM()`, `RIGHT()`, `RTRIM()`, `SPACE()`, `SUBSTR()` / `SUBSTRING()`, `TRIM()`, `UPPER()`, `STRVAL()`

### Date/Time Functions

`CURDATE` / `CURRENT_DATE`, `CURTIME` / `CURRENT_TIME`, `CURTIMESTAMP` / `CURRENT_TIMESTAMP`, `DATEVAL()`, `TIMEVAL()`, `TIMESTAMPVAL()`, `TODAY`, `DAY()`, `MONTH()`, `YEAR()`, `HOUR()`, `MINUTE()`, `SECOND()`, `DAYNAME()`, `DAYOFWEEK()`, `MONTHNAME()`

Note: `DATE()` and `TIME()` are deprecated — use `CURRENT_DATE` and `CURRENT_TIME`.

`DAYOFWEEK()` returns 1 for Sunday through 7 for Saturday.

### Numeric Functions

`ABS()`, `ATAN()`, `ATAN2()`, `CEIL()` / `CEILING()`, `DEG()` / `DEGREES()`, `EXP()`, `FLOOR()`, `INT()`, `LN()`, `LOG()`, `MAX()` (scalar, 2 args), `MIN()` (scalar, 2 args), `MOD()`, `NUMVAL()`, `PI()`, `RADIANS()`, `ROUND()`, `SIGN()`, `SIN()`, `SQRT()`, `TAN()`

Note: `MAX()` and `MIN()` with two arguments are scalar functions (return the larger/smaller of two values). With one argument in a `SELECT`, they are aggregate functions.

### Aggregate Functions

`SUM()`, `AVG()`, `COUNT()`, `MAX()`, `MIN()`, `STDEV()`, `STDEVP()`

`COUNT(*)` counts all rows including those with NULL values. `COUNT(fieldName)` counts only non-NULL values.

### Conditional Functions

`CASE WHEN ... THEN ... ELSE ... END`, `COALESCE()`, `NULLIF()`

`IIF()`, `IF()`, and `CHOOSE()` do **not** work in ExecuteSQL. Use `CASE` instead.

### Conversion Functions

`CAST(expression AS type)` — converts between types. Supported target types: `VARCHAR`, `DOUBLE`, `DATE`, `TIME`, `TIMESTAMP`.

`NUMVAL()` converts dates to a day number (like `GetAsNumber(Get(CurrentDate))`) and times to seconds. `STRVAL()` converts any value to text. `COALESCE(dateField, '')` returns dates in localized `MM/DD/YYYY` format instead of ISO format.

## LIKE Wildcards

- `%` — matches zero or more characters (equivalent to `*` in FileMaker finds).
- `_` — matches exactly one character (equivalent to `@` in FileMaker finds — note the different symbol).

```
WHERE LastName LIKE 'A_a%'  -- A, any char, lowercase a, then anything
```

## Robust Coding: Preventing Breakage from Field/TO Renames

Field and table occurrence names in ExecuteSQL queries are **hardcoded strings**. If a field or TO is renamed in FileMaker, the query silently breaks and returns `?`.

To make queries rename-safe, use `GetFieldName()` to resolve field references dynamically:

```
Let (
    ~field = GetFieldName ( Contacts::LastName ) ;
    ExecuteSQL (
        "SELECT " & ~field & " FROM Contacts" ;
        "" ; ""
    )
)
```

This way, if `LastName` is renamed, `GetFieldName()` updates automatically and the query continues to work.

## Performance Considerations

### Commit Before ExecuteSQL in Scripts (Hosted Files)

When ExecuteSQL runs on a hosted file and the client has an **open (uncommitted) record** in the target table, FileMaker Server cannot execute the query server-side. Instead, **FMS sends the entire table's data to the client**, which then resolves the SQL query locally. On large tables this causes a dramatic slowdown — a query that normally returns in milliseconds can take seconds or longer due to the network transfer alone.

The mechanism: the server does not know which records the client needs to reconcile with its uncommitted changes, so it sends everything. Once the data arrives, the client's local cache retains it (mitigating repeat hits), but the initial transfer on a large table is devastating.

**Always issue a `Commit Records/Requests` step before calling ExecuteSQL in a script:**

```
Commit Records/Requests [ With dialog: Off ]
Set Variable [ $result ; Value: ExecuteSQL ( "SELECT Name FROM Contacts WHERE Status = ?" ; "" ; "" ; "Active" ) ]
```

This ensures all records are in a committed state so the server can execute the query and return only the result set. If committing is not desirable at that point in the script (e.g., mid-transaction or during a record edit the user hasn't confirmed), be aware of the performance penalty and consider restructuring the script flow.

**Scope:** Only the table(s) referenced in the query are affected. An open record in an unrelated table does not trigger the full-table download.

**PSOS as an alternative:** `Perform Script On Server` sidesteps the issue entirely — server-side execution has no "open record" client context, so the query always runs server-side. This can yield 5–10x speed improvements for ExecuteSQL-heavy operations.

**Single-user local files:** The performance penalty is negligible in non-hosted files since all data is already local. The issue is fundamentally a client-server network transfer problem.

### Avoid ExecuteSQL in Auto-Evaluated Contexts

ExecuteSQL in **unstored calculations, tooltips, conditional formatting, or object visibility calculations** is especially dangerous. These contexts re-evaluate continuously — including while a record is being edited (open). Each re-evaluation can trigger a full-table download from the server. Use ExecuteSQL in **scripts** where you control the record state, and store results in fields or variables rather than embedding queries in auto-evaluated expressions.

### General Performance

- ExecuteSQL queries are not cached — each evaluation runs the full query.
- Queries against indexed fields perform significantly better than against unstored calculations or unindexed fields.
- Using functions like `LOWER(field)` or `UPPER(field)` in `WHERE` clauses prevents the SQL engine from using the field's index for that predicate, regardless of record state. Prefer passing pre-formatted `?` arguments over wrapping columns in functions when possible.
- ExecuteSQL **cannot** query unstored calculation fields via ODBC/JDBC. Within the function, unstored calcs may evaluate but performance is poor on large record sets.
- For large result sets, consider whether a relationship or a native Find would be more efficient than ExecuteSQL.

## References

| Name | Type | Local doc | Claris help |
|------|------|-----------|-------------|
| ExecuteSQL | function | `agent/docs/filemaker/functions/logical/executesql.md` | [executesql](https://help.claris.com/en/pro-help/content/executesql.html) |
| GetFieldName | function | `agent/docs/filemaker/functions/logical/getfieldname.md` | [getfieldname](https://help.claris.com/en/pro-help/content/getfieldname.html) |
| Get ( RecordID ) | function | `agent/docs/filemaker/functions/get/get-recordid.md` | [get-recordid](https://help.claris.com/en/pro-help/content/get-recordid.html) |
| Get ( RecordModificationCount ) | function | `agent/docs/filemaker/functions/get/get-recordmodificationcount.md` | [get-recordmodificationcount](https://help.claris.com/en/pro-help/content/get-recordmodificationcount.html) |
| Commit Records/Requests | step | `agent/docs/filemaker/script-steps/commit-records-requests.md` | [commit-records-requests](https://help.claris.com/en/pro-help/content/commit-records-requests.html) |
