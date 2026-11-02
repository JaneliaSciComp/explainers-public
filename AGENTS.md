# Instructions for agents

This public repo holds general concept units. `units/README.md` is the guide to writing one; read it before you
change a page.

## Keep the units general

- A unit teaches one general idea. It never names a project, a person, private data or private results, and it
  never quotes a project's code. That material belongs in an explanation kept elsewhere, which links to the unit.
- Write no local paths: no home folders and no paths into another checkout. Write commands relative to this
  repo's root.
- Everything pushed here is public at once, including commit messages. Treat a push as irreversible.

## Build and check before each commit

```sh
python3 -I -B scripts/build_units.py
python3 -I -B scripts/build_units.py --check --require-all
node scripts/render_check_units.mjs tmp/units-shots --only <changed unit ids>
```

Fix every error. The build writes the generated blocks and `units/index.html`; do not edit those by hand.

## Push only through the hook

- Install the pre-push hook once per clone with `sh scripts/install-hooks.sh`. It runs the leak scan
  `scripts/scan_public.py --pre-push`, then `git lfs pre-push`.
- Never bypass it with `git push --no-verify`. If the scan reports a hit, fix the file, path or commit message.
- Put no session URLs, such as links to an AI assistant's session, in commit messages or pull requests.
