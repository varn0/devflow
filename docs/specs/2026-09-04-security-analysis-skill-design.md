# Security Analysis Skill — Design Spec

- **Date:** 2026-09-04
- **Status:** Implemented (2026-09-12) — skill at `skills/security-scan/`, built via `superpowers:writing-skills` (RED→GREEN→REFACTOR)
- **Author:** varno-devflow
- **Skill name:** `/security-scan` (`varno-devflow:security-scan`) — confirmed
- **Build method:** created with the `superpowers:writing-skills` skill once this spec is approved.

---

## 1. Goal

A Claude Code skill that runs a set of **best-in-class, low-overlap security scanners** over the codebase, **merges and de-duplicates** their findings into a single normalized model, and produces a **human-readable report plus machine-readable artifacts** for the user to evaluate.

The skill **detects and reports; it never fixes.** The user reviews the report and then decides, finding by finding, what (if anything) to remediate in a follow-up task.

### What "good" looks like

- One clean report instead of N noisy tool outputs.
- No duplicate findings when two tools report the same CVE / same line.
- Every finding is traceable to the tool(s) that raised it and to the exact commit scanned.
- Zero LLM-invented vulnerabilities — the LLM only normalizes, dedupes, ranks, categorizes, and writes prose. **All findings originate from a real scanner.**

---



## 2. Non-goals (explicitly out of scope for v1)

- **No auto-fixing / no patches.** Reporting only. Remediation is a separate, user-directed task.
- **No diff/MR-targeted mode** — v1 scans the whole repo. Diff-scoped scanning for merge requests is **Phase 2** (see Roadmap).
- **No IaC / container misconfiguration scanning** — deferred to **Phase 3**.
- **No CI/pipeline wiring** — v1 is invoked interactively inside Claude Code.
- **Not a replacement for a human security review** — it's a triage aid.

---



## 3. Prior art & references

Researched Sept 2026. These are the models we borrow from (we are building our own, but standing on what works).


| Reference                                                                                       | What we take from it                                                                                                                                                                    |
| ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `anthropics/claude-code-security-review` (MIT, GitHub Action + the original `/security-review`) | Vulnerability **category taxonomy** and **severity model** (HIGH/MED/LOW). Notably it has **no dedup logic** — the gap our skill closes.                                                |
| `claude-security` official plugin (`/plugin install claude-security@claude-plugins-official`)   | **Output contract** to emulate: finding IDs (`F1…`), Markdown + JSONL + **SARIF/CWE**, and a **revision stamp** tying the report to a commit. Also its verify-before-report discipline. |
| Built-in `/security-review` slash command                                                       | False-positive discipline: confidence-to-report threshold, exclusion list (DoS, rate-limiting, etc.).                                                                                   |
| **OSV.dev / OSV-Scanner** (Google)                                                              | The **dedup anchor** for dependencies: OSV aliases map GHSA/PYSEC/GO/RUSTSEC → canonical **CVE**.                                                                                       |
| **SARIF 2.1.0** (OASIS/GitHub)                                                                  | The **universal ingestion format** — nearly every scanner emits it; carries CWE (SAST) or CVE (SCA) metadata.                                                                           |
| GitLab application security                                                                     | Confirms the underlying OSS engines (Semgrep=SAST, Gitleaks=secrets, Trivy=containers) — so our output stays compatible with GitLab's model while running the free engines directly.    |


**Ecosystem gap this fills:** none of the existing Claude tools *orchestrate real scanners and dedupe across them*. superpowers has no security skill at all. This is a genuinely open niche.

---



## 4. Tool selection — decided from a feature-overlap investigation

**Method (per reviewer requirement):** before choosing tools, we ran a dedicated **feature-overlap investigation** on every candidate — what each one actually detects, its *analysis technique*, its database, and its *unique* coverage — so the set is picked to **maximize coverage while minimizing redundancy**, not by reputation. Snyk is a required default; each other tool had to prove it covers an axis Snyk does not. Findings below.

### 4.1 What the overlap investigation found

**SAST side (Snyk Code is the required incumbent):**

- **Snyk Code** — semantic **ML + interfile taint** (DeepCode engine). Finds *exploitable* flows across files without hand-written rules. ~17 languages. SARIF+CWE. Needs auth (SaaS default).
- **Semgrep** — **AST pattern-matching** (+ intrafile taint; interfile is Pro-only). On *stock* vuln classes (injection/XSS/crypto/secrets) it **heavily overlaps Snyk Code**. Its non-overlapping value is narrow but real: **custom org-specific rules** (Snyk's ML can't be told "ban our `unsafeExec()`"), **fully offline/no-auth OSS operation**, and **35+ languages**.
- **Bearer** — data-flow that tracks **sensitive data (PII/PHI, 120+ types)** and emits **privacy/GDPR (PIA/DPIA/RoPA)** evidence. **Neither Snyk Code nor Semgrep does data-classification or privacy** — a *structurally different axis*. **Zero meaningful overlap → the strongest, least-redundant add.**
- **CodeQL** — overlaps Snyk Code's semantic taint **and** is license-blocked for private code (needs GitHub Advanced Security). **Excluded** (mention-only).

**SCA side (Snyk Open Source is the required incumbent):**

- No dependency DB is a strict superset. **Snyk** owns a distinct **pre-CVE / curated / malicious-package tail** (~47-day median lead on JS advisories) + **reachability + priority score + fix PRs**. **OSV-Scanner** reads **ecosystem-native DBs directly (RustSec/Go/PyPA)**, is **free, offline, no auth, no test cap**, and its **OSV alias graph is the dedup anchor**. Unioning the two raises recall; they **dedupe cleanly on CVE/GHSA**, leaving only each side's unique tail. → **OSV-Scanner is additive, keep it.**
- **Trivy / Grype** in filesystem mode derive language-dep data from the *same* GHSA/OSV/NVD feeds as OSV-Scanner → **redundant for source SCA**. They only earn a place on the **container/OS-package/IaC** axis → **Phase 2**.

**Secrets side (Snyk does not scan secrets):**

- **Gitleaks** — regex+entropy, fast, offline, **native SARIF**, MIT. Answers "does this *look* like a secret."
- **trufflehog** — **live-verification** against 800+ providers; answers "is this credential *actually live*." Different false-positive profile, scans non-git sources; **AGPL-3.0**, JSON-only (no SARIF). **Complementary, not redundant.**



### 4.2 Decided tool set


| Axis                               | Default (runs every scan)                                                      | Analysis / unique value                                                             | Non-overlap justification                               |
| ---------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Semantic SAST** (exploitability) | **Snyk Code** (`snyk code test`)                                               | ML + interfile taint                                                                | Required incumbent                                      |
| **Privacy / sensitive-data SAST**  | **Bearer** (`bearer scan .`)                                                   | PII/PHI data-flow + GDPR evidence                                                   | Only tool on the data-classification axis — no overlap  |
| **Dependencies / SCA**             | **Snyk Open Source** (`snyk test`) + **OSV-Scanner** (`osv-scanner scan -r .`) | Snyk = curated/pre-CVE tail + reachability; OSV = open/offline tail + ecosystem DBs | Divergent DB tails; deduped on CVE/GHSA via OSV aliases |
| **Secrets**                        | **Gitleaks** (`gitleaks detect`)                                               | fast regex/entropy, native SARIF                                                    | Distinct domain (Snyk can't)                            |


**Opt-in (off by default, enabled per-scan or by config):**

- **Semgrep** (`--with-semgrep`) — for teams that want **custom rules** or **offline SAST** when Snyk Code auth/quota is unavailable. Off by default because it materially overlaps Snyk Code on stock detection (respects the "don't overlap much" mandate).
- **trufflehog** (`--verify-secrets`) — adds **live-credential verification** to cut secret false-positives; hits provider APIs (network), so opt-in.

**Excluded:** CodeQL (redundant + private-code license), Trivy/Grype for source SCA (redundant DB feeds).

### 4.3 Deferred to Phase 3 (IaC + container/OS)

**Trivy** (`trivy config` for Terraform/CloudFormation/K8s/Dockerfile; `trivy image` for OS packages) and/or **Checkov**. This is exactly where Trivy/Grype stop being redundant — a genuinely new axis, folded through the same normalize+dedupe pipeline as a new `iac` category.

### 4.4 Discover, don't hardcode

Per project ethos, the skill **probes which binaries exist** (`snyk`, `bearer`, `osv-scanner`, `gitleaks`, plus opt-ins `semgrep`, `trufflehog`) and its Snyk auth status, then runs whatever is available. Missing/unauth tools are **skipped with a note in the report** plus an install/auth hint. It never hard-fails on one absent tool, and never silently claims coverage it didn't run. Because **Snyk is a default but needs auth**, the skill checks `snyk auth` state up front and, if absent, reports Snyk as skipped rather than erroring.

---



## 5. Architecture & workflow

Tool-orchestration with an **LLM merge/triage layer** (no LLM-invented findings).

```
1. PREFLIGHT   detect available scanners; resolve scan target (whole repo, v1);
               capture commit SHA + dirty-state for the revision stamp.
2. SCAN        run each available scanner, each emitting SARIF (or JSON fallback)
               into a scratch dir. Scanners run independently (parallelizable).
3. PARSE       load every tool's output into the normalized Finding model (§6).
4. DEDUPE      collapse duplicates across tools per category rules (§7),
               resolving SCA IDs to canonical CVE via OSV aliases.
5. TRIAGE      LLM normalizes severity to one scale, buckets each finding into an
               OWASP Top-10 category (via CWE->OWASP), and drops known-noise classes
               (DoS, rate-limiting, etc. — the documented exclusion list).
6. REPORT      emit SECURITY-REPORT.md (human) + findings.jsonl + merged.sarif +
               revision stamp. Findings get stable IDs (F1, F2, ...).
```

The **LLM's job is bounded**: dedupe judgment on ambiguous matches, severity normalization, OWASP categorization, exclusion-list application, and writing the readable report. **It may not add a finding no scanner produced.** Every reported finding carries `source_tools[]` proving provenance.

---



## 6. Normalized finding model

```jsonc
Finding {
  id: "F1",                         // stable within a report
  category: "sast" | "sca" | "secret",   // + "iac" in Phase 3
  title: string,
  severity: "critical" | "high" | "medium" | "low" | "info",  // normalized
  confidence: "high" | "medium" | "low",
  owasp: "A03:2021-Injection" | ...,     // bucketed via CWE->OWASP mapping
  cwe: ["CWE-89", ...],             // SAST/IaC taxonomy
  cve: ["CVE-2024-....", ...],      // SCA canonical key (OSV-resolved)
  package: { name, installed_version, fixed_version } | null,  // SCA only
  location: { file, start_line, end_line } | null,
  fingerprint: string,              // SARIF partialFingerprints / gitleaks fingerprint
  description: string,
  exploit_scenario: string,         // "how this could be abused"
  recommendation: string,           // guidance only — NOT applied
  source_tools: ["semgrep", "snyk"] // provenance / which tools agreed
}
```

---



## 7. De-duplication strategy

Ingest **SARIF where available**, JSON otherwise; normalize; then dedupe **per category**:

- **SCA:** key = `(package, installed_version, canonical_CVE)`. Resolve GHSA/PYSEC/GO/RUSTSEC/SNYK → CVE via **OSV aliases before comparing**. Collapses OSV-Scanner ↔ Snyk Open Source overlap; the surviving deltas are exactly each tool's unique tail (Snyk's pre-CVE/curated entries have no CVE yet, so they can't collide). No-CVE advisories fall back to their OSV/GHSA/SNYK ID. Carry Snyk's reachability/priority signal onto the merged finding when present.
- **SAST:** key = `(normalized_relative_path, line_range, CWE)`. Rule IDs are tool-specific, so **CWE + location** is the cross-tool key; keep every tool's rule_id as evidence on the merged finding.
- **Secrets:** key = `(normalized_relative_path, line, secret_hash)`. Never dedupe on plaintext; use gitleaks fingerprints / trufflehog redacted hashes.

When two tools report the same finding, they **merge into one** with `source_tools` listing both (higher confidence signal).

---



## 8. Output contract

Written **outside the repo** to `~/Downloads/varno-devflow-security-scan/reports/` (confirmed),
one timestamped subdirectory per scan (model: `claude-security` plugin):

```
~/Downloads/varno-devflow-security-scan/reports/<timestamp>/
├── SECURITY-REPORT.md      # human report — the primary deliverable
├── findings.jsonl          # one normalized Finding per line (machine-readable)
├── merged.sarif            # SARIF 2.1.0, CWE-classified, GitHub-uploadable
└── revision.json           # commit SHA, branch, dirty-state, tools run, tool versions,
                            #   scan scope, timestamp — ties report to exact code state
```

Reports live outside the repo, so **no** `.gitignore` **entry is needed** and reports are
never committed by accident. The skill creates the directory if absent.

`SECURITY-REPORT.md` structure:

- **Summary:** counts by severity + by category, tools run, tools skipped (with why), commit scanned.
- **Severity source of truth:** normalized to one scale; when tools disagree, **CVSS (NVD) wins** over tool-native ratings (confirmed).
- **Findings**, sorted by severity then confidence: `ID · title · severity · confidence · OWASP bucket · location/package · which tools flagged it · exploit scenario · recommendation`.
- **Skipped/excluded** appendix (noise classes filtered) so nothing is silently dropped.

---



## 9. Skill UX / invocation

- **Command:** `/security-scan` (confirmed — see Decisions §11).
- **v1 args:** optional `--path <dir>` to narrow scope; default = whole working tree.
- **Fits varno-devflow:** run it before `/close-task` to review a branch's security posture; the report informs whether findings need a fix task before opening the MR. (Deeper glab/MR integration is Phase 2.)
- **Prerequisites handling:** skill checks for scanner binaries at start; prints a one-line install hint per missing tool (`brew install …`); proceeds with whatever is available.

---



## 10. Roadmap / phases

- **Phase 1 (this spec):** whole-repo scan; defaults **Snyk Code + Snyk Open Source + Bearer + OSV-Scanner + Gitleaks** (opt-ins: Semgrep, trufflehog); LLM merge/triage; Markdown + JSONL + SARIF + revision stamp. No fixing.
- **Phase 2:** diff/MR-targeted mode — scan only `git diff main...HEAD`, wire into the merge-request flow (glab) for fast, focused reviews on every MR.
- **Phase 3:** IaC + container/OS scanning (Trivy `config`/`image` and/or Checkov) as a new `iac` category through the same pipeline — the axis where Trivy stops being redundant with OSV-Scanner.

## 11. Decisions (all resolved with reviewer)

1. **Skill name** — `/security-scan`. ✓
2. **Snyk** — **default** (Snyk Code + Snyk Open Source), not opt-in. ✓
3. **Bearer** — **included** as the privacy/sensitive-data axis; the overlap investigation confirmed it's the least-redundant tool (Snyk/Semgrep don't do data-classification). ✓
4. **Report location** — `~/Downloads/varno-devflow-security-scan/reports/<timestamp>/` (outside the repo; no gitignore needed). ✓
5. **Severity tiebreak** — when tools disagree, **CVSS (NVD) wins** over tool-native ratings. ✓
6. **Semgrep** — **opt-in** (`--with-semgrep`), not default: overlaps Snyk Code on stock detection; kept for custom-rule/offline scenarios. *(My call, per your ask to decide from the investigation — flag if you'd rather it be default or dropped entirely.)*
7. **trufflehog** — **opt-in** (`--verify-secrets`) for live-credential verification. *(My call — same note.)*

---



## 12. Verification plan

How we'll confirm the built skill works (used later by `/verify-work`):

1. **Detection:** on a machine missing a tool, the skill skips it and says so — no hard failure.
2. **Findings are real:** seed a repo with a known vulnerable dependency (a pinned CVE) and a hardcoded secret; confirm both appear, attributed to the right tools, with correct CVE/fingerprint.
3. **Dedup works:** run with both OSV-Scanner and Snyk enabled on the same vulnerable dep; confirm **one** merged finding with `source_tools: [osv-scanner, snyk]`, not two.
4. **No hallucination:** confirm every finding in `findings.jsonl` has non-empty `source_tools` traceable to a raw scanner output file.
5. **Output contract:** `merged.sarif` validates against SARIF 2.1.0; `revision.json` matches `git rev-parse HEAD`.
6. **No mutation:** confirm the skill made zero edits to source files (report-only).

