#!/usr/bin/env python3
"""Populate registry/ from sources/manifest.yaml.

Pipeline per item:
  1. ensure the upstream is cloned at the pinned commit SHA (in .cache/);
  2. run the security scanner (scripts/scan.py) over the candidate file(s);
  3. detect the license;
  4. VENDOR (copy into registry/) only if permissive AND scan-clean;
     otherwise record a REFERENCE entry (with reason) — never silently drop.

Writes: registry/, sources/lock.json (sha256 of every vendored file),
catalog.yaml, THIRD_PARTY.md.

Never executes upstream code. Stdlib only.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters import common  # noqa: E402
from scripts import scan as scanner  # noqa: E402

CACHE = ROOT / ".cache"
REG = ROOT / "registry"
COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".DS_Store")


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #

def ensure_clone(source: dict) -> Path:
    dest = CACHE / source["id"]
    repo, commit = source["repo"], str(source["commit"])
    if not (dest / ".git").is_dir():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--filter=blob:none",
                        "--no-checkout", repo, str(dest)], check=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1",
                    "origin", commit], check=False)
    subprocess.run(["git", "-C", str(dest), "checkout", "-q", commit], check=True)
    head = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    if not head.startswith(commit[:12]) and head != commit:
        raise SystemExit(f"[sync] {source['id']}: HEAD {head} != pinned {commit}")
    return dest


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_license(skill_dir: Path, fm: dict) -> str:
    fm_lic = str(fm.get("license", "") or "")
    if "proprietary" in fm_lic.lower():
        return "Proprietary"
    blob = ""
    for cand in ("LICENSE.txt", "LICENSE", "LICENSE.md"):
        p = skill_dir / cand
        if p.is_file():
            blob = p.read_text(encoding="utf-8", errors="ignore")
            break
    text = (blob + " " + fm_lic)
    low = text.lower()
    if "proprietary" in low:
        return "Proprietary"
    if "apache license" in low or "apache-2" in low:
        return "Apache-2.0"
    if "mit license" in low or fm_lic.strip().upper() == "MIT":
        return "MIT"
    if "bsd " in low or "redistribution and use" in low:
        return "BSD"
    if "isc license" in low:
        return "ISC"
    return fm_lic or "UNKNOWN"


def normalize_model(model: str) -> str:
    """Map upstream dated/pinned model snapshots to 'inherit' for portability.

    e.g. 'claude-sonnet-4-20250514' -> 'inherit'. Generic aliases pass through.
    """
    m = (model or "").strip()
    if not m:
        return "inherit"
    low = m.lower()
    if any(ch.isdigit() for ch in low) and ("-202" in low or low.count("-") >= 2):
        return "inherit"
    if low.startswith("claude-") or low.startswith("gpt-") or low.startswith("gemini-"):
        return "inherit"
    return m


def scan_clean(path: Path) -> tuple[bool, str]:
    findings = scanner.scan_path(path)
    worst = scanner.worst_severity(findings)
    if worst == "block":
        blocks = [f for f in findings if f.severity == "block"]
        reasons = sorted({f"{f.category}:{f.rule}" for f in blocks})
        sample = blocks[0]
        return False, (f"{len(blocks)} blocking finding(s) "
                       f"[{', '.join(reasons[:4])}] e.g. {sample.path}:{sample.line}")
    return True, ""


# --------------------------------------------------------------------------- #
# vendoring
# --------------------------------------------------------------------------- #

def vendor_agent(cache: Path, src: str, name: str, domain: str,
                 source: dict, lock: dict, catalog: list) -> None:
    spath = cache / src
    if not spath.is_file():
        catalog.append(dict(id=f"agent/{domain}/{name}", kind="agent", name=name,
                            domain=domain, status="reference",
                            reason=f"source path not found: {src}",
                            source=dict(repo=source["repo"], commit=str(source["commit"]), path=src)))
        print(f"  REFERENCE agent {name:<24} (missing source {src})")
        return
    clean, reason = scan_clean(spath)
    lic = source.get("license", "UNKNOWN")
    if not clean or not common.is_permissive(lic):
        why = reason if not clean else f"non-permissive license {lic}"
        catalog.append(dict(id=f"agent/{domain}/{name}", kind="agent", name=name,
                            domain=domain, status="reference", reason=why,
                            source=dict(repo=source["repo"], commit=str(source["commit"]), path=src)))
        print(f"  REFERENCE agent {name:<24} ({why})")
        return

    fm, body = common.parse_frontmatter(spath.read_text(encoding="utf-8"))
    out_fm = {
        "name": name,
        "description": str(fm.get("description", "")),
        "domain": domain,
        "model": normalize_model(str(fm.get("model", "") or "")),
        "tags": common._as_list(fm.get("tags")),
        "source": {"repo": source["repo"], "commit": str(source["commit"]), "path": src},
        "license": lic,
    }
    if not out_fm["tags"]:
        del out_fm["tags"]
    out_dir = REG / "agents" / domain / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "agent.md"
    out_file.write_text(common.build_frontmatter(out_fm) + "\n" + body.lstrip("\n"),
                        encoding="utf-8")
    lock[str(out_file.relative_to(ROOT))] = sha256(out_file)
    catalog.append(dict(id=f"agent/{domain}/{name}", kind="agent", name=name,
                        domain=domain, status="vendored", license=lic,
                        description=out_fm["description"][:160],
                        source=dict(repo=source["repo"], commit=str(source["commit"]), path=src)))
    print(f"  VENDOR    agent {name:<24} [{lic}]")


def vendor_skill(cache: Path, sk: str, source: dict, lock: dict,
                 catalog: list, force_reference: bool = False) -> None:
    sdir = cache / source.get("skills_dir", "skills") / sk
    src_rel = f"{source.get('skills_dir', 'skills')}/{sk}"
    if not (sdir / "SKILL.md").is_file():
        catalog.append(dict(id=f"skill/{sk}", kind="skill", name=sk, status="reference",
                            reason="SKILL.md not found",
                            source=dict(repo=source["repo"], commit=str(source["commit"]), path=src_rel)))
        print(f"  REFERENCE skill {sk:<24} (no SKILL.md)")
        return
    fm, _ = common.parse_frontmatter((sdir / "SKILL.md").read_text(encoding="utf-8"))
    lic = detect_license(sdir, fm)
    clean, reason = scan_clean(sdir)
    permissive = common.is_permissive(lic)

    if force_reference or not permissive or not clean:
        why = ("forced reference (proprietary/unclear license)" if force_reference
               else (f"non-permissive license {lic}" if not permissive else reason))
        catalog.append(dict(id=f"skill/{sk}", kind="skill", name=sk, status="reference",
                            license=lic, reason=why,
                            source=dict(repo=source["repo"], commit=str(source["commit"]), path=src_rel)))
        print(f"  REFERENCE skill {sk:<24} [{lic}] ({why})")
        return

    out_dir = REG / "skills" / sk
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(sdir, out_dir, ignore=COPY_IGNORE)
    # inject provenance into the vendored SKILL.md
    sm = out_dir / "SKILL.md"
    fm2, body2 = common.parse_frontmatter(sm.read_text(encoding="utf-8"))
    fm2["source"] = {"repo": source["repo"], "commit": str(source["commit"]), "path": src_rel}
    fm2["license"] = lic
    sm.write_text(common.build_frontmatter(fm2) + "\n" + body2.lstrip("\n"), encoding="utf-8")
    for f in sorted(out_dir.rglob("*")):
        if f.is_file():
            lock[str(f.relative_to(ROOT))] = sha256(f)
    catalog.append(dict(id=f"skill/{sk}", kind="skill", name=str(fm2.get("name", sk)),
                        status="vendored", license=lic,
                        description=str(fm2.get("description", ""))[:160],
                        source=dict(repo=source["repo"], commit=str(source["commit"]), path=src_rel)))
    print(f"  VENDOR    skill {sk:<24} [{lic}]")


def register_submodule(source: dict, catalog: list) -> None:
    rel = f"sources/vendor/{source['id']}"
    dest = ROOT / rel
    if not dest.exists():
        subprocess.run(["git", "-C", str(ROOT), "submodule", "add", "-f",
                        source["repo"], rel], check=False)
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", str(source["commit"])],
                       check=False)
    catalog.append(dict(id=f"submodule/{source['id']}", kind="submodule",
                        name=source["id"], status="submodule", license=source.get("license", "see upstream"),
                        source=dict(repo=source["repo"], commit=str(source["commit"]), path=rel)))
    print(f"  SUBMODULE {source['id']} -> {rel}")


# --------------------------------------------------------------------------- #
# outputs
# --------------------------------------------------------------------------- #

def write_third_party(catalog: list) -> None:
    vendored = [c for c in catalog if c["status"] == "vendored"]
    refs = [c for c in catalog if c["status"] in ("reference", "submodule")]
    lines = ["# Third-Party Attributions", "",
             "Every item vendored into `registry/` retains its upstream license. The",
             "MIT license in `LICENSE` covers only this repo's original glue code.", "",
             "## Vendored content (copied into `registry/`)", ""]
    by_repo: dict[str, list] = {}
    for c in vendored:
        by_repo.setdefault(c["source"]["repo"], []).append(c)
    for repo, items in sorted(by_repo.items()):
        commit = items[0]["source"]["commit"]
        lines.append(f"### {repo}")
        lines.append(f"- Pinned commit: `{commit}`")
        for c in sorted(items, key=lambda x: x["id"]):
            lines.append(f"- `{c['id']}` — {c.get('license', '?')} — `{c['source']['path']}`")
        lines.append("")
    lines += ["## Referenced content (NOT copied — see upstream for license & install)", ""]
    for c in sorted(refs, key=lambda x: x["id"]):
        lines.append(f"- `{c['id']}` — {c.get('license', '?')} — {c['source']['repo']} "
                     f"(`{c['source']['path']}`) — _{c.get('reason', '')}_")
    lines.append("")
    (ROOT / "THIRD_PARTY.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    manifest = common.load_yaml((ROOT / "sources" / "manifest.yaml").read_text(encoding="utf-8"))
    lock: dict = {}
    catalog: list = []
    for source in manifest.get("sources", []):
        print(f"[sync] source {source['id']} ({source.get('mode')})")
        mode = source.get("mode")
        if mode == "submodule":
            register_submodule(source, catalog)
            continue
        cache = ensure_clone(source)
        for a in source.get("agents", []) or []:
            vendor_agent(cache, a["src"], a["name"], a["domain"], source, lock, catalog)
        for sk in source.get("skills", []) or []:
            vendor_skill(cache, sk, source, lock, catalog)
        for sk in source.get("reference", []) or []:
            vendor_skill(cache, sk, source, lock, catalog, force_reference=True)

    # Catalog + lock any original (authored-in-repo) content not from a source.
    known = {c["id"] for c in catalog}
    for item in common.load_registry(REG):
        if item.id in known:
            continue
        files = [item.path] if item.kind == "agent" else [
            f for f in item.path.rglob("*") if f.is_file()]
        for f in files:
            lock[str(f.relative_to(ROOT))] = sha256(f)
        catalog.append(dict(id=item.id, kind=item.kind, name=item.name,
                            domain=item.domain, status="original",
                            license=item.license or "MIT",
                            description=item.description[:160],
                            source=dict(repo="original", commit="original",
                                        path=str(item.path.relative_to(ROOT)))))
        print(f"  ORIGINAL  {item.kind} {item.name}")

    (ROOT / "sources" / "lock.json").write_text(
        common.json.dumps(dict(sorted(lock.items())), indent=2) + "\n", encoding="utf-8")
    catalog_doc = {
        "generated_from": "sources/manifest.yaml",
        "counts": {
            "vendored": sum(1 for c in catalog if c["status"] == "vendored"),
            "original": sum(1 for c in catalog if c["status"] == "original"),
            "reference": sum(1 for c in catalog if c["status"] == "reference"),
            "submodule": sum(1 for c in catalog if c["status"] == "submodule"),
        },
        "items": sorted(catalog, key=lambda c: (c["kind"], c["id"])),
    }
    (ROOT / "catalog.yaml").write_text(common.dump_yaml(catalog_doc) + "\n", encoding="utf-8")
    write_third_party(catalog)

    c = catalog_doc["counts"]
    print(f"\n[sync] done: {c['vendored']} vendored, {c['reference']} reference, "
          f"{c['submodule']} submodule. Wrote catalog.yaml, sources/lock.json, THIRD_PARTY.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
