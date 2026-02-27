# AGENTS.md

## AI Agent Operating Rules

This file defines how AI agents (Codex, ChatGPT, etc.) must behave in this repository.

---

## Prime Directive

Before making any changes, agents must read and follow (in order):

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `DECISIONS.md`

If instructions conflict:

* `AGENTS.md` takes precedence
* then `ARCHITECTURE.md`
* then `DECISIONS.md`

Agents must refresh context from these files before implementing changes.

---

## Scope of Modification

Agents may modify (edit, add, delete) contents of:

* Files in the repository root
* `src/`
* `tests/`
* `docs/` (if present)
* `.github/` (if present)

Agents must **NOT**:

* Change licensing terms in a way that conflicts with MIT licensing
* Add non-permissive dependencies
* Introduce network calls, telemetry, or data exfiltration
* Modify large binary files unless explicitly instructed

---

## Dependency Management

This project must use **permissively licensed** Python libraries suitable for enterprise use.

Rules:

* Prefer Python standard library when practical
* Primary PDF library: **`pypdf` (BSD-3-Clause)**
* Do not introduce new dependencies without explicit approval

If a task appears to require a library not already listed in `pyproject.toml`, the agent must stop and request approval.

---

## Change Rules

* Preserve existing behavior unless explicitly asked to change it
* Do not change public CLI flags or output formats without updating documentation and tests
* Any heuristic that may cause content loss must default to conservative behavior

---

## Coding Standards

* Prefer small, pure functions
* Use explicit type hints
* Add docstrings to all public modules and functions
* Keep code readable and explicit
* Avoid clever or implicit logic
* Prefer deterministic behavior

---

## Testing Requirements

* All logic changes must include tests (or update existing tests appropriately)
* Do not delete tests to resolve failures
* Add regression tests for bug fixes
* Tests must not modify real user files

---

## Reporting & Safety

Processing must be **non-destructive**:

* Never overwrite the original PDF
* Always write edited output to a new file using the suffix:

```
.edited.pdf
```

Every execution must produce:

* A machine-readable JSON run report
* A human-readable text run report

If a PDF cannot be processed safely, it must be skipped and the reason recorded in the report.

---

## Empty Page Policy (High-Level)

Default behavior:

* Structural detection (no rendering engine)
* Pages containing only annotations are treated as empty
* Detection must be conservative by default

Agents must not change default detection behavior without updating documentation and tests.

---

## Bookmark / Outline Policy

If a bookmark, outline entry, or named destination references a removed page:

* The reference must be **dropped**
* It must not be silently retargeted

This behavior is deliberate and must not change without updating `DECISIONS.md`.

---

## When to Ask for Clarification

Agents must stop and request clarification if:

* “Empty page” criteria need expansion or modification
* A proposed change may increase false positives
* A new dependency is required
* Output naming conventions need revision
* Report schema changes are required

---

## Security and Enterprise Constraints

* No external API calls
* No cloud uploads
* No telemetry
* No automatic updates
* No dynamic code execution

The tool must remain deterministic, local, and auditable.
