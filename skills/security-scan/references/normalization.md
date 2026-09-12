# Normalization, dedup, and triage rules

`merge_findings.py` does the **deterministic** work: parse → dedupe on exact keys →
assign stable IDs → emit `findings.jsonl` + `merged.sarif`. This file documents what
it does (so you can trust its output) and the **judgment** left to you afterward.

## Finding model (spec §6)

```jsonc
Finding {
  id, category: "sast"|"sca"|"secret",   // "iac" is Phase 3
  title, severity, confidence,
  cwe: [], cve: [], aliases: [],         // aliases = every advisory id seen
  package: {name, installed_version, fixed_version} | null,   // SCA only
  location: {file, start_line, end_line} | null,
  fingerprint, description, recommendation,
  rule_ids: [], severity_sources: {tool: native_sev},
  source_tools: []                       // MUST be non-empty (provenance)
}
```

## De-dup keys (spec §7) — done by the script

- **SCA** — merge when same `(package, installed_version)` **and** alias sets
  intersect. Snyk emits `identifiers.CVE/GHSA`, OSV emits `aliases`; the script
  unions them, so `GHSA-…` ↔ `CVE-…` resolve without a network call. No-alias
  advisories (Snyk's pre-CVE/curated tail) fall back to `package@version` + vendor
  id and therefore **cannot collide** with a CVE finding — exactly the surviving
  unique tail we want.
- **SAST** — key `(normalized_path, start_line, CWE-set)`. Rule IDs are
  tool-specific, so CWE + location is the cross-tool key; each tool's `rule_id` is
  kept as evidence on the merged finding.
- **Secrets** — key = `fingerprint` (`path:rule:line` / gitleaks fingerprint /
  trufflehog redacted hash). **Never dedupe on plaintext.**

Merged findings list **every** contributing tool in `source_tools` (agreement =
higher confidence).

## Severity — CVSS wins, never guess

The script normalizes each tool's native severity to `critical|high|medium|low|info`
and keeps the **max** across tools in `severity`, with every native value in
`severity_sources`. Your triage job:

- When tools **disagree**, prefer the **CVSS (NVD)** rating over a tool-native label.
  Use a CVSS score already present in the scanner output; **do not fetch** one and do
  **not** invent a score.
- A finding with `severity: null` had **no** severity in any tool's output. Report it
  as **unrated** — do **not** assign a severity from memory.

## OWASP bucketing (your job, from CWE)

Map each finding's CWE to its OWASP Top-10 (2021) category for the report, e.g.
`CWE-89 → A03:2021-Injection`, `CWE-79 → A03:2021-Injection`,
`CWE-798/CWE-259 → A07:2021-Identification and Authentication Failures`,
`CWE-22 → A01:2021-Broken Access Control`, `CWE-502 → A08:2021-Software and Data
Integrity Failures`. No CWE → leave the OWASP bucket blank; don't guess.

## Exclusion list (documented noise — filter, don't delete)

Move these to the **Skipped/excluded appendix**, never silently drop them:
DoS / resource-exhaustion, rate-limiting, verbose error messages, missing security
headers on non-sensitive routes, and self-XSS. If unsure, **keep** the finding.

## The boundary you may not cross

The script guarantees `orphan_findings` is empty — every emitted finding came from a
scanner. When you write prose you may **normalize, dedupe-judge ambiguous matches,
rank, bucket, and recommend**. You may **not** add a finding no scanner produced —
not from your own knowledge of a package, not "for completeness". Extra context on a
*real* finding (e.g. "this is the AWS docs placeholder key") is fine and belongs in
its description; a brand-new finding is not.
