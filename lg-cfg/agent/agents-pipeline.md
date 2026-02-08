# Work Pipeline in This Project

## Core Working Principles

### Delegation Through Agents

**CRITICALLY IMPORTANT**: You do almost nothing yourself through Edit/Write tools. All code work happens through specialized subagents. This saves tokens and increases efficiency.

### Flexibility Instead of Rigid Iterations

You decide which chain of agents to call based on:
- Task complexity
- Scope of changes
- Criticality of modules
- Results from previous agents

### Execution Sequence

All agents are called strictly sequentially. Never run agents in parallel. The order depends on the specific situation.

### Context Management

**Listing Generator** prepared the main context for the task, but there are legitimate cases for reading additional files:

✅ **ALLOWED to use Read/Grep**:
- Read files from @test-runner errors (if they're not in the initial context)
- Read files modified by @code-integrator (to verify changes were applied)
- Grep for patterns when dealing with similar errors from @test-runner
- Read conftest.py/fixtures recommended by @test-advisor

❌ **NOT ALLOWED**:
- General codebase exploration without a specific trigger
- Reading files for architectural understanding (should be in initial context)
- Searching "how it works elsewhere" without specific reason
- Studying test infrastructure directly (use @test-advisor)

## Available Agents and Their Roles

### @code-integrator
**Role**: Integrate any code into the codebase
- Accepts detailed instructions with patches
- Makes changes to production code
- Makes changes to tests
- Creates new files
- Returns list of modified files

**When to call**:
- Changes in 3+ code locations
- Creating new modules or tests
- Mass test fixes
- Refactoring with API changes

<!-- lg:if tag:code-inspector -->
### @code-inspector
**Role**: Code quality checking through Qodana
- Runs static analysis
- Automatically fixes found issues
- May require re-running tests after fixes

**When to call**:
- After each code integration
- After fixing tests
- Before final report to user
<!-- lg:endif -->

### @test-runner
**Role**: Running tests and interpreting results
- Runs pytest in different modes
- Groups similar errors
- Returns exact coordinates of failed tests

**Testing modes (make informed choice)**:
- `single` - specific test
- `module` - test file
- `specific` - specific set of test files
- `package` - test directory
- `all` - full run (if critical changes)

### @test-advisor
**Role**: Test infrastructure consultation
- Where to create new test
- Which fixtures to use
- Find similar tests for example
- Recommend testing scope

**When to call** (by consultation type):
- `recommend_scope`: BEFORE first test run to predict impact of changes.
- `find_location`: When you want to create a new test or test suite to understand where best to place it. And also, whether new tests are needed or if it's easier to adjust existing ones (add `find_similar`) or adjust fixtures (add `find_fixtures`).
- `find_similar`: Even if you need to develop new tests but want to understand what structure they usually have, you can ask to find similar tests.
- `find_fixtures`: If you don't know which fixtures to use and whether new ones need to be developed, you can ask about this.
- `explain_infra`: To understand test infrastructure (fixtures, conftest, structure, utilities) to avoid repeating utility code. Agent helps follow DRY principle.

**DON'T call for**:
- Analyzing why production code caused test error (not its task)
- Choosing scope AFTER @test-runner (use test-runner results directly)
- Understanding business logic in test code (this is part of production analysis)

## Typical Work Scenarios

These are just recommended examples. Don't take them as rigid rules. You can decide yourself how to optimally call agents.

### Scenario 1: Developing New Feature

<!-- lg:if tag:code-inspector -->
```
1. Plan architecture and design
2. Prepare instructions for @code-integrator
3. @code-integrator → code integration
4. @test-advisor (advice_type: find_location) → where to create tests
5. Prepare tests in instructions
6. @code-integrator → add tests
7. @test-runner (mode: specific/module) → check new tests
8. [If tests failed] → analyze and fix through @code-integrator
9. @code-inspector → quality check
10. [If many fixes] → @test-runner again
11. Report to user
```
<!-- lg:else -->
```
1. Plan architecture and design
2. Prepare instructions for @code-integrator
3. @code-integrator → code integration
4. @test-advisor (advice_type: find_location) → where to create tests
5. Prepare tests in instructions
6. @code-integrator → add tests
7. @test-runner (mode: specific/module) → check new tests
8. [If tests failed] → analyze and fix through @code-integrator
9. Report to user
```
<!-- lg:endif -->

### Scenario 2: Bug Fixes

<!-- lg:if tag:code-inspector -->
```
1. Analyze problem. Initial @test-runner run if needed.
2. [If need to understand tests] → @test-advisor (advice_type: explain_infra)
3. Prepare fixes
4. Apply fix (through @code-integrator or Edit, depending on scope)
5. @test-runner (mode: specific/package for affected subsystems) → check fix
6. @code-inspector → code quality
7. [Optional] @test-runner (mode: all) → final check before commit
8. Report to user
```
<!-- lg:else -->
```
1. Analyze problem. Initial @test-runner run if needed.
2. [If need to understand tests] → @test-advisor (advice_type: explain_infra)
3. Prepare fixes
4. Apply fix (through @code-integrator or Edit, depending on scope)
5. @test-runner (mode: specific/package for affected subsystems) → check fix
6. [Optional] @test-runner (mode: all) → final check before commit
7. Report to user
```
<!-- lg:endif -->

**Important for step 5**:
- Use results from first @test-runner run to determine scope
- If bug affected 1 function → run `specific` for tests of that subsystem
- DON'T use `all` immediately after fix — it's excessive

### Scenario 3: Mass Test Errors (>10)

<!-- lg:if tag:code-inspector -->
```
1. @test-runner → get full error list
2. Analyze and group errors
3. Prioritize: critical → mass → specific
4. Prepare instructions with grouped fixes
5. @code-integrator → mass fixes
6. @test-runner → check fixes
7. [Repeat 4-6 for next group]
8. @code-inspector → final check
9. Report with results
```
<!-- lg:else -->
```
1. @test-runner → get full error list
2. Analyze and group errors
3. Prioritize: critical → mass → specific
4. Prepare instructions with grouped fixes
5. @code-integrator → mass fixes
6. @test-runner → check fixes
7. [Repeat 4-6 for next group]
8. Report with results
```
<!-- lg:endif -->

### Scenario 4: Refactoring

<!-- lg:if tag:code-inspector -->
```
1. Plan changes
2. @test-advisor (advice_type: recommend_scope) → which tests are affected
3. @code-integrator → code refactoring
4. @test-runner → check nothing broke
5. [If need to update tests] → @code-integrator
6. @code-inspector → quality check
7. Report to user
```
<!-- lg:else -->
```
1. Plan changes
2. @test-advisor (advice_type: recommend_scope) → which tests are affected
3. @code-integrator → code refactoring
4. @test-runner → check nothing broke
5. [If need to update tests] → @code-integrator
6. Report to user
```
<!-- lg:endif -->

## Decision-Making Rules

### When to Use @code-integrator vs Direct Editing

**Use @code-integrator when**:
- Changes in 3+ code locations (would require 3+ Edit calls)
- Creating 3+ new files (would require 3+ Write calls)
- Changing public APIs
- Mass uniform edits
- Writing/fixing tests

**Can do yourself through Edit/Write when**:
- Any fixes that are simpler to do yourself (would require no more than 2 editing tool calls total)

### Choosing Test Mode

**IMPORTANT**: Full run (`all`) takes significant time. Always choose minimally sufficient scope.

#### Scope Selection Algorithm

**First run after code changes**:

1. **Can you confidently predict affected subsystems?**
   - **NO** → Call @test-advisor (advice_type: recommend_scope) → then @test-runner with recommended scope
   - **YES** → Call @test-runner directly with likely scope:
     * 1 file changed → `module` for that file's tests
     * 2-4 files in one subsystem → `package` for subsystem
     * changes in core/base classes → `all`

**Subsequent runs after fixes**:

1. **ALWAYS use results from previous @test-runner**
2. **DON'T call @test-advisor again** to determine scope
3. **Determine scope by failed tests from previous run**:
   - 1-5 tests from 1-2 directories → `specific` with those paths
   - 6-15 tests from 3-5 directories → `specific` with those paths
   - >15 tests OR >5 directories → `package` or `all`

**Full run (`all`) only when**:
- Changes in base classes/interfaces used everywhere
- Changes in shared types
- Before final commit of critical changes
- After mass fixes for final verification

**Example of correct approach**:
```
Task: Fix bug in lg/template/common.py
Failed 15 tests from: tests/template/, tests/common_placeholders/, tests/md_placeholders/

✅ Correct:
@test-runner (mode: specific, test_path: ["tests/template", "tests/common_placeholders", "tests/md_placeholders"])

❌ Wrong:
@test-runner (mode: all)  # Excessive! Takes 10x more time
```

### When to Create New Tests

- **Always** when adding new features
- **On request** from user
- **Recommend** for critical changes
- **Discuss separately** for large functional blocks

### Processing Agent Results

**@code-integrator**:
- Got file list → use for inspector and test-runner
- Not all changes applied → stop, inform user

**@test-runner**:
- 0 errors → continue pipeline
- 1-10 errors → fix through @code-integrator
- >10 errors → group and fix in batches
- Unclear errors → escalate to user

<!-- lg:if tag:code-inspector -->
**@code-inspector**:
- Fixed >20 issues → run tests again
- Unfixed issues remain → assess criticality, possibly escalate
<!-- lg:endif -->

**@test-advisor**:
- Got recommendations → use in instructions for @code-integrator
- Suggested adapting existing tests → follow recommendation

## Forming Instructions for Agents

### For @code-integrator

**If integrating production code**:
- brief business requirements;
- required architecture changes (if needed);
- main and optimal integration points for new functionality;
- new code listings as fenced inserts;
- patch descriptions (they can be informal but sufficient for another AI model to understand);
- **when changing public APIs** - explicit indication of ALL files using these functions/types;
- and so on;

**If integrating test code**:
- Description of new tests, if needed.
- Description of fixes to existing tests, if needed. Can be in generalized form.

**IMPORTANT**: Instructions should be written once when launching the @code-integrator agent tool. Never duplicate this instruction in dialogue with user.

### For @test-runner

1. **task_description** - brief description of current task
2. **test_mode** - testing mode (see table below)
3. **test_path** - path to test/module/package (see table below)

#### Table of test_mode and test_path Parameters

| test_mode | test_path | Format | Example |
|-----------|-----------|--------|---------|
| `single` | **Required** | String: exact test path | `"tests/foo/test_bar.py::test_func"` |
| `module` | **Required** | String: path to test file | `"tests/foo/test_bar.py"` |
| `specific` | **Required** | **List of strings**: directories or files | `["tests/foo", "tests/bar/test_baz.py"]` |
| `package` | **Required** | String: path to directory | `"tests/template"` |
| `all` | Not used | - | (runs all tests) |

**Wrong**: Don't ask this agent for advice on fixing tests. It's not configured for production code analysis. It simply provides convenient report on test run results from `tests/`.

### For @test-advisor

1. **task_description** - brief description of current task
2. **advice_type** - type of consultation needed:
   - `find_location` - where to create new test
   - `find_similar` - find similar existing tests
   - `find_fixtures` - find suitable fixtures
   - `recommend_scope` - which tests to run after changes
   - `explain_infra` - explain test infrastructure elements
3. **changed_files** (optional) - list of modified files
4. **test_requirement** (optional) - what needs to be tested

<!-- lg:if tag:code-inspector -->
### For @code-inspector

- **Task**: Brief task description (1 sentence, what work is currently being done)
- **Recent changes**: List of modified files (from @code-integrator report)
- **Request**: Request to run inspection
<!-- lg:endif -->

## TodoWrite and Reporting

### Using TodoWrite

Use TodoWrite for:
- Planning complex tasks (3+ steps)
- Tracking progress
- Organizing work with multiple bugs

Don't use for:
- Simple one-step fixes
- Agent calls (they know what to do)

## Important Notes

1. **Agent context isolation**: Each call is a new session. Pass full information.
2. **Python specifics**: No compilation, but runtime errors exist. Tests are main verification method.
3. **Testing strategy**: Tests take long to run, so informed choice of appropriate scope is needed.
4. **Escalation**: When in doubt, better to stop and ask user.
5. **Documentation**: Don't create documentation on your own initiative. Only on explicit request.

## Control Checklist

Before completing task work, check:
- [ ] Code integrated through @code-integrator
- [ ] Tests run and pass
<!-- lg:if tag:code-inspector -->
- [ ] Qodana check performed
<!-- lg:endif -->
- [ ] TodoWrite updated
- [ ] Report sent to user in dialogue

Remember: you are a coordinator managing specialized agents. Delegate work to them, and focus yourself on planning and decision-making.