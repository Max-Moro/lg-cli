# Context Window Contents

The initial contents of your context window were prepared by **Listing Generator** — a software tool for assembling "dense" contexts from sources in the repository. This tool should already be configured to immediately provide you with all necessary data to complete the assigned task. This usually means you don't need to independently explore the codebase through reading and search tools: Read, Edit, Glob, Grep, and so on.
<!-- lg:if provider:com.anthropic.claude -->
If after initial analysis you understand that the context is insufficient for quality task completion:

**Criteria for insufficient context**:
- Missing key documentation for the subsystem from the task
- Can't see code of modules imported in task files
- Project architecture is unclear for making design decisions
- Context clearly prepared for a different functional block

**Actions with insufficient context**:
- Inform user about problem with **Listing Generator**
- DON'T start independent exploration through Read/Grep without grounds

**Legitimate exceptions** (see details in agents-pipeline.md, "Context Management" section):
- Files mentioned in errors from @test-runner or @code-inspector that are not yet in context from **Listing Generator**
- Verification of changes applied by @code-integrator
- Fixtures and conftest.py recommended by @test-advisor
- Grep for searching patterns in similar errors
<!-- lg:else -->
If after initial analysis you understand that you clearly lack data for quality task completion:

- not all useful project documentation is loaded in context;
- not all task-related program code is visible immediately (based on import analysis);
- project architecture is not clear overall;
- context prepared for a different functional block and sent to you by mistake;

, then in such a situation it's worth immediately stopping work on the task and informing the user about the problem with the **Listing Generator** tool.
<!-- lg:endif -->
