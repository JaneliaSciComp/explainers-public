#!/bin/sh
# Install the pre-push hook: it runs the leak scan (scripts/scan_public.py --pre-push), then git-lfs's own
# pre-push step, which uploads the video. Run it from anywhere inside a clone of this repo.
#
# It replaces the stock hook that `git lfs install` writes, which only runs `git lfs pre-push`, and rewrites
# a hook that this script wrote earlier. It refuses any other pre-push hook: merge that one by hand.
# It does not set core.hooksPath, which would switch off every other hook in .git/hooks.
set -eu
top=$(git rev-parse --show-toplevel)
cd "$top"
hooks=$(git rev-parse --git-path hooks)
hook="$hooks/pre-push"
marker='# explainers-public pre-push hook, written by scripts/install-hooks.sh'

# A stock git-lfs pre-push hook, from any git-lfs version: a "#!/bin/sh" line, one line that starts with
# "command -v git-lfs >/dev/null 2>&1 ||" and ends with "exit 2; }", and the line git lfs pre-push "$@",
# with nothing else but blank lines.
is_stock() {
  awk '
    /^[ \t\r]*$/ { next }
    { sub(/\r$/, ""); n++ }
    n == 1 { ok = ($0 == "#!/bin/sh"); next }
    n == 2 { ok = ok && index($0, "command -v git-lfs >/dev/null 2>&1 ||") == 1 && substr($0, length($0) - 8) == "exit 2; }"; next }
    n == 3 { ok = ok && ($0 == "git lfs pre-push \"$@\""); next }
    { ok = 0 }
    END { exit !(ok && n == 3) }
  ' "$1"
}

if [ -e "$hook" ]; then
  if grep -qxF "$marker" "$hook"; then
    action="rewrote the hook this script wrote earlier"
  elif is_stock "$hook"; then
    action="replaced git-lfs's stock pre-push hook"
  else
    echo >&2 "install-hooks: $hook exists and is neither git-lfs's stock hook nor one this script wrote."
    echo >&2 "install-hooks: refusing to overwrite it. Merge it by hand, or move it aside and run this again."
    exit 1
  fi
else
  action="wrote a new hook"
fi

mkdir -p "$hooks"
cat > "$hook" <<EOF
#!/bin/sh
$marker
# Rerun scripts/install-hooks.sh to update it. Blocks the push on a leak-scan hit, then lets git-lfs upload.
command -v git-lfs >/dev/null 2>&1 || { echo >&2 "pre-push: git-lfs was not found on your path; it is needed to push the video."; exit 2; }
input=\$(mktemp) || exit 1
trap 'rm -f "\$input"' EXIT
cat > "\$input"
python3 -I -B "\$(git rev-parse --show-toplevel)/scripts/scan_public.py" --pre-push < "\$input" || {
  echo >&2 "pre-push: the leak scan refused this push (exit \$?); its output above says why. Fix that, then push again."
  exit 1
}
git lfs pre-push "\$@" < "\$input"
EOF
chmod +x "$hook"
echo "install-hooks: $action: $hook"
