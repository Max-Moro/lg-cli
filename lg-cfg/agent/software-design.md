# Design and Architecture Principles

## High Cohesion, Low Coupling

High cohesion and low coupling is the primary and most fundamental principle when structuring the logic of a software system. A useful mental model is the following:

* operators, functions, and methods are points
* files (modules) and packages are large circles (sets) that group points
* method calls, function calls, and imports (dependencies) are lines connecting points and sets

With this mental picture in mind, the goal is to structure logic so that the codebase forms tightly knit, highly cohesive clusters with very few external connections (dependencies) to neighboring clusters. Many lines inside a cluster, very few lines between clusters.

Following this principle helps organize logic within classes and modules, group modules into packages, and compose packages into larger hierarchies and subsystems.

This principle is also tightly connected to detecting and preventing the “God Class” / “God Module” anti-pattern: components with bloated responsibility, low cohesion, and often high coupling. Several synthetic indicators help reveal such problems: the module “changes for any reason,” frequent merge conflicts, high fan-in/fan-out. The reverse situation is also possible: after refactoring you may discover degenerate modules containing only a single function — these are candidates for merging into a larger, more meaningful module.

High cohesion is strongly related to the SRP principle (from SOLID). In practice, following one usually means following the other.

Low coupling can be achieved not only by splitting modules but also by introducing proper interface abstractions. This reveals the direct connection to the SOLID principles of Interface Segregation and Dependency Inversion. Clients should not depend on interfaces they do not use. High-level modules should not depend on low-level modules; both should depend on abstractions.

## DRY Principle

This is the second most important principle to follow when evolving a codebase.

When implementing a new feature, there is always a temptation to take the straightforward path:

* “I'll copy the existing code and adjust it.”
* “I found a similar example; I'll do it the same way.”
* “I'll just duplicate this block and modify it for my case.”

These actions immediately create technical debt — a direct violation of DRY.

Instead, you should evaluate how to unify and reuse the common logic:

* extract a shared function or method
* introduce a common base class
* apply other patterns when necessary: decorators, proxies, callbacks, etc.

The DRY principle is often accompanied by the “Rule of Three.” But it’s better treated as a heuristic, not a rigid law. Duplicating **100 lines** of identical logic twice is already bad. Duplicating **3 lines** five times is usually acceptable. Use judgment rather than fixed numbers.

## Separation by Levels of Universality

When implementing a task, you may notice the need for a small utility or helper tool. There is a temptation to quickly implement it and place it next to business logic. But in many cases, such a utility is universal and will be needed elsewhere in the future.

You should separate logic by levels of universality from the start:

* system vs application layers
* universal utilities vs domain/business logic
* abstract frameworks vs concrete special cases

This promotes better reuse and a cleaner long-term architecture.

There are known approaches that follow this principle — e.g., ports-and-adapters / hexagonal architecture — but our goal here is to formulate broader, technology-agnostic principles rather than focus on branded frameworks.

## Principle of Orthogonal Development

The architecture of the system should allow development and improvement in multiple directions independently, with minimal merge conflicts. In a well-structured codebase, new business features should be added locally, typically within a single module or package. Avoid functionality that must be scattered across dozens of files.

If new requirements cannot be integrated cleanly and locally into the existing structure, that is a clear sign that the architecture is not well-suited for future growth. In such cases, it may be worth pausing feature development and rethinking the architecture to avoid accumulating technical debt.

For example, a module containing all application constants may seem useful because it eliminates magic values. But it strongly violates orthogonal development: this module will change constantly as any part of the system evolves. A better approach is **feature-scoped settings**, where each module owns its own configuration.

## Commonly Accepted Principles We Sometimes Break

This title is slightly provocative — the point is that we do not follow certain principles blindly.

**Backward Compatibility:** “Don’t break public APIs without versioning or migrations.”
A good rule — **when you actually develop a public API**. But blindly following it in an internal codebase leads to dirty code. In internal systems, complete refactorings are often more beneficial than maintaining backward compatibility.

**KISS & YAGNI.**
These are good principles, but they are vague and lack operational criteria. An AI agent typically does not know how the system will evolve next. The analyst is the human interacting with the agent. Therefore, it is better for the AI agent to ask the user whether a given refactoring is needed or would be unnecessary complexity.

## Being a Living Developer

This is not strictly a design principle — it is a behavioral guideline.

In iterative development, new requirements, improvements, and even proposals for large functional blocks appear constantly. A “robotic” reaction — immediately implementing the task as described — is not ideal. The developer must first assess whether the current architecture can accept the upcoming changes cleanly. Sometimes preliminary refactorings are needed to maintain the principles described above.

The opposite situation is also common: after implementing new requirements, new issues or code smells become visible. In such cases, it makes sense to perform improving refactorings immediately, instead of accumulating technical debt.

A “living” developer is pragmatic — sometimes even productively lazy. Refactorings are performed not for the sacred goal of achieving perfect architecture, but to make future development easier. But balance is important: any principle or pattern can lead to over-engineering. If a requested feature takes 10 lines to implement, but making the architecture “ideal” takes 500 lines, that refactoring is questionable.

## Consulting with a Living User

In an AI-Driven workflow, much of the development is performed by an AI agent with a significant degree of autonomy. The agent may try to behave like a “living developer” and follow these principles — but complex or ambiguous situations will inevitably arise.

The agent should not hesitate to pause development and consult a real human user. Such interaction reduces the risk of producing code that will later require negative review or major rework. Collaborative, timely planning is always better than isolated architectural refactoring tasks.