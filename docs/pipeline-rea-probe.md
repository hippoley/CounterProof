# Pipeline REA — read-only probe (experimental)

**What it does:** Inspect a local Jenkinsfile, GitLab CI file or GitHub Actions workflow to produce a small JSON inventory of stages/jobs, referenced credential names and possible inline secret assignments. **Never supply real secret values.**

This is the first narrow slice of a proposed pipeline-reconstruction product, **not** a production security scanner or a complete parser. It does not run arbitrary repositories or evaluate pipeline syntax.

## Try it

```bash
python tools/pipeline_rea.py Jenkinsfile
python -m unittest discover -s tools -p 'test_pipeline_rea.py' -v
```

To inspect a GitLab CI file:

```bash
python tools/pipeline_rea.py .gitlab-ci.yml
```

Output schema: `pipeline-rea.report.v0`. A finding marks a line and key name **only**; values are never returned. The heuristic intentionally sacrifices completeness and may misclassify values.

## Next acceptance gates

1. Replace regex extraction with trustworthy platform-aware parsing while avoiding execution of untrusted Groovy or YAML.
2. Model GitLab includes/Jenkins shared libraries/actions reuse without fetching private resources by default.
3. Create a no-upload browser UI with a sample pipeline and an evidence side panel.
4. Add malicious-input, redaction, large-file and cross-platform corpus tests.
5. Verify against at least two independent real pipelines and document false positives.

This probe is not the same as Agent REA or Physical REA; those products remain separate user experiences.
