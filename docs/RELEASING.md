# Releasing CounterProof

CounterProof publishes Python distributions through PyPI Trusted Publishing. The release workflow uses GitHub OIDC and does not store a long-lived PyPI API token.

## One-time setup

Before the first release:

1. In GitHub, create an environment named `pypi`.
2. In PyPI account settings, add a **pending GitHub publisher** with:
   - PyPI project name: `counterproof`
   - Owner: `hippoley`
   - Repository: `CounterProof`
   - Workflow filename: `release.yml`
   - Environment: `pypi`
3. Keep the GitHub environment restricted to maintainers you trust. Requiring approval for the environment is recommended when available.

A pending publisher does not reserve the package name until the first successful publish, so do not treat setup alone as ownership of `counterproof`.

## Release procedure

1. Update `project.version` in `pyproject.toml`.
2. Merge all intended release changes to `main`.
3. Confirm main CI is green.
4. Create a GitHub Release whose tag is exactly `v<project.version>`, for example `v0.2.0`.
5. Publishing the GitHub Release triggers `.github/workflows/release.yml`.

The workflow refuses to publish if the release tag and `pyproject.toml` version disagree.

## What the workflow verifies

Before uploading anything, it:

- builds both source and wheel distributions;
- runs `twine check`;
- installs the built wheel into a clean virtual environment;
- verifies the installed `counterproof` CLI is present.

Only the publish job receives `id-token: write`, and that job is bound to the `pypi` GitHub environment.

## After publishing

Verify:

```bash
python -m pip install --upgrade counterproof
counterproof --help
counterproof doctor
```

Then update README installation examples from the GitHub URL to `pip install counterproof` only after the PyPI release is actually available.
