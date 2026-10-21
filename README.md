# BCD AltStore source

An unofficial AltStore Classic and SideStore source for the latest stable
[BCD release](https://github.com/thebcd69/bcd-games/releases), developed by thebcd69.

**Source URL:** <https://le0-vv.github.io/bcd-altsource/source.json>

Add that URL under Sources in AltStore Classic or SideStore. You can also open
the [source page](https://le0-vv.github.io/bcd-altsource/) on your device.
This source distributes a sideloading IPA. It does not support AltStore PAL.

GitHub Actions checks upstream at 17 minutes past each hour, on pushes to `main`,
and when you run the workflow manually. Scheduled runs can be delayed by GitHub.
The source contains the latest stable release only. Drafts and prereleases are
excluded. IPA downloads point directly to the original GitHub release asset.

The generator verifies the IPA size and SHA-256 digest against GitHub's release
metadata. It reads the app version, build number, bundle identifier, minimum iOS
version, entitlements and privacy descriptions from the IPA. It includes the
permissions of embedded app extensions. The source icon uses the upstream image
at the release tag.

Unchanged releases do not require another IPA download or Pages deployment.
Release notes and replacement assets also trigger an update. A failed check
leaves the previous Pages deployment in place. No personal access token is
required. The workflow uses GitHub's temporary token.

GitHub can disable scheduled workflows in public repositories after 60 days
without repository activity. If that happens, re-enable this workflow in Actions.

## Local checks

Use Python 3.13 on macOS. The generator uses the system `codesign` command to read
the IPA's entitlements. It does not run the downloaded executable.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/update_source.py --force
python3 -m http.server 8000 --directory site
```

If you already have the official IPA, use
`python3 scripts/update_source.py --force --ipa /absolute/path/BCD.ipa`.
The file must match the latest stable release checksum.

## GitHub Pages setup

This repository uses **Settings → Pages → Build and deployment → GitHub Actions**.
The workflow uploads only the generated `site/` directory. Generated files and
downloaded IPA files are not committed to Git.

Source format reference: [AltStore's developer documentation](https://faq.altstore.io/developers/make-a-source).
