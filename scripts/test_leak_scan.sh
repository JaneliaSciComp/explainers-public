#!/usr/bin/env bash
# Test the leak scan, the pre-push hook and the build check's handling of the forbidden list.
#
# Usage, from anywhere in the repo:  bash scripts/test_leak_scan.sh
#
# Each run deletes and rebuilds tmp/leak-scan-test/ in this repo, which git ignores. There it makes a bare repo as
# the origin, and a work repo that holds a copy of this clone's files: every file that git tracks or would add, as it
# is on disk. So the test also covers changes to the scripts that are not committed yet. The forbidden list is made
# up: one word, new on each run, passed through $EXPLAINERS_FORBIDDEN_LIST. No real list entry is used, and the word
# appears in no file of the repo. Commits use a throwaway identity, given with -c; git config is never changed.
#
# It needs Git LFS, rsync and Python 3, and the video's LFS object in this clone, which a clone made with Git LFS
# installed has. It prints PASS or FAIL for each case, and writes the details to tmp/leak-scan-test/log.txt. Exit
# status 1 means that a case failed.
set -u
SRC=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
T=$SRC/tmp/leak-scan-test
WORD=leakword$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')
ZERO=0000000000000000000000000000000000000000
rm -rf "$T"
mkdir -p "$T"
LOG=$T/log.txt
: > "$LOG"
printf '# A made-up list for this test.\n\n%s\n' "$WORD" > "$T/list.txt"
: > "$T/empty.txt"
printf '# only a comment\n\n' > "$T/comment-only.txt"
export EXPLAINERS_FORBIDDEN_LIST=$T/list.txt

fails=0
result() {  # result NAME STATUS: PASS when STATUS is 0
  if [ "$2" = 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fails=$((fails + 1)); fi
  echo "=== $1: $([ "$2" = 0 ] && echo PASS || echo FAIL)" >> "$LOG"
}
G() { git -c user.name=test -c user.email=test@example.invalid "$@"; }
scan() { python3 -I -B scripts/scan_public.py "$@"; }
exits() {  # exits WANT CMD...: run CMD, log its output, and succeed when its exit status is WANT
  local want=$1; shift
  echo "\$ $* (want exit $want)" >> "$LOG"
  "$@" >> "$LOG" 2>&1
  local got=$?
  echo "exit $got" >> "$LOG"
  [ "$got" = "$want" ]
}
remote_refs() { git -C "$T/origin.git" for-each-ref --format='%(refname) %(objectname)'; }
refused() {  # refused PUSH-ARGS...: the push fails and the bare repo's refs do not change
  local before; before=$(remote_refs)
  echo "\$ git push $* (want refused)" >> "$LOG"
  if git push "$@" >> "$LOG" 2>&1; then echo "push succeeded" >> "$LOG"; return 1; fi
  [ "$(remote_refs)" = "$before" ] || { echo "the bare repo's refs changed" >> "$LOG"; return 1; }
}
prepush() {  # prepush LOCAL-REF LOCAL-SHA REMOTE-REF REMOTE-SHA: the scan of what that push line sends
  printf '%s %s %s %s\n' "$@" | scan --pre-push
}
reset_work() {
  git checkout -q main
  git reset -q --hard origin/main
  git clean -qfd
  for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do [ "$b" = main ] || git branch -qD "$b"; done
  for t in $(git tag); do git tag -d "$t" > /dev/null; done
}

# ----------------------------------------------------------------------------------------------- set up
git init -q --bare "$T/origin.git"
git init -q -b main "$T/work"
cd "$T/work"
git lfs install --local > /dev/null
git -C "$SRC" ls-files -z --cached --others --exclude-standard |
  rsync -a --from0 --files-from=- "$SRC/" ./ >> "$LOG" 2>&1
git remote add origin "file://$T/origin.git"

# ----------------------------------------------------------------------------------------------- the installer
out=$(sh scripts/install-hooks.sh 2>&1); echo "$out" >> "$LOG"
case $out in *"replaced git-lfs's stock pre-push hook"*) s=0 ;; *) s=1 ;; esac
result "installer replaces the stock git-lfs hook (this git-lfs)" $s

cat > .git/hooks/pre-push <<'EOF'
#!/bin/sh
command -v git-lfs >/dev/null 2>&1 || { echo >&2 "\nThis repository is configured for Git LFS but 'git-lfs' was not found on your path. If you no longer wish to use Git LFS, remove this hook by deleting .git/hooks/pre-push.\n"; exit 2; }

git lfs pre-push "$@"
EOF
out=$(sh scripts/install-hooks.sh 2>&1); echo "$out" >> "$LOG"
case $out in *"replaced git-lfs's stock pre-push hook"*) s=0 ;; *) s=1 ;; esac
result "installer replaces a stock git-lfs hook with another version's wording and a blank line" $s

out=$(sh scripts/install-hooks.sh 2>&1); echo "$out" >> "$LOG"
case $out in *"rewrote the hook this script wrote earlier"*) s=0 ;; *) s=1 ;; esac
result "installer rewrites its own hook" $s

cp .git/hooks/pre-push "$T/our-hook"
printf '#!/bin/sh\necho another hook\ngit lfs pre-push "$@"\n' > .git/hooks/pre-push
cp .git/hooks/pre-push "$T/other-hook"
exits 1 sh scripts/install-hooks.sh && cmp -s .git/hooks/pre-push "$T/other-hook"; s=$?
result "installer refuses any other hook and leaves it alone" $s
cp "$T/our-hook" .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# ----------------------------------------------------------------------------------------------- a clean push
G add -A
G commit -q -m "Test commit: the public tree"
s=0
exits 0 scan --all || s=1
exits 0 git push -u origin main || s=1
oid=$(git -C "$T/origin.git" cat-file -p main:units/media/flow-matching.mp4 | sed -n 's/^oid sha256://p')
obj=$T/origin.git/lfs/objects/${oid:0:2}/${oid:2:2}/$oid
echo "video oid $oid; object in the bare repo: $(ls -l "$obj" 2>&1)" >> "$LOG"
[ -n "$oid" ] && [ -f "$obj" ] && [ "$(wc -c < "$obj")" = "$(wc -c < "$(git rev-parse --git-path lfs/objects)/${oid:0:2}/${oid:2:2}/$oid")" ] || s=1
result "clean push succeeds, and the bare repo holds the video as an LFS object" $s
BASE=$(git rev-parse HEAD)

# ----------------------------------------------------------------------------------------------- leaks a push must refuse
# Each case: the scan exits 1 (--all where the word is in the history, and --pre-push on the line the push sends),
# then the hook refuses the push and the bare repo does not change.

python3 -I -B - units/vectors.html "$WORD" <<'EOF'
import sys
path, word = sys.argv[1], sys.argv[2]
h2 = "<h2>The idea in one paragraph</h2>"
s = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(s.replace(h2, h2 + "<p>see " + word + "</p>", 1))
EOF
G commit -q -am "Test: edit a page"
s=0
exits 1 scan --all || s=1
exits 1 prepush refs/heads/main "$(git rev-parse HEAD)" refs/heads/main "$BASE" || s=1
refused origin main || s=1
result "the word in a page: scan exits 1, hook refuses the push" $s
reset_work

echo "<!-- harmless -->" >> units/vectors.html
G commit -q -am "Test: a note about $WORD"
s=0
exits 1 scan --all || s=1
exits 1 prepush refs/heads/main "$(git rev-parse HEAD)" refs/heads/main "$BASE" || s=1
refused origin main || s=1
result "the word in a commit message only: scan exits 1, hook refuses the push" $s
reset_work

git mv units/media/src/README.md "units/media/src/$WORD-notes.md"
G commit -q -m "Test: rename a file"
s=0
exits 1 scan --all || s=1
exits 1 prepush refs/heads/main "$(git rev-parse HEAD)" refs/heads/main "$BASE" || s=1
refused origin main || s=1
result "the word in a file name: scan exits 1, hook refuses the push" $s
reset_work

git branch "feature-$WORD"
s=0
exits 1 prepush "refs/heads/feature-$WORD" "$BASE" "refs/heads/feature-$WORD" $ZERO || s=1
refused origin "feature-$WORD" || s=1
result "the word in a branch name: scan exits 1, hook refuses the push" $s
reset_work

G tag -a v-test -m "Test: a tag about $WORD"
s=0
exits 1 prepush refs/tags/v-test "$(git rev-parse v-test)" refs/tags/v-test $ZERO || s=1
refused origin v-test || s=1
result "the word in an annotated tag's message, the tag pushed alone: scan exits 1, hook refuses the push" $s
s=0
exits 0 scan --all || s=1
exits 1 scan --all --rev v-test || s=1
result "scan_public.py --all --rev <annotated tag>, the word only in the tag's message: exits 1 (and 0 at HEAD)" $s
reset_work

python3 -I -B - units/media/flow-matching-poster.png "$WORD" <<'EOF'
import struct, sys, zlib
path, word = sys.argv[1], sys.argv[2]
png = open(path, 'rb').read()
end_of_ihdr = 8 + 8 + 13 + 4
data = b'Comment\x00made with ' + word.encode()
chunk = struct.pack('>I', len(data)) + b'tEXt' + data + struct.pack('>I', zlib.crc32(b'tEXt' + data) & 0xffffffff)
open(path, 'wb').write(png[:end_of_ihdr] + chunk + png[end_of_ihdr:])
EOF
G commit -q -am "Test: image metadata"
s=0
exits 1 scan --all || s=1
exits 1 prepush refs/heads/main "$(git rev-parse HEAD)" refs/heads/main "$BASE" || s=1
refused origin main || s=1
result "the word in an image's metadata (a PNG tEXt chunk): scan exits 1, hook refuses the push" $s
reset_work

python3 -I -B - units/media/test-clip.mp4 "$WORD" <<'EOF'
import sys
path, word = sys.argv[1], sys.argv[2]
open(path, 'wb').write(b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00' + b'title ' + word.encode() + b'\x00' * 64)
EOF
G add units/media/test-clip.mp4
G commit -q -m "Test: a new video"
clip_oid=$(git cat-file -p HEAD:units/media/test-clip.mp4 | sed -n 's/^oid sha256://p')
s=0
git cat-file -p HEAD:units/media/test-clip.mp4 | grep -q "^version https://git-lfs" || s=1
git cat-file -p HEAD:units/media/test-clip.mp4 | grep -qi "$WORD" && s=1
exits 1 scan --all || s=1
exits 1 prepush refs/heads/main "$(git rev-parse HEAD)" refs/heads/main "$BASE" || s=1
refused origin main || s=1
[ -e "$T/origin.git/lfs/objects/${clip_oid:0:2}/${clip_oid:2:2}/$clip_oid" ] && s=1
result "the word in an LFS object's content only: scan exits 1, hook refuses the push, nothing uploaded" $s
reset_work

# ----------------------------------------------------------------------------------------------- --worktree
# Each case starts from a clean work repo. --worktree must find the word wherever the next commit, or `git add -A`,
# would hold it, and must change nothing: HEAD, the refs, the status and the index are the same after the scan.
state() {
  git rev-parse HEAD
  git for-each-ref
  git --no-optional-locks status --porcelain --untracked-files=all
  cksum < "$(git rev-parse --git-path index)"
}
wt() {  # wt WANT NAME: scan --worktree exits WANT and changes nothing in the work repo
  local before s=0; before=$(state)
  exits "$1" scan --worktree || s=1
  [ "$(state)" = "$before" ] || { echo "the scan changed the work repo" >> "$LOG"; s=1; }
  result "--worktree, $2: exits $1 and changes nothing" $s
  reset_work
  rm -rf tmp
}
wt 0 "a clean tree"

printf '<p>%s</p>\n' "$WORD" > units/new-page.html
wt 1 "the word in an untracked file"

echo "<!-- $WORD -->" >> units/vectors.html
wt 1 "the word in a changed file that is not staged"

echo "<!-- $WORD -->" >> units/vectors.html
G add units/vectors.html
git show HEAD:units/vectors.html > units/vectors.html
wt 1 "the word staged, then removed from the file on disk"

mkdir -p tmp && echo "$WORD" > tmp/notes.txt
G add -f tmp/notes.txt
wt 1 "the word in an ignored file staged with git add -f"

mkdir -p tmp && echo "$WORD" > tmp/notes.txt
wt 0 "the word in an ignored file that is not staged"

echo hi > "units/$WORD-page.html"
wt 1 "the word in the name of an untracked file"

python3 -I -B - units/media/wt-clip.mp4 "$WORD" <<'EOF'
import sys
path, word = sys.argv[1], sys.argv[2]
open(path, 'wb').write(b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00' + b'title ' + word.encode() + b'\x00' * 64)
EOF
wt 1 "the word in a new LFS file that is not committed"

echo "<!-- harmless -->" >> units/vectors.html
G commit -q -am "Test: a commit about $WORD that is not pushed"
wt 1 "the word in a commit that is not pushed"

# ----------------------------------------------------------------------------------------------- other rules
lfs=$(git rev-parse --git-path lfs/objects)/${oid:0:2}/${oid:2:2}/$oid
mv "$lfs" "$T/video.aside"
out=$(scan --all 2>&1); st=$?; echo "$out" >> "$LOG"
mv "$T/video.aside" "$lfs"
s=1; [ "$st" = 0 ] && case $out in *"1 LFS objects not present here, not scanned"*) s=0 ;; esac
result "an LFS object not present here is counted in the summary, and the scan still passes" $s

exits 2 env -u EXPLAINERS_FORBIDDEN_LIST python3 -I -B scripts/scan_public.py --all; s=$?
result "scan_public.py with no list exits 2" $s

out=$(scan --all --rev "$WORD" 2>&1); st=$?; echo "$out" >> "$LOG"
s=1; [ "$st" = 2 ] && ! printf '%s' "$out" | grep -qi "$WORD" && s=0
result "scan_public.py --rev <no such revision> exits 2 and masks the revision" $s

s=0
for list in empty.txt comment-only.txt; do
  out=$(EXPLAINERS_FORBIDDEN_LIST=$T/$list python3 -I -B scripts/build_units.py --check 2>&1); st=$?; echo "$out" >> "$LOG"
  [ "$st" = 1 ] && case $out in *"the forbidden list has no entries"*) ;; *) s=1 ;; esac || s=1
done
result "build_units.py --check with an empty or comment-only list reports an error" $s

s=0
out=$(env -u EXPLAINERS_FORBIDDEN_LIST python3 -I -B scripts/build_units.py --check 2>&1); st=$?; echo "$out" >> "$LOG"
[ "$st" = 0 ] && case $out in *"notice: no forbidden list"*) ;; *) s=1 ;; esac || s=1
result "build_units.py --check with no list prints the notice and passes" $s

echo
if [ "$fails" = 0 ]; then echo "test_leak_scan: all cases passed (log: $LOG)"; else echo "test_leak_scan: $fails cases FAILED (log: $LOG)"; fi
[ "$fails" = 0 ]
