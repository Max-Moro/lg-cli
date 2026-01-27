# Maintenance: qodana.recommended.with-tests.yaml

Standalone inspection profile equivalent to `qodana.recommended`, but with test code included in the analysis scope.

## Why standalone (not baseProfile)

Qodana merges `ignore` lists additively when using `baseProfile` inheritance. This makes it impossible to *remove* the test exclusion patterns from the parent. Therefore, this profile is a full replica of `qodana.recommended` + `qodana.recommended.all` with test exclusions removed.

## What was changed

The upstream `qodana.recommended` profile ignores test code via three patterns in the `group: ALL` ignore list:

```yaml
- "tests/**"        # glob: tests directory
- "scope#test:*..*" # IntelliJ test source scope
- "**.test.ts"      # glob: TypeScript test files
```

Our profile contains all the same group definitions and inspection settings, but without these three patterns.

## When to update

Check the profile for compatibility when either of these happens:

1. **Qodana CLI version update** (`qodana --version` to check current; profile created at 2025.3.1)
2. **Upstream profile change** in [JetBrains/qodana-profiles](https://github.com/JetBrains/qodana-profiles)

## How to update

1. Open both upstream source files:
   - https://github.com/JetBrains/qodana-profiles/blob/master/.idea/inspectionProfiles/qodana.recommended.yaml
   - https://github.com/JetBrains/qodana-profiles/blob/master/.idea/inspectionProfiles/qodana.recommended.all.yaml

2. Diff each section against our `qodana.recommended.with-tests.yaml`:
   - **groups**: compare group definitions (groupId, inspections, categories)
   - **inspections**: compare inspection settings (enabled, severity, options)
   - **ignore list**: compare the `group: ALL` ignore patterns

3. Apply upstream additions/removals to our profile.
   Do NOT add back the three test-exclusion patterns listed above.

4. Run inspection and verify:
   ```bash
   source .claude/skills/qodana-inspect/scripts/run-qodana.sh --linter qodana-python-community
   ```

## Verification

After any profile change, confirm test files appear in analysis output:

```bash
# Run Qodana, then check SARIF for test file paths
jq -r '
  [.runs[0].results[].locations[0].physicalLocation.artifactLocation.uri]
  | unique
  | map(select(startswith("tests/")))
  | .[]
' .qodana/results/qodana.sarif.json
```

If this outputs test file paths, the profile is working correctly. If Qodana reports 0 problems and test code is known to have issues, the profile override is not being applied.
