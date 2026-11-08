#!/usr/bin/env python3
"""Leak scan: refuse private names in anything this public repo pushes (Python 3 standard library only).

Usage, from anywhere inside the repo:
    python3 -I -B scripts/scan_public.py --all [--rev REV]   # everything reachable from REV (default HEAD)
    python3 -I -B scripts/scan_public.py --pre-push          # what a push sends; reads git's pre-push lines on stdin
    python3 -I -B scripts/scan_public.py --worktree          # what --all scans, plus the files not yet committed
    python3 -I -B scripts/scan_public.py --all --builtin-only   # the built-in patterns only, with no list (for CI)

It matches every string in the forbidden list, ignoring case and inside words, plus two built-in patterns (a
session URL and an absolute home folder), against everything in its range:
  - every commit and every annotated tag object, as text: message, author, committer and tagger lines;
  - every path in the commits' trees, and, with --pre-push, the local and remote ref names the push sends;
  - every text blob, line by line;
  - every binary blob (a NUL byte in its first 8000 bytes), through its printable ASCII runs of 4 or more bytes,
    which is what `strings` prints. Image metadata stored as plain text, such as a PNG tEXt chunk, is caught this
    way, but compressed text, such as a zTXt chunk, is not;
  - for a Git LFS pointer, the pointer as text and the object it names from .git/lfs/objects, through its
    printable runs. An object not present here is counted in the summary and not scanned. A push still scans
    each new object, because git-lfs uploads only objects present locally.
A hit is reported by place and list entry number, never by the matched text, so no log prints a private name.
A hit in binary content has no line number.

The list is found in this order: --forbidden PATH, then $EXPLAINERS_FORBIDDEN_LIST, then
../explainers-private/forbidden-strings.txt beside this repo. It holds one string per line; blank lines and
lines that start with # are skipped. scripts/build_units.py loads it with the same functions.

--pre-push scans only what the remote lacks: the new commits and tags, the objects they add, every path in the
new commits' trees, and the ref names. A new branch or tag, or a remote commit missing here, gets a full scan of
what it points to. With --all --rev, an annotated tag stays the tip, so its tag object is scanned too.
--worktree scans what --all scans from HEAD, plus two commits that no ref points to: the staged files, which the
next commit would hold, and every file that `git add -A` would stage. It writes objects inside .git, and changes no
ref, no index and no file outside .git. It cannot see the next commit's message or author, or the commits that a
merge in progress would add; the pre-push hook scans those when they are pushed.
Exit status: 0 no hits, 1 at least one hit, 2 the list is missing or the scan cannot run.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIST_ENV = "EXPLAINERS_FORBIDDEN_LIST"
SIBLING_LIST = REPO.parent / "explainers-private" / "forbidden-strings.txt"
BUILTIN = [("a session URL", re.compile(r"claude\.ai/code/session_", re.I)),
           ("an absolute home folder", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+/"))]
ZERO = re.compile(r"^0+$")
BINARY_PROBE = 8000
PRINTABLE_RUN = re.compile(rb"[\x20-\x7e]{4,}")
LFS_POINTER = re.compile(r"\Aversion https://git-lfs\.github\.com/spec/v1\n(?:.*\n)*?oid sha256:([0-9a-f]{64})\n")


# ---------------------------------------------------------------------------------------------- the list

def find_list(explicit: str | None = None) -> Path | None:
    """The forbidden list's path, in lookup order; None when no list is named and none sits beside the repo."""
    if explicit:
        return Path(explicit)
    if os.environ.get(LIST_ENV):
        return Path(os.environ[LIST_ENV])
    return SIBLING_LIST if SIBLING_LIST.is_file() else None


def load_list(path: Path) -> list[str]:
    """One string per line; blank lines and lines starting with # are skipped. Raises OSError if unreadable."""
    out = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


# ---------------------------------------------------------------------------------------------- matching

class Scanner:
    def __init__(self, entries: list[str]) -> None:
        self.entries = [e.lower() for e in entries]
        # One pattern, longest entry first, so that an entry inside a longer one cannot leave part of it shown.
        longest = sorted(self.entries, key=len, reverse=True)
        self.any_entry = re.compile("|".join(map(re.escape, longest)), re.I) if longest else None
        self.hits = 0

    def find(self, text: str) -> list[tuple[str, int]]:
        """(label, offset) for each match; the label names a list entry by number or a built-in pattern."""
        low = text.lower()
        out = []
        for k, e in enumerate(self.entries, 1):
            out += [(f"list entry {k}", m.start()) for m in re.finditer(re.escape(e), low)]
        for name, rx in BUILTIN:
            out += [(f"built-in pattern: {name}", m.start()) for m in rx.finditer(text)]
        return out

    def mask(self, text: str) -> str:
        """The text with every match replaced by ***, so a path that holds a match can be printed."""
        if self.any_entry:
            text = self.any_entry.sub("***", text)
        for _, rx in BUILTIN:
            text = rx.sub("***", text)
        return text

    def scan_text(self, where: str, text: str) -> None:
        found: dict[str, list[int]] = {}
        for label, i in self.find(text):
            found.setdefault(label, []).append(text.count("\n", 0, i) + 1)
        for label, lines in found.items():
            ls = sorted(set(lines))
            more = f" and {len(ls) - 5} more" if len(ls) > 5 else ""
            print(f"HIT {self.mask(where)} line {', '.join(map(str, ls[:5]))}{more}: {label}")
            self.hits += 1

    def scan_binary(self, where: str, data: bytes) -> None:
        """The printable ASCII runs of binary content, as `strings` shows them; a hit has no line number."""
        runs = "\n".join(m.group().decode("ascii") for m in PRINTABLE_RUN.finditer(data))
        for label in sorted({label for label, _ in self.find(runs)}):
            print(f"HIT {self.mask(where)} (binary content): {label}")
            self.hits += 1

    def scan_path(self, path: str, kind: str = "path") -> None:
        labels = sorted({label for label, _ in self.find(path)})
        for label in labels:
            print(f"HIT {kind} {self.mask(path)}: {label}")
            self.hits += 1


# ---------------------------------------------------------------------------------------------- git

def git(*args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], input=stdin, capture_output=True, check=True).stdout


def exists(sha: str) -> bool:
    return subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def lfs_dir() -> Path:
    """Git LFS keeps its objects in the common git folder, which a linked worktree shares with the main one."""
    d = Path(git("rev-parse", "--git-common-dir").decode().strip()) / "lfs" / "objects"
    return d if d.is_absolute() else REPO / d


def scan_range(sc: Scanner, tips: list[str], exclude: list[str]) -> dict[str, int]:
    """Scan what is reachable from tips but not from exclude: commits and tags as text, every path in the commits'
    trees, the blobs they add, and the LFS objects those blobs point to."""
    rng = tips + [f"^{x}" for x in exclude]
    commits = git("rev-list", *rng).decode().split()
    for c in commits:
        raw = git("cat-file", "commit", c).decode("utf-8", "replace")
        sc.scan_text(f"commit {c[:12]}", raw)
    paths: set[str] = set()
    for c in commits:
        for rec in git("ls-tree", "-r", "-t", "-z", "--name-only", c).decode("utf-8", "replace").split("\0"):
            if rec:
                paths.add(rec)
    for p in sorted(paths):
        sc.scan_path(p)
    named: dict[str, str] = {}
    for line in git("rev-list", "--objects", *rng).decode("utf-8", "replace").splitlines():
        sha, _, name = line.partition(" ")
        named.setdefault(sha, name)
    shas = list(named)
    kinds = git("cat-file", "--batch-check=%(objectname) %(objecttype)", stdin="\n".join(shas).encode() + b"\n")
    typed = [ln.split() for ln in kinds.decode().splitlines()]
    blobs = [s for s, t in typed if t == "blob"]
    tags = [s for s, t in typed if t == "tag"]
    for s in tags:
        sc.scan_text(f"tag {s[:12]}", git("cat-file", "tag", s).decode("utf-8", "replace"))
    binary = lfs = lfs_missing = 0
    if blobs:
        data = git("cat-file", "--batch", stdin="\n".join(blobs).encode() + b"\n")
        i = 0
        for sha in blobs:
            j = data.index(b"\n", i)
            size = int(data[i:j].split()[2])
            body = data[j + 1:j + 1 + size]
            i = j + 1 + size + 1
            where = f"file {named[sha] or sha[:12]}"
            if b"\0" in body[:BINARY_PROBE]:
                binary += 1
                sc.scan_binary(where, body)
                continue
            text = body.decode("utf-8", "replace")
            sc.scan_text(where, text)
            m = LFS_POINTER.match(text)
            if m:
                oid = m.group(1)
                obj = lfs_dir() / oid[:2] / oid[2:4] / oid
                if obj.is_file():
                    lfs += 1
                    sc.scan_binary(f"{where} (LFS object)", obj.read_bytes())
                else:
                    lfs_missing += 1
    return {"commits": len(commits), "tags": len(tags), "paths": len(paths), "blobs": len(blobs), "binary": binary,
            "lfs": lfs, "lfs_missing": lfs_missing}


def pre_push_ranges(lines: list[str]) -> tuple[list[tuple[list[str], list[str]]], list[str]]:
    """git's pre-push lines -> (tips, exclude) pairs, and the ref names sent. A deleted ref is skipped; a new
    branch or tag gets a full scan."""
    out, refs = [], []
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local, remote_ref, remote = parts
        if ZERO.match(local):
            continue
        refs += [local_ref, remote_ref]
        out.append(([local], [] if ZERO.match(remote) or not exists(remote) else [remote]))
    return out, refs


def worktree_commit() -> str:
    """Two commits that no ref points to, on top of HEAD: the staged files, then every file that `git add -A` would
    stage. Returns the second. It works on a copy of the index, so the real index, the refs and the files stay as
    they are."""
    index = Path(git("rev-parse", "--git-path", "index").decode().strip())
    index = index if index.is_absolute() else REPO / index
    git_dir = Path(git("rev-parse", "--git-dir").decode().strip())
    git_dir = git_dir if git_dir.is_absolute() else REPO / git_dir
    who = {"GIT_AUTHOR_NAME": "scan_public", "GIT_AUTHOR_EMAIL": "scan@example.invalid",
           "GIT_COMMITTER_NAME": "scan_public", "GIT_COMMITTER_EMAIL": "scan@example.invalid"}
    with tempfile.TemporaryDirectory(dir=git_dir) as d:  # inside .git, so that no list of paths lands in /tmp
        env = {**os.environ, **who, "GIT_INDEX_FILE": str(Path(d) / "index")}

        def run(*args: str) -> str:
            return subprocess.run(["git", "-C", str(REPO), *args], env=env, capture_output=True,
                                  check=True).stdout.decode().strip()

        if index.is_file():
            # copy2 keeps the index's mtime. Git compares it with each entry's mtime to find a file that changed in
            # the instant it was staged, and a newer copy would hide such a change.
            shutil.copy2(index, env["GIT_INDEX_FILE"])
        else:
            run("read-tree", "HEAD")
        staged = run("commit-tree", run("write-tree"), "-p", "HEAD", "-m", "scan_public --worktree: the staged files")
        run("add", "-A")
        return run("commit-tree", run("write-tree"), "-p", staged, "-m", "scan_public --worktree: the files on disk")


# ---------------------------------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="scan everything reachable from --rev")
    mode.add_argument("--pre-push", action="store_true", help="scan what a push sends (git's pre-push lines on stdin)")
    mode.add_argument("--worktree", action="store_true",
                      help="scan what --all scans from HEAD, plus the staged files and the files on disk")
    ap.add_argument("--rev", default="HEAD", help="with --all, the revision to scan from (default HEAD)")
    ap.add_argument("--builtin-only", action="store_true", help="use only the built-in patterns; no list needed")
    ap.add_argument("--forbidden", metavar="PATH", help="the forbidden list (else $%s, else the sibling repo)" % LIST_ENV)
    args = ap.parse_args()

    entries: list[str] = []
    if not args.builtin_only:
        path = find_list(args.forbidden)
        if path is None:
            print(f"scan_public: no forbidden list (--forbidden, ${LIST_ENV}, or {SIBLING_LIST.name} in a sibling "
                  "explainers-private clone); refusing to scan without it. Use --builtin-only to skip it.")
            return 2
        try:
            entries = load_list(path)
        except OSError as e:
            print(f"scan_public: cannot read the forbidden list: {e.strerror}")
            return 2
        if not entries:
            print("scan_public: the forbidden list has no entries; refusing to scan without it")
            return 2
    sc = Scanner(entries)

    refs: list[str] = []
    if args.all or args.worktree:
        rev = args.rev
        if args.worktree:
            try:
                rev = worktree_commit()
            except subprocess.CalledProcessError as e:
                print("scan_public: cannot make the commits of the working tree: "
                      + sc.mask(e.stderr.decode("utf-8", "replace").strip()))
                return 2
            print("scan_public: scanning the staged files and the files on disk as commits that no ref points to")
        try:  # keep an annotated tag as the tip, so that its tag object is scanned
            git("rev-parse", "--verify", f"{rev}^{{commit}}")
            tip = git("rev-parse", "--verify", rev).decode().strip()
        except subprocess.CalledProcessError:
            print(f"scan_public: no commit at {sc.mask(rev)!r}")
            return 2
        ranges = [([tip], [])]
    else:
        ranges, refs = pre_push_ranges(sys.stdin.read().splitlines())
    for r in dict.fromkeys(refs):
        sc.scan_path(r, kind="ref")
    total = dict.fromkeys(("commits", "tags", "paths", "blobs", "binary", "lfs", "lfs_missing"), 0)
    for tips, exclude in ranges:
        for k, v in scan_range(sc, tips, exclude).items():
            total[k] += v
    what = "built-in patterns only" if args.builtin_only else f"{len(entries)} list entries and the built-in patterns"
    missing = f", {total['lfs_missing']} LFS objects not present here, not scanned" if total["lfs_missing"] else ""
    print(f"scan_public: {what}; {total['commits']} commits, {total['tags']} tags, {len(set(refs))} ref names, "
          f"{total['paths']} paths, {total['blobs']} blobs ({total['binary']} binary), {total['lfs']} LFS objects"
          f"{missing}: {sc.hits} hits" + ("" if sc.hits else " - OK"))
    return 1 if sc.hits else 0


if __name__ == "__main__":
    sys.exit(main())
