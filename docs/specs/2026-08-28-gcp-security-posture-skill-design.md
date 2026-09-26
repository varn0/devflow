# gcp-security-posture Skill Design

## Overview

A new `gcp-security-posture` skill that performs Cloud Security Posture Management (CSPM) for Google Cloud. It detects misconfigurations across IAM/service accounts, network/firewall, storage, and APIs/functions/logging, and integrates Security Command Center (SCC) findings when available.

The skill follows a **two-phase, separation-of-concerns pattern** (adapted from `alirezarezvani/claude-skills` → `engineering-team/skills/cloud-security`):

1. **Collector phase** — runs a fixed set of **read-only** `gcloud`/`gcloud scc` commands that dump JSON into a local working directory. Auto-detects the account's setup (Organization present? SCC tier?) and degrades gracefully.
2. **Analyzer phase** — a Python script (`gcp_posture_check.py`) that is **stdlib-only, no network, no auth, no subprocess**. It reads the local JSON and emits findings with severity, affected resource, an exact `gcloud` remediation command, and MITRE ATT&CK mapping.

This separation is the core safety property: the analyzer never touches the cloud, holds no credentials, and cannot mutate anything. All privileged access is confined to read-only collection commands run under the user's existing `gcloud` auth.

### Why this pattern

- **Safe by construction** — mutation is impossible in the analyzer; the collector uses only read verbs.
- **CI-friendly** — the analyzer emits `--json` and exit codes (0/1/2), so it can gate pipelines.
- **Offline / auditable** — collected JSON can be reviewed, archived, or diffed between runs.
- **Tier-agnostic** — direct `gcloud` config checks run regardless of SCC availability; SCC findings are additive when present.

### Non-goals (YAGNI)

- Not incident response for active compromise.
- Not application vulnerability / SAST scanning.
- Not auto-remediation — the skill reports and suggests exact fix commands; it never applies them.
- No third-party SDKs (no `google-cloud-*` Python libraries). Collection is pure `gcloud` CLI; analysis is pure stdlib.

## Design Pattern Reference

Mirrors the reference repo's structure and safety model:

| Reference (`cloud-security`) | This skill (`gcp-security-posture`) |
|---|---|
| `SKILL.md` methodology | `SKILL.md` methodology + collector workflow |
| `scripts/cloud_posture_check.py` (stdlib, offline) | `scripts/gcp_posture_check.py` (stdlib, offline) |
| Input: exported policy/config JSON | Input: `gcloud`-exported JSON in `./posture-data/` |
| Checks: `iam` / `s3` / `sg`, AWS actions | Checks: `iam` / `net` / `storage` / `services`, GCP resources |
| Exit codes 0/1/2, `--json`, severity modifiers | Same contract |

## Components Affected

- `skills/gcp-security-posture/SKILL.md` — new skill file (methodology + collector workflow + analyzer invocation)
- `skills/gcp-security-posture/references/gcloud-collect.md` — exact read-only collection commands + setup auto-detection logic
- `skills/gcp-security-posture/references/cspm-checks.md` — check catalog: what each finding means and its severity rationale
- `skills/gcp-security-posture/scripts/collect.sh` — runs all read-only `gcloud`/`scc` dumps into `./posture-data/`
- `skills/gcp-security-posture/scripts/gcp_posture_check.py` — offline analyzer (stdlib only)
- `CLAUDE.md` — add `gcp-security-posture` to the `skills/` project-structure listing
- `hooks/session-context.md` — add the skill to the available-skills table injected at session start

## Changes by File

### `skills/gcp-security-posture/SKILL.md`

Frontmatter (match existing skill conventions):

```yaml
---
name: gcp-security-posture
description: Use when assessing a Google Cloud project or organization for security misconfigurations — IAM privilege risks, service-account key hygiene, public firewall rules, public GCS buckets, unauthenticated Functions/Run services, and audit-logging gaps. Pulls Security Command Center findings when available. Read-only; never mutates cloud resources.
user-invocable: true
argument-hint: [gcp-project-id]
---
```

Body sections:

1. **Overview & safety contract** — state the read-only guarantee up front. Enumerate the exact verb allowlist the collector may use: `list`, `describe`, `get-iam-policy`, `scc findings list`, `organizations list`. Explicitly forbid `create`/`update`/`delete`/`set-iam-policy`/`add-iam-policy-binding`/`remove-iam-policy-binding`/`enable`/`disable`.

2. **Prerequisites** — `gcloud` installed and authenticated; recommended least-privilege roles `roles/viewer` + `roles/iam.securityReviewer` (and `roles/securitycenter.findingsViewer` at org level if SCC is used). Note the skill uses whatever the active `gcloud` credential already has; it adds no credentials of its own.

3. **Setup auto-detection** — before collecting, determine the environment (see `references/gcloud-collect.md`):
   - `gcloud organizations list` → does the account belong to an Organization?
   - If an org exists, attempt `gcloud scc settings services describe` / probe `gcloud scc findings list` on the org to determine whether SCC (and which tier) is usable.
   - Record the detected mode in `./posture-data/_meta.json`: `{ "org_id": ..., "scc_available": bool, "project_id": ... }`. The analyzer reads this to decide whether missing SCC data is expected (no false "SCC not run" warnings).

4. **Collector workflow** — instruct running `scripts/collect.sh <project-id>` (or the equivalent commands from `references/gcloud-collect.md` when a user wants to run them manually). All output lands in `./posture-data/*.json`. The collector always runs the four direct-config check groups; it additionally pulls SCC findings only when `scc_available` is true.

5. **Analysis workflow** — run:
   ```bash
   python3 scripts/gcp_posture_check.py ./posture-data --check all --json
   ```
   Summarize the findings for the user grouped by severity, and for each critical/high finding show the affected resource and the suggested `gcloud` remediation command. Never run the remediation commands automatically — present them for the user to apply.

6. **Check groups** — document the four groups and what each covers (mirror `references/cspm-checks.md`).

7. **Anti-patterns** — do not run mutating commands; do not widen the credential's scope to collect more; do not treat absent SCC findings as "clean" (state coverage limits explicitly).

8. **Cross-references** — point to `references/cspm-checks.md` and `references/gcloud-collect.md`.

### `skills/gcp-security-posture/references/gcloud-collect.md`

The exact, copy-pasteable **read-only** commands, one block per artifact. Each writes JSON to `./posture-data/<name>.json`. Canonical set:

**Setup detection**
```bash
gcloud organizations list --format=json > ./posture-data/_orgs.json
# scc_available probe (org-scoped); tolerate failure and record false
```

**IAM & service accounts**
```bash
gcloud projects get-iam-policy "$PROJECT" --format=json > ./posture-data/iam_policy.json
gcloud iam service-accounts list --project="$PROJECT" --format=json > ./posture-data/service_accounts.json
# for each SA: gcloud iam service-accounts keys list --iam-account=<sa> --format=json
#   (only USER_MANAGED keys are a finding; capture validAfterTime for age) → ./posture-data/sa_keys.json
```

**Network / firewall**
```bash
gcloud compute firewall-rules list --project="$PROJECT" --format=json > ./posture-data/firewall.json
gcloud compute networks list --project="$PROJECT" --format=json > ./posture-data/networks.json
gcloud compute instances list --project="$PROJECT" --format=json > ./posture-data/instances.json
```

**Storage (GCS)**
```bash
gcloud storage buckets list --project="$PROJECT" --format=json > ./posture-data/buckets.json
# per bucket IAM policy (allUsers/allAuthenticatedUsers) + uniformBucketLevelAccess flag
#   → ./posture-data/bucket_iam.json (array of {bucket, iam_policy, uniform_bucket_level_access})
```

**APIs / functions / logging**
```bash
gcloud functions list --project="$PROJECT" --format=json > ./posture-data/functions.json
# per function/Run service: get-iam-policy → detect allUsers invoker → ./posture-data/function_iam.json
gcloud run services list --project="$PROJECT" --format=json > ./posture-data/run_services.json
gcloud services list --enabled --project="$PROJECT" --format=json > ./posture-data/enabled_apis.json
gcloud logging sinks list --project="$PROJECT" --format=json > ./posture-data/log_sinks.json
gcloud projects get-iam-policy "$PROJECT" --format=json  # audit-log config is in the policy's auditConfigs
```

**SCC (only when scc_available)**
```bash
gcloud scc findings list "$ORG_ID" --filter="state=\"ACTIVE\"" --format=json \
  > ./posture-data/scc_findings.json
```

This file must state the verb allowlist and that every command here is read-only.

### `skills/gcp-security-posture/references/cspm-checks.md`

The check catalog. For each check: ID, category, what it detects, how it maps from the collected JSON, default severity, severity-modifier behavior, MITRE technique, and the exact remediation `gcloud` command template. Catalog (minimum viable set):

**IAM & service accounts**
| ID | Detects | Severity | Remediation |
|---|---|---|---|
| `iam-public-member` | `allUsers`/`allAuthenticatedUsers` in project IAM policy | Critical | `gcloud projects remove-iam-policy-binding` |
| `iam-primitive-owner` | `roles/owner` bound to a user/group | High | Replace with least-privilege predefined role |
| `iam-primitive-editor` | `roles/editor` bound to a user/group | Medium | Scope to specific predefined roles |
| `iam-external-member` | member outside allowed domain(s) | High | Review/remove external principal |
| `sa-user-managed-key` | user-managed SA key exists | High | Delete key; use workload identity / short-lived creds |
| `sa-old-key` | user-managed key age > 90 days | Medium | Rotate/delete key |
| `sa-primitive-role` | SA granted owner/editor | High | Scope SA to minimal roles |

**Network / firewall**
| `fw-open-admin` | ingress `0.0.0.0/0` to 22/3389/…  | Critical | Restrict source ranges |
| `fw-open-all` | ingress `0.0.0.0/0` all ports | Critical | Restrict source ranges / delete rule |
| `net-default-network` | default network in use | Low | Migrate to a custom VPC |
| `vm-external-ip` | instance has an external IP | Low (Medium if paired with open admin fw) | Remove external IP / use IAP |

**Storage**
| `gcs-public-iam` | bucket grants allUsers/allAuthenticatedUsers | Critical | Remove public binding |
| `gcs-uniform-off` | uniform bucket-level access disabled | Medium | Enable uniform access |

**APIs / functions / logging**
| `fn-public-invoker` | Function/Run service allows `allUsers` invoker | High | Remove public invoker binding |
| `log-audit-gap` | Data-access audit logging not enabled for key services | Medium | Configure `auditConfigs` |
| `api-broad-enabled` | high-risk APIs enabled but unused (advisory) | Low | Disable unused APIs |

**Severity modifiers** (match reference contract): `--severity-modifier internet-facing` and `--severity-modifier regulated-data` each bump findings by one level.

### `skills/gcp-security-posture/scripts/collect.sh`

A bash script: `collect.sh <project-id>`. Behavior:

- `set -euo pipefail`; create `./posture-data/`.
- Run setup detection; write `_meta.json`.
- Run every read-only command from `references/gcloud-collect.md`, tolerating individual failures (a missing API or permission writes an empty array + a note into `_meta.json.collection_errors[]` rather than aborting the whole run).
- Only invoke `gcloud scc findings list` when `scc_available` is true.
- Print a one-line summary of what was collected. **No mutating commands anywhere.**

### `skills/gcp-security-posture/scripts/gcp_posture_check.py`

Pure-stdlib analyzer. Contract mirrors `cloud_posture_check.py`:

- **Imports:** only `argparse, json, sys, os, glob, dataclasses, datetime, typing`. No `subprocess`, no `requests`/`urllib`, no `google.*`, no network, no auth. (This is a hard invariant — a test asserts it.)
- **Input:** a directory path (`./posture-data`) rather than a single file; loads each `*.json` artifact it recognizes. Missing artifacts are skipped with a coverage note, not an error.
- **CLI:**
  ```
  gcp_posture_check.py <posture-data-dir> [--check all|iam|net|storage|services]
                       [--severity-modifier internet-facing|regulated-data]
                       [--json] [--min-severity low|medium|high|critical]
  ```
- **Finding dataclass:** `finding_id, category, severity, title, description, affected_resource, recommendation, gcloud_fix, mitre_technique`.
- **Result dataclass:** `source_dir, check_mode, scc_available, findings[], summary{by_severity}, coverage{artifacts_present, artifacts_missing}, timestamp_utc`.
- **Check functions:** one per catalog group (`check_iam`, `check_net`, `check_storage`, `check_services`) plus `merge_scc_findings` that normalizes `scc_findings.json` into the same schema and dedupes against direct findings (by `affected_resource` + category).
- **Severity → exit code:** any critical ⇒ 2; else any high ⇒ 1; else 0. (Matches reference.)
- **Output:** human-readable table by default; `--json` emits the full result object.
- **timestamp_utc:** `datetime.now(timezone.utc).isoformat()`.

### `CLAUDE.md`

Add `gcp-security-posture` to the `skills/` line in the project-structure block. One-line description: read-only GCP CSPM (gcloud + SCC), offline analyzer.

### `hooks/session-context.md`

Add a row to the available-skills table:

```
| `/gcp-security-posture` | Read-only GCP security posture assessment (gcloud + Security Command Center) |
```

## Safety Invariants (must hold in implementation)

1. **Collector verb allowlist** — only `list`, `describe`, `get-iam-policy`, `scc findings list`, `organizations list`. Any other verb is a spec violation. Documented in both `SKILL.md` and `references/gcloud-collect.md`.
2. **Analyzer isolation** — `gcp_posture_check.py` imports only stdlib; no `subprocess`/network/cloud SDK. Enforced by a unit test that greps the import set.
3. **No auto-remediation** — remediation commands are printed, never executed by the skill.
4. **Graceful degradation** — absent org/SCC or missing permissions never crash the run; coverage limits are reported explicitly so absent data is never mistaken for "clean".
5. **Least privilege guidance** — the skill recommends `roles/viewer` + `roles/iam.securityReviewer` (+ `roles/securitycenter.findingsViewer` for SCC) and works read-only under existing credentials.

## Verification Plan

### Behavioral Checks
- [ ] `python3 gcp_posture_check.py <fixtures>` on a fixture dir with a known public bucket, an `allUsers` IAM binding, an open `0.0.0.0/0:22` firewall rule, and a user-managed SA key produces exactly the expected findings at the expected severities.
- [ ] Exit code is 2 when a critical fixture is present, 1 when only high, 0 when clean.
- [ ] `--json` output validates against the documented result schema.
- [ ] Running the analyzer against a `posture-data` dir with `scc_available:false` in `_meta.json` reports SCC coverage as "not collected" rather than emitting a false warning or crashing.
- [ ] `--severity-modifier internet-facing` bumps a normally-High finding to Critical.

### Edge Cases
- [ ] Missing artifact files (e.g., no `functions.json`) are skipped with a coverage note; run still succeeds.
- [ ] Empty arrays (no firewall rules, no buckets) produce zero findings and exit 0.
- [ ] Malformed JSON in one artifact reports that artifact as unreadable in `coverage` without aborting the others.

### Safety Checks
- [ ] `grep -E 'import (subprocess|requests|urllib|google)' gcp_posture_check.py` returns nothing.
- [ ] `grep -E '(create|delete|update|set-iam-policy|add-iam-policy-binding|remove-iam-policy-binding|--quiet)' collect.sh` returns nothing (no mutating verbs; note `remove-iam-policy-binding` appears only as a *suggested* fix string in the analyzer, never executed).
- [ ] `collect.sh` run against a real project with a `roles/viewer`-only credential completes without permission-denied aborts (individual failures captured in `_meta.json.collection_errors`).

## Implementation Notes

- Build the analyzer first with local JSON fixtures (test-driven); the collector and `gcloud` plumbing come second so analysis logic is validated without cloud access.
- Keep each check function small and independently testable — one function per catalog group, each taking parsed JSON and returning `List[Finding]`.
- Fixtures for the four groups double as the reference examples in `cspm-checks.md`.
