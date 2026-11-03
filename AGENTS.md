# Instructions for agents

This public repo holds general concept units. Before you write, check, review or fix a unit, read
`skills/explainer-units/SKILL.md` and follow it. It gives the steps of each task and points to the reference files
that hold the rules. `units/README.md` gives the mechanics: the manifest, the page parts and the commands.

## Keep the units general

- A unit teaches one general idea. It never names a project that is not public, and never quotes or describes one
  project's code, data, people or results, even without naming them. That material belongs in an explanation kept
  elsewhere, which links to the unit. Public attribution is fine, such as the author or site of a "Go further" item.
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
