# Release Checklist (v1.0.0 Baseline)

## Pre-Release

- [ ] Ensure `pyproject.toml` version matches intended tag (currently `1.0.0`).
- [ ] Confirm `CHANGELOG.md` includes release notes for the target version.
- [ ] Run full validation:
  - [ ] `python scripts/lab_validate_all.py --python-runs 1000 --tms-runs 500 --tms-corpus 1500 --graph-runs 300 --graph-corpus 900 --agent-runs 180 --agent-reflection-frequency 2 --agent-seed-count 40 --report-output results/lab_validation_report.md`
- [ ] Confirm TypeScript and Java reports are current:
  - [ ] `typescript/results/lab_validation_report.md`
  - [ ] `java/results/lab_validation_report.md`
- [ ] Confirm canonical quickstart commands in `README.md` are unchanged.

## Packaging

- [ ] Build distributions:
  - [ ] `python -m build`
- [ ] Verify package metadata:
  - [ ] `python -m twine check dist/*`
- [ ] Optional test publish:
  - [ ] `python -m twine upload --repository testpypi dist/*`

## Tag and Release

- [ ] Create annotated tag:
  - [ ] `git tag -a v1.0.0 -m "ThoughtWrapper v1.0.0"`
- [ ] Push tag:
  - [ ] `git push origin v1.0.0`
- [ ] Confirm GitHub Actions release workflow succeeds:
  - [ ] `.github/workflows/release.yml`
- [ ] Confirm GitHub Release body reflects `CHANGELOG.md` `1.0.0` section.

## Post-Release

- [ ] Publish to PyPI:
  - [ ] `python -m twine upload dist/*`
- [ ] Verify install from PyPI:
  - [ ] `pip install thoughtwrapper==1.0.0`
- [ ] Smoke test imports:
  - [ ] `python -c "import thoughtwrapper; print(thoughtwrapper.__version__)"`
- [ ] Announce release and link artifacts:
  - [ ] `results/lab_validation_report.md`
  - [ ] benchmark JSON artifacts
