# Working on Petrolmate

Notes for anyone (person or AI) changing this integration's code.

## Releases

A push or merge into `main` publishes a release (which HACS / the Marketplace picks up) when a commit in it
has a message starting with `major:`, `minor:` or `patch:`, once the HACS and hassfest checks pass. The
release workflow reads commit messages, not the pull request title, so put the prefix on the commit message
(for a squash merge, the commit title) as well as the PR title. Anything else releases nothing.

The workflow writes the new version into `manifest.json` and the card's `PM_VERSION`, tags `vX.Y.Z` and
publishes the GitHub Release. Don't bump those by hand.
