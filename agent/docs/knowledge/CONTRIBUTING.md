# Contributing Knowledge Base Articles

## Purpose

The knowledge base captures FileMaker behavioral intelligence that an AI would otherwise get wrong. These are not tutorials or beginner guides — they are targeted documents that prevent incorrect code generation by explaining nuances, gotchas, and idiomatic patterns that cannot be derived from official documentation alone.

Every article that exists here improves every script the agent writes on topics it covers. Contributions from developers with real-world experience are how this collection grows.

## What Makes a Good Article

A good article addresses **a behavior an AI would confidently get wrong** — not a behavior that is obvious from the FileMaker help docs.

Good candidate questions to ask before writing:

- Would a developer coming from another language make a predictable mistake here?
- Does FileMaker behave differently from what its UI or documentation implies?
- Is there a known gotcha that causes subtle bugs in production scripts?
- Is there an idiomatic FileMaker pattern that an AI tends to substitute with a worse alternative?

An article does NOT need to cover a topic exhaustively. It should be focused and actionable — the AI reads it in context right before writing a script.

## Article Format

Follow the structure used in the existing articles (`single-pass-loop.md`, `found-sets.md`):

```
# Title

**NOTE:** Items marked with **(step)** are script steps. Items marked with **(function)**
are calculation functions. [Include this line if the article mentions both.]

## Section Heading

Body text. Use concrete examples where the behavior is non-obvious.

### Sub-section (if needed)

Code examples use triple-backtick blocks with no language tag for HR scripts,
and ```xml for XML snippets.

## References

| Name | Type | Local doc | Claris help |
|------|------|-----------|-------------|
| Step Name | step | `agent/docs/filemaker/script-steps/<slug>.md` | [slug](https://help.claris.com/en/pro-help/content/<slug>.html) |
| FunctionName | function | `agent/docs/filemaker/functions/<category>/<slug>.md` | [slug](https://help.claris.com/en/pro-help/content/<slug>.html) |
```

**Required sections:** at least one substantive body section, and a References section.

**Length:** aim for 80–150 lines. Long enough to be useful; short enough to be read in full before a script is written.

**Slug rules** (for the References table):
- Steps: lowercase, hyphen-separated — `Replace Field Contents` → `replace-field-contents`
- Functions: lowercase, no separators — `GetNthRecord` → `getnthrecord`
- Local step path: `agent/docs/filemaker/script-steps/<slug>.md`
- Local function path: `agent/docs/filemaker/functions/<category>/<slug>.md`
- Claris URL: `https://help.claris.com/en/pro-help/content/<slug>.html`

## Submission Process

1. Fork the repository.
2. Add your article to `agent/docs/knowledge/` using a lowercase-kebab-case filename (e.g., `portal-filtering.md`).
3. Add a row to the table in `agent/docs/knowledge/MANIFEST.md` with the filename, a one-sentence description, and relevant keywords. Keywords are how the agent discovers the article — be specific and include terms a developer would use.
4. Open a pull request. The PR description should explain which AI mistake or common developer error the article addresses.

## Review Criteria

A contribution will be accepted if it meets these criteria:

- **Accurate** — the behavior described is correct and tested in a real FileMaker solution, not inferred from docs or memory.
- **Targeted** — the article addresses a specific behavior, not a broad topic. "Portals" is too broad; "Portal row context when running a script from a button inside a portal" is right.
- **Idiomatic** — code examples follow the conventions in `agent/docs/CODING_CONVENTIONS.md`. Variable prefixes, Let() formatting, and boolean conventions must be correct.
- **Not redundant** — the topic is not already covered in an existing article or is a meaningful extension of one.
- **References complete** — every step and function mentioned in the body has an entry in the References table.

## Good Topic Ideas

Areas not yet covered that are known sources of AI mistakes:

1. **Portal row context** — what `Get ( ActivePortalRowNumber )` returns, when portal scripts fire, and when context is lost
2. **Global fields in server scripts (PSOS)** — why `$$` globals from the client are not visible server-side, and how to pass state through script parameters instead
3. **Transactions** — `Open Transaction` / `Commit Transaction` semantics, rollback behavior, and what happens when a transaction is open during `Perform Script on Server`
4. **Record locking** — when FileMaker locks a record, what error 301 means in practice, and why `Open Record/Request` followed by `Commit Records` is the correct pattern for server-side edits
5. **Container fields** — `GetContainerAttribute`, `GetAs`, `Base64Encode`, exporting vs. referencing, and embedded vs. referenced storage implications
6. **ExecuteSQL** — zero-based column indexing, the `fieldSeparator` and `rowSeparator` params, NULL handling, and why it cannot reference unstored calc fields
7. **External SQL (ESS)** — shadow table behavior, why field names appear doubled, and commit timing differences
8. **Privilege set and account scripting** — `Get ( AccountPrivilegeSetName )`, re-login flow, and the limitation that `Change Password` requires the user to be the current account
9. **Data API patterns** — session token lifecycle, the difference between Data API and PSOS for server-side work, and common response parsing mistakes
10. **Custom menus** — UUID requirements, why pasted menus without matching UUIDs are silently ignored, and the `ut16` clipboard class requirement
11. **Value list sourcing** — conditional value lists driven by relationships, why they require an indexed field, and when `GetValue` is the correct retrieval method
12. **Script triggers** — which triggers fire before vs. after a commit, `OnRecordCommit` vs. `OnObjectSave`, and how to prevent infinite trigger loops
13. **Window management** — card window constraints, why `Close Window` from inside a card returns to the host window, and the interaction between card windows and `Allow User Abort`
14. **Date and time arithmetic** — FileMaker's date serial number origin, why adding 30 to a date works but subtracting months does not, and the correct approach using `Date ( Month ( d ) - 1 ; Day ( d ) ; Year ( d ) )`
15. **Summary fields and GetSummary** — why `GetSummary` returns `?` outside a sorted context, the requirement for the break field to match the current sort, and the difference between a leading vs. trailing summary part

## Bad Topic Ideas

Do not submit articles that:

- **Explain FileMaker basics** already covered in official help docs — "how to create a relationship", "what a portal is", "how to use Perform Find". The agent already has access to those docs.
- **Cover vendor-specific plugins** — MBS, BaseElements, 360Works, etc. Plugin behavior belongs in plugin-specific documentation, not this knowledge base.
- **Document version-specific features without a callout** — if something only applies to FileMaker 2024 or later, the article must prominently call that out. Articles that silently assume a version cause incorrect generation on older solutions.
- **Duplicate existing articles** — check the MANIFEST.md table before writing. If an existing article covers the topic partially, consider opening a PR to extend it instead.
- **List every possible option for a step** — the step catalog already does that. Knowledge articles explain *behavior*, not parameter lists.
