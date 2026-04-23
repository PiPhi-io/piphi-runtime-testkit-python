# Versioning and Compatibility

## Semver policy

`piphi-runtime-testkit-python` follows semantic versioning.

- `MAJOR`: breaking changes to public imports, fixture names, assertion behavior, or documented testing contracts
- `MINOR`: backward-compatible helper additions, new fixtures, and additive mock/assertion capabilities
- `PATCH`: bug fixes, docs improvements, and internal changes that do not alter the public testkit surface

## Pre-1.0 guidance

Until `1.0.0`, the testkit is still stabilizing. We still aim to avoid unnecessary
breakage, but fixture behavior and helper APIs may be refined when that
meaningfully improves the developer experience.

Guidance during `0.x`:

- prefer additive changes in `MINOR` releases
- keep breaking changes grouped and documented clearly
- provide upgrade notes when fixture names, helper signatures, or captured-request behavior change

## Runtime kit compatibility

The testkit is designed to help developers test PiPhi runtimes, not replace the
runtime kit itself.

Compatibility expectations:

- additive runtime-kit features should not break existing testkit consumers
- when examples or fixtures start relying on newer runtime-kit behavior, the testkit should document the minimum expected runtime-kit version
- end-to-end example tests should be kept aligned with the currently supported runtime-kit API

## Upgrade notes

When publishing a release:

1. update `CHANGELOG.md`
2. note any fixture, helper, or assertion behavior changes
3. call out any minimum runtime-kit expectations that changed
4. include migration examples when public fixture names or helper signatures changed
5. prefer the `Release Testkit Package` workflow in `.github/workflows/release-pypi.yml`
6. choose the correct semantic bump: `patch`, `minor`, `major`, `prepatch`, `preminor`, `premajor`, `prerelease`, `release`, or `custom`
7. publish to `testpypi` first when you want a rehearsal or prerelease validation
8. publish to `pypi` for the real release once the package is ready

## Trusted publishing setup

The automated release workflow uses PyPI Trusted Publishing instead of storing a
long-lived API token in GitHub.

Before the first automated release:

1. configure a Trusted Publisher on TestPyPI for repository `PiPhi-io/piphi-runtime-testkit-python`
2. set the workflow path to `.github/workflows/release-pypi.yml`
3. set the environment name to `testpypi`
4. configure a matching Trusted Publisher on PyPI with environment `pypi`
5. if the package does not exist yet, create a pending publisher so the first publish can create the project

Manual fallback remains available:

1. run `pdm build`
2. run `pdm run twine check dist/*`
3. upload with `pdm run twine upload dist/*`
