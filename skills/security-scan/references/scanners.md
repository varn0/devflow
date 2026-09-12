# Scanner catalog — detection, commands, output

Every command here is **read-only** — scanners analyze; they never modify source.
The skill **discovers which tools exist** and runs whatever is available. A missing
or unauthenticated tool is **skipped with a note**, never a hard failure, and its
axis is reported as *not covered* — never as *clean*.

Write each tool's raw output into the scratch input dir under the **exact filename
in the "Output file" column** — `merge_findings.py` selects a parser by that stem.

## Defaults (run on every scan)

| Tool | Axis | Detect | Run | Output file |
|---|---|---|---|---|
| Snyk Code | Semantic SAST | `command -v snyk` **and** `snyk auth` state OK | `snyk code test --sarif-file-output=<in>/snyk-code.sarif` | `snyk-code.sarif` |
| Snyk Open Source | SCA | same as above | `snyk test --json-file-output=<in>/snyk-oss.json` | `snyk-oss.json` |
| Bearer | Privacy / sensitive-data SAST | `command -v bearer` | `bearer scan . --format json --output <in>/bearer.json` | `bearer.json` |
| OSV-Scanner | SCA | `command -v osv-scanner` | `osv-scanner scan --recursive --format json --output <in>/osv-scanner.json .` | `osv-scanner.json` |
| Gitleaks | Secrets | `command -v gitleaks` | `gitleaks detect --report-format sarif --report-path <in>/gitleaks.sarif --no-banner` (or `--report-format json` → `gitleaks.json`) | `gitleaks.json` / `.sarif` |

## Opt-in (only when the user passes the flag)

| Tool | Flag | Run | Output file |
|---|---|---|---|
| Semgrep | `--with-semgrep` | `semgrep scan --sarif --output <in>/semgrep.sarif` | `semgrep.sarif` |
| trufflehog | `--verify-secrets` | `trufflehog filesystem . --json > <in>/trufflehog.json` | `trufflehog.json` |

## Snyk auth is a gate, not a crash

Snyk is a **default but needs auth**. Before running either Snyk command, check auth
state (e.g. `snyk auth` status / a trivial `snyk test` dry run). If unauthenticated:
report Snyk Code **and** Snyk Open Source as **skipped — unauthenticated**, print the
hint `snyk auth`, and continue with the other tools. Never treat "snyk not run" as a
clean SAST/SCA result.

## Install / auth hints (print one line per missing tool)

| Missing | Hint |
|---|---|
| snyk | `npm install -g snyk && snyk auth` |
| bearer | `brew install bearer/tap/bearer` |
| osv-scanner | `brew install osv-scanner` |
| gitleaks | `brew install gitleaks` |
| semgrep | `pipx install semgrep` (opt-in) |
| trufflehog | `brew install trufflehog` (opt-in) |

## Coverage axes — what a skipped tool costs

State the gap explicitly in the report when a tool is skipped:

- **Snyk Code skipped** → no semantic/interfile SAST (injection, taint flows).
- **Bearer skipped** → no sensitive-data / privacy (PII/PHI) coverage.
- **Snyk OSS + OSV-Scanner both skipped** → no dependency/CVE coverage at all.
- **Gitleaks skipped** → no secret detection.

Two SCA tools cover each other's tail; one alone is *reduced*, not *absent*, coverage.
