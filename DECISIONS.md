# DECISIONS.md

## Architectural & Strategic Decisions

This document records major architectural and strategic decisions for **PDFEditor**, along with their rationale.

Its purpose is to preserve intent, prevent repeated debate, and guide future contributors and AI agents.

---

# 1. Licensing Strategy

**Date:** 2026-02-28

## Decision

* The repository is licensed under **MIT**.
* All dependencies must use **permissive licenses**.
* Primary PDF library: **`pypdf` (BSD-3-Clause)**.

## Rationale

* Enterprise compatibility
* Minimal legal friction for colleagues
* Avoid copyleft constraints (GPL / AGPL / MPL unless explicitly approved)

## Reconsider If

* A critical feature requires a different library
* A permissive alternative is not viable
* Legal approval is explicitly granted

---

# 2. Non-Destructive Editing Policy

**Date:** 2026-02-28

## Decision

Original PDFs must never be modified in place.

Edited files must use the suffix:

```
.edited.pdf
```

## Rationale

* Prevent irreversible content loss
* Maintain auditability
* Enable easy rollback
* Reduce enterprise risk

## Reconsider If

* A controlled workflow requires in-place editing
* Explicit backup mechanisms are added
* The change is guarded behind an opt-in flag

---

# 3. Empty Page Detection Philosophy

**Date:** 2026-02-28

## Decision

Default detection mode is:

* Structural (no rendering engine)
* Conservative
* Pages containing only annotations are considered empty by default

## Rationale

* Rendering engines increase complexity and licensing risk
* Structural inspection is deterministic and auditable
* Conservative behavior reduces false positives

## Reconsider If

* Real-world document corpus requires rendering-based detection
* A permissively licensed rendering approach is approved
* False-negative rate becomes operationally problematic

---

# 4. Bookmark / Outline Correction Policy

**Date:** 2026-02-28

## Decision

If a bookmark, outline entry, or named destination references a removed page:

* The reference is **dropped**
* It is not retargeted to another page

## Rationale

* Retargeting risks silently misleading users
* Dropping preserves correctness and transparency
* Removal is visible in the run report

## Reconsider If

* A clear, safe retargeting policy is defined
* Behavior is made configurable behind a flag
* Documentation is updated accordingly

---

# 5. Reporting Requirements

**Date:** 2026-02-28

## Decision

Every run must generate:

1. A machine-readable JSON report
2. A human-readable text report

Reports must include:

* Timestamp (local + UTC)
* Username
* Hostname
* Python version
* Dependency versions
* Per-file processing status
* Page removal counts
* Errors and warnings

## Rationale

* Enterprise auditability
* Debuggability
* Enables automation and monitoring
* Supports reproducibility

## Reconsider If

* Report size becomes problematic
* Structured logging framework is adopted
* A formal schema versioning system is introduced

---

# 6. Default Scope of Processing

**Date:** 2026-02-28

## Decision

* The tool processes all `*.pdf` files in the current directory.
* Processing is non-recursive by default.
* Recursive mode may be introduced later as an explicit flag.

## Rationale

* Predictable behavior
* Prevent accidental large-scale modifications
* Suitable for controlled enterprise workflows

## Reconsider If

* Bulk processing of directory trees becomes common
* Explicit recursive behavior is requested

---

# 7. No External Communication

**Date:** 2026-02-28

## Decision

The tool must:

* Make no network calls
* Send no telemetry
* Perform no cloud uploads
* Execute no dynamic code

## Rationale

* Enterprise safety
* Deterministic local execution
* Avoid security review friction

## Reconsider If

* Enterprise logging integration is formally required
* Security review approves controlled outbound logging

---

# 8. Deterministic Execution

**Date:** 2026-02-28

## Decision

Execution must be deterministic:

* No randomness
* No time-dependent logic affecting behavior
* Identical inputs produce identical outputs

Timestamps are allowed only in report metadata.

## Rationale

* Reproducibility
* Testability
* Audit reliability
