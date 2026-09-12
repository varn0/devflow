#!/usr/bin/env python3
"""Deterministic parse + dedupe + emit for /security-scan.

Reads raw scanner outputs from an input directory, normalizes every record
into the Finding model, dedupes per category, assigns stable IDs, and emits
findings.jsonl + merged.sarif + a summary to the output directory.

HARD INVARIANT: this script NEVER invents a finding. Every Finding it emits
originates from a real scanner file and carries a non-empty source_tools[].
It has no network access and imports only the standard library.

The LLM triage layer runs AFTER this script. Its job is bounded to: ambiguous
merge judgment, OWASP bucketing, exclusion-list application, and prose. It may
not add a finding this script did not produce.

Recognized input filenames (stem -> parser). Missing files are skipped with a
coverage note, never an error:
  gitleaks.json        gitleaks secrets (JSON array)
  trufflehog.json      trufflehog secrets (JSON lines or array)
  osv-scanner.json     OSV-Scanner SCA
  snyk-oss.json        `snyk test --json` SCA
  snyk-code.sarif      `snyk code test --sarif` SAST
  bearer.json          `bearer scan --format json` SAST/privacy
  semgrep.sarif        `semgrep --sarif` SAST (opt-in)
  *.sarif              any other SARIF 2.1.0 file (generic SAST/SCA)

Usage:
  merge_findings.py <input-dir> <output-dir> [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from glob import glob
from typing import Any, Optional

# ── severity + confidence normalization ─────────────────────────────────────

SEV_ORDER = ["info", "low", "medium", "high", "critical"]
SEV_RANK = {s: i for i, s in enumerate(SEV_ORDER)}

_SEV_ALIASES = {
    "crit": "critical", "critical": "critical",
    "high": "high", "error": "high",
    "medium": "medium", "moderate": "medium", "warning": "medium", "med": "medium",
    "low": "low", "note": "low", "minor": "low",
    "info": "info", "informational": "info", "none": "info", "unknown": "info",
}


def norm_sev(value: Any) -> Optional[str]:
    """Map a tool-native severity to the common scale, or None if absent."""
    if value is None:
        return None
    if isinstance(value, (int, float)):  # CVSS numeric score
        v = float(value)
        if v >= 9.0:
            return "critical"
        if v >= 7.0:
            return "high"
        if v >= 4.0:
            return "medium"
        if v > 0.0:
            return "low"
        return "info"
    key = str(value).strip().lower()
    return _SEV_ALIASES.get(key)


def max_sev(sevs: list[Optional[str]]) -> Optional[str]:
    present = [s for s in sevs if s]
    if not present:
        return None
    return max(present, key=lambda s: SEV_RANK[s])


# ── the Finding model (mirrors spec §6) ──────────────────────────────────────

@dataclass
class Finding:
    category: str                       # sast | sca | secret
    title: str
    severity: Optional[str]             # normalized; None => triage must resolve
    confidence: Optional[str] = None
    cwe: list[str] = field(default_factory=list)
    cve: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)   # all advisory ids seen
    package: Optional[dict] = None      # {name, installed_version, fixed_version}
    location: Optional[dict] = None     # {file, start_line, end_line}
    fingerprint: Optional[str] = None
    description: str = ""
    recommendation: str = ""
    rule_ids: list[str] = field(default_factory=list)
    severity_sources: dict = field(default_factory=dict)  # tool -> native severity
    source_tools: list[str] = field(default_factory=list)
    id: str = ""                        # assigned after sort


def _norm_path(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    p = p.replace("\\", "/")
    p = re.sub(r"^\./", "", p)
    p = re.sub(r"^file://", "", p)
    return p.lstrip("/") if p.startswith("/") and "://" not in p else p


# ── parsers: each returns list[Finding] and never raises on bad shape ────────

def _get(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    return default


def parse_gitleaks(data: Any, tool: str) -> list[Finding]:
    out = []
    rows = data if isinstance(data, list) else _get(data or {}, "findings", default=[])
    for r in rows or []:
        f = _norm_path(_get(r, "File", "file"))
        line = _get(r, "StartLine", "line")
        out.append(Finding(
            category="secret",
            title=f"Secret: {_get(r, 'RuleID', 'rule', default='hardcoded secret')}",
            severity="high",
            confidence="medium",
            location={"file": f, "start_line": line, "end_line": _get(r, "EndLine", default=line)},
            fingerprint=_get(r, "Fingerprint", "fingerprint") or f"{f}:{_get(r, 'RuleID', default='')}:{line}",
            description=_get(r, "Description", "Match", default="Potential hardcoded secret detected."),
            rule_ids=[str(_get(r, "RuleID", "rule", default="gitleaks"))],
            severity_sources={tool: "high"},
            source_tools=[tool],
        ))
    return out


def parse_trufflehog(data: Any, tool: str) -> list[Finding]:
    out = []
    rows = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    for r in rows:
        if not isinstance(r, dict):
            continue
        src = _get(r, "SourceMetadata", default={})
        fdata = _get(src, "Data", default={}) if isinstance(src, dict) else {}
        loc = {}
        for engine in (fdata.values() if isinstance(fdata, dict) else []):
            if isinstance(engine, dict):
                loc = {"file": _norm_path(_get(engine, "file")),
                       "start_line": _get(engine, "line"), "end_line": _get(engine, "line")}
                break
        verified = bool(_get(r, "Verified", default=False))
        redacted = _get(r, "Redacted", default="")
        det = _get(r, "DetectorName", default="secret")
        out.append(Finding(
            category="secret",
            title=f"Secret: {det}" + (" (verified live)" if verified else ""),
            severity="critical" if verified else "high",
            confidence="high" if verified else "medium",
            location=loc or None,
            fingerprint=f"{loc.get('file')}:{det}:{redacted}" if loc else f"{det}:{redacted}",
            description=f"trufflehog {'verified live' if verified else 'unverified'} credential ({det}).",
            rule_ids=[str(det)],
            severity_sources={tool: "verified" if verified else "unverified"},
            source_tools=[tool],
        ))
    return out


def _collect_aliases(ids: list[str]) -> tuple[list[str], list[str]]:
    """Split a mixed id list into (cves, all_aliases_deduped_sorted)."""
    seen, aliases, cves = set(), [], []
    for i in ids:
        if not i:
            continue
        i = str(i).strip()
        if i in seen:
            continue
        seen.add(i)
        aliases.append(i)
        if i.upper().startswith("CVE-"):
            cves.append(i.upper())
    return sorted(set(cves)), sorted(aliases)


def parse_osv(data: Any, tool: str) -> list[Finding]:
    out = []
    for res in _get(data or {}, "results", default=[]) or []:
        source = _norm_path(_get(_get(res, "source", default={}) or {}, "path"))
        for pkg in _get(res, "packages", default=[]) or []:
            pinfo = _get(pkg, "package", default={}) or {}
            name = _get(pinfo, "name")
            version = _get(pinfo, "version")
            for v in _get(pkg, "vulnerabilities", default=[]) or []:
                ids = [_get(v, "id")] + list(_get(v, "aliases", default=[]) or [])
                cves, aliases = _collect_aliases(ids)
                sev = None
                for s in _get(v, "severity", default=[]) or []:
                    sev = max_sev([sev, norm_sev(_get(s, "score"))])
                dbsev = _get(_get(v, "database_specific", default={}) or {}, "severity")
                sev = max_sev([sev, norm_sev(dbsev)])
                out.append(Finding(
                    category="sca",
                    title=_get(v, "summary", default=f"Vulnerability in {name}"),
                    severity=sev,
                    confidence="high",
                    cve=cves,
                    aliases=aliases,
                    package={"name": name, "installed_version": version, "fixed_version": None},
                    location={"file": source, "start_line": None, "end_line": None} if source else None,
                    fingerprint=f"{name}@{version}:{(cves or aliases or ['?'])[0]}",
                    description=_get(v, "details", "summary", default=""),
                    rule_ids=[str(_get(v, "id", default=""))],
                    severity_sources={tool: dbsev or "n/a"},
                    source_tools=[tool],
                ))
    return out


def parse_snyk_oss(data: Any, tool: str) -> list[Finding]:
    out = []
    vulns = _get(data or {}, "vulnerabilities", default=[])
    if isinstance(data, list):  # multi-project array
        vulns = [v for proj in data for v in _get(proj or {}, "vulnerabilities", default=[]) or []]
    for v in vulns or []:
        idents = _get(v, "identifiers", default={}) or {}
        ids = [_get(v, "id")] + list(_get(idents, "CVE", default=[]) or []) + list(_get(idents, "GHSA", default=[]) or [])
        cves, aliases = _collect_aliases(ids)
        name = _get(v, "packageName", "name")
        version = _get(v, "version")
        fixed = None
        upgrade = _get(v, "fixedIn", default=[])
        if isinstance(upgrade, list) and upgrade:
            fixed = upgrade[0]
        out.append(Finding(
            category="sca",
            title=_get(v, "title", default=f"Vulnerability in {name}"),
            severity=norm_sev(_get(v, "severity")),
            confidence="high",
            cve=cves,
            aliases=aliases,
            package={"name": name, "installed_version": version, "fixed_version": fixed},
            fingerprint=f"{name}@{version}:{(cves or aliases or [_get(v, 'id', default='?')])[0]}",
            description=_get(v, "description", default=""),
            rule_ids=[str(_get(v, "id", default="snyk"))],
            severity_sources={tool: str(_get(v, "severity", default="n/a"))},
            source_tools=[tool],
        ))
    return out


def parse_bearer(data: Any, tool: str) -> list[Finding]:
    out = []
    if not isinstance(data, dict):
        return out
    for level in ("critical", "high", "medium", "low", "warning"):
        for r in _get(data, level, default=[]) or []:
            loc = {"file": _norm_path(_get(r, "filename", "full_filename")),
                   "start_line": _get(r, "line_number", "start_line"),
                   "end_line": _get(r, "end_line", default=_get(r, "line_number"))}
            cwes = [f"CWE-{c}" for c in (_get(r, "cwe_ids", default=[]) or [])]
            out.append(Finding(
                category="sast",
                title=_get(r, "title", "description", default="Sensitive-data / SAST finding"),
                severity=norm_sev(level),
                confidence="medium",
                cwe=cwes,
                location=loc,
                fingerprint=_get(r, "fingerprint") or f"{loc['file']}:{loc['start_line']}:{_get(r, 'id', default='')}",
                description=_get(r, "description", default=""),
                rule_ids=[str(_get(r, "id", "rule_id", default="bearer"))],
                severity_sources={tool: level},
                source_tools=[tool],
            ))
    return out


def parse_sarif(data: Any, tool: str) -> list[Finding]:
    """Generic SARIF 2.1.0 -> Finding (SAST). Used for snyk-code, semgrep, etc."""
    out = []
    for run in _get(data or {}, "runs", default=[]) or []:
        # build ruleId -> (cwe[], default-level) from the rules catalog
        rule_meta: dict[str, dict] = {}
        driver = _get(_get(run, "tool", default={}) or {}, "driver", default={}) or {}
        for rule in _get(driver, "rules", default=[]) or []:
            rid = _get(rule, "id")
            cwes = []
            for tag in _get(_get(rule, "properties", default={}) or {}, "tags", default=[]) or []:
                m = re.search(r"cwe[-:\s]?(\d+)", str(tag), re.I)
                if m:
                    cwes.append(f"CWE-{m.group(1)}")
            lvl = _get(_get(rule, "defaultConfiguration", default={}) or {}, "level")
            rule_meta[rid] = {"cwe": cwes, "level": lvl}
        for res in _get(run, "results", default=[]) or []:
            rid = _get(res, "ruleId", default="")
            meta = rule_meta.get(rid, {})
            loc, sl, el = None, None, None
            locs = _get(res, "locations", default=[]) or []
            if locs:
                phys = _get(locs[0], "physicalLocation", default={}) or {}
                art = _get(phys, "artifactLocation", default={}) or {}
                region = _get(phys, "region", default={}) or {}
                loc = _norm_path(_get(art, "uri"))
                sl = _get(region, "startLine")
                el = _get(region, "endLine", default=sl)
            fp = None
            fps = _get(res, "partialFingerprints", default={}) or {}
            if fps:
                fp = ":".join(f"{k}={v}" for k, v in sorted(fps.items()))
            props = _get(res, "properties", default={}) or {}
            cwes = list(meta.get("cwe") or [])
            for tag in _get(props, "cwe", default=[]) or []:
                m = re.search(r"(\d+)", str(tag))
                if m:
                    cwes.append(f"CWE-{m.group(1)}")
            sev = norm_sev(_get(res, "level") or meta.get("level") or _get(props, "security-severity"))
            msg = _get(_get(res, "message", default={}) or {}, "text", default=rid)
            out.append(Finding(
                category="sast",
                title=msg[:120] if msg else rid,
                severity=sev,
                confidence="medium",
                cwe=sorted(set(cwes)),
                location={"file": loc, "start_line": sl, "end_line": el} if loc else None,
                fingerprint=fp or (f"{loc}:{sl}:{rid}" if loc else rid),
                description=msg,
                rule_ids=[str(rid)] if rid else [],
                severity_sources={tool: str(_get(res, "level", default="n/a"))},
                source_tools=[tool],
            ))
    return out


# ── dedupe (per category, per spec §7) ───────────────────────────────────────

def _merge_into(base: Finding, other: Finding) -> None:
    for t in other.source_tools:
        if t not in base.source_tools:
            base.source_tools.append(t)
    base.cve = sorted(set(base.cve) | set(other.cve))
    base.aliases = sorted(set(base.aliases) | set(other.aliases))
    base.cwe = sorted(set(base.cwe) | set(other.cwe))
    base.rule_ids = sorted(set(base.rule_ids) | set(other.rule_ids))
    base.severity_sources.update(other.severity_sources)
    base.severity = max_sev([base.severity, other.severity])
    # keep the richer of the two on package fixed_version / recommendation
    if other.package and base.package:
        if not base.package.get("fixed_version") and other.package.get("fixed_version"):
            base.package["fixed_version"] = other.package["fixed_version"]
    if not base.recommendation and other.recommendation:
        base.recommendation = other.recommendation


def dedupe(findings: list[Finding]) -> list[Finding]:
    sca, sast, secret = [], [], []
    for f in findings:
        (sca if f.category == "sca" else sast if f.category == "sast" else secret).append(f)

    # SCA: match if same package@version AND alias sets intersect (OSV-alias
    # resolution); no-alias advisories fall back to package@version+vendor id.
    merged_sca: list[Finding] = []
    for f in sca:
        pkg = (f.package or {}).get("name"), (f.package or {}).get("installed_version")
        f_ids = set(f.cve) | set(f.aliases)
        hit = None
        for m in merged_sca:
            mpkg = (m.package or {}).get("name"), (m.package or {}).get("installed_version")
            if mpkg != pkg:
                continue
            m_ids = set(m.cve) | set(m.aliases)
            if (f_ids and m_ids and f_ids & m_ids) or (not f_ids and not m_ids and set(f.rule_ids) & set(m.rule_ids)):
                hit = m
                break
        if hit:
            _merge_into(hit, f)
        else:
            merged_sca.append(f)

    # SAST: key = (path, line-range overlap, CWE). Exact (path, start_line, cwe-set).
    merged_sast: list[Finding] = []
    for f in sast:
        loc = f.location or {}
        key_cwe = tuple(sorted(f.cwe))
        hit = None
        for m in merged_sast:
            mloc = m.location or {}
            if _norm_path(loc.get("file")) == _norm_path(mloc.get("file")) \
               and loc.get("start_line") == mloc.get("start_line") \
               and key_cwe and tuple(sorted(m.cwe)) == key_cwe:
                hit = m
                break
        if hit:
            _merge_into(hit, f)
        else:
            merged_sast.append(f)

    # Secrets: key = (path, line, fingerprint). Never dedupe on plaintext.
    merged_secret: list[Finding] = []
    for f in secret:
        hit = None
        for m in merged_secret:
            if f.fingerprint and f.fingerprint == m.fingerprint:
                hit = m
                break
        if hit:
            _merge_into(hit, f)
        else:
            merged_secret.append(f)

    return merged_sca + merged_sast + merged_secret


# ── output ───────────────────────────────────────────────────────────────────

PARSERS = {
    "gitleaks": parse_gitleaks,
    "trufflehog": parse_trufflehog,
    "osv-scanner": parse_osv,
    "snyk-oss": parse_snyk_oss,
    "bearer": parse_bearer,
}


def load_dir(indir: str) -> tuple[list[Finding], list[str], list[str]]:
    findings, ran, unreadable = [], [], []
    for path in sorted(glob(os.path.join(indir, "*"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read().strip()
            if not text:
                ran.append(stem)
                continue
            # trufflehog emits JSON-lines; tolerate that
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = [json.loads(ln) for ln in text.splitlines() if ln.strip()]
        except (OSError, ValueError, json.JSONDecodeError):
            unreadable.append(os.path.basename(path))
            continue
        if stem in PARSERS:
            findings += PARSERS[stem](data, stem)
        elif ext == ".sarif" or (isinstance(data, dict) and "runs" in data):
            findings += parse_sarif(data, stem)
        else:
            continue
        ran.append(stem)
    return findings, ran, unreadable


def sort_and_id(findings: list[Finding]) -> list[Finding]:
    conf_rank = {"high": 2, "medium": 1, "low": 0, None: -1}
    findings.sort(key=lambda f: (
        -SEV_RANK.get(f.severity or "info", 0),
        -conf_rank.get(f.confidence, -1),
        f.category,
        (f.location or {}).get("file") or "",
    ))
    for i, f in enumerate(findings, 1):
        f.id = f"F{i}"
    return findings


def to_sarif(findings: list[Finding]) -> dict:
    results = []
    for f in findings:
        r = {
            "ruleId": (f.cwe or f.cve or f.rule_ids or [f.id])[0],
            "level": {"critical": "error", "high": "error", "medium": "warning",
                      "low": "note", "info": "note"}.get(f.severity or "info", "note"),
            "message": {"text": f.title},
            "properties": {"security-severity-normalized": f.severity,
                           "source_tools": f.source_tools, "cve": f.cve, "cwe": f.cwe},
        }
        if f.location and f.location.get("file"):
            r["locations"] = [{"physicalLocation": {
                "artifactLocation": {"uri": f.location["file"]},
                "region": {"startLine": f.location.get("start_line") or 1},
            }}]
        if f.fingerprint:
            r["partialFingerprints"] = {"varno/v1": f.fingerprint}
        results.append(r)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "varno-devflow-security-scan",
                                      "informationUri": "https://github.com/varn0/devflow",
                                      "rules": []}},
                  "results": results}],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge + dedupe security scanner output.")
    ap.add_argument("input_dir")
    ap.add_argument("output_dir")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args()

    findings, ran, unreadable = load_dir(args.input_dir)
    findings = dedupe(findings)
    findings = sort_and_id(findings)

    os.makedirs(args.output_dir, exist_ok=True)
    jsonl_path = os.path.join(args.output_dir, "findings.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for f in findings:
            fh.write(json.dumps(asdict(f), ensure_ascii=False) + "\n")
    sarif_path = os.path.join(args.output_dir, "merged.sarif")
    with open(sarif_path, "w", encoding="utf-8") as fh:
        json.dump(to_sarif(findings), fh, indent=2)

    by_sev: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity or "unrated"] = by_sev.get(f.severity or "unrated", 0) + 1
        by_cat[f.category] = by_cat.get(f.category, 0) + 1
    # provenance invariant: every emitted finding must trace to a scanner
    orphans = [f.id for f in findings if not f.source_tools]
    summary = {
        "total": len(findings),
        "by_severity": by_sev,
        "by_category": by_cat,
        "tools_with_output": sorted(set(ran)),
        "unreadable_files": unreadable,
        "orphan_findings": orphans,   # MUST be empty — non-empty = a bug
        "findings_jsonl": jsonl_path,
        "merged_sarif": sarif_path,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"{summary['total']} findings "
              f"({', '.join(f'{k}:{v}' for k, v in sorted(by_sev.items()))}) "
              f"from {', '.join(summary['tools_with_output']) or 'no tools'}")
        if unreadable:
            print(f"unreadable: {', '.join(unreadable)}")
        if orphans:
            print(f"ERROR: {len(orphans)} findings without provenance: {orphans}")
    return 1 if orphans else 0


if __name__ == "__main__":
    sys.exit(main())
