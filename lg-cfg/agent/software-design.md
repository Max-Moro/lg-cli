# Design and Architecture Principles

## The "High Cohesion Low Coupling" Principle

The principle of high cohesion and low coupling is the primary and most important when building the logic of a software product. We try to mentally visualize the picture:
- operators, functions and methods — are a set of points
- files (modules) and packages — are large circles (sets) grouping points
- method and function calls, imports (dependencies) — are lines connecting points and sets

Having visualized this picture, it's necessary to structure the logic so that the resulting codebase looks like a collection of very dense and well-cohesive point clusters that have very few external connections (dependencies) with neighboring, equally dense clusters. Many lines inside sets, rare lines between sets.

Adhering to this principle allows you to properly organize logic into classes and files, in turn group files into packages, and build packages into larger hierarchies (package modules).

The "high cohesion low coupling" principle is closely related to timely detection and prevention of the "god class" or "god module" (file) antipattern, which has bloated responsibilities and therefore low cohesion but possibly high coupling. Certain synthetic metrics can be identified: the module changes "for any reason", frequent merge conflicts, high fan-in/fan-out. The reverse is also true. Sometimes after refactoring you can find degenerate modules consisting of only one function — these are candidates for moving to another, larger module.

High cohesion is closely related to the SRP principle (from SOLID). By adhering to one, we usually immediately adhere to the other.

Low coupling can be achieved not only by separating modules, but also by introducing additional interface abstractions. Here we find a direct connection between the "Interface Segregation" and "Dependency Inversion" principles (from SOLID). Clients should not depend on interfaces they don't use. High-level modules should not depend on low-level modules; both should depend on abstractions.

## The DRY Principle

This is the second most important principle that must be followed when developing the codebase.

When working on a new feature, there's always a temptation to act straightforwardly:
- I'll write by analogy;
- found a good example, do it like there;
- I'll copy this code section and adjust it to my needs;
  Such actions immediately create technical debt — violation of the DRY principle.

Instead, it's necessary to immediately assess how best to unify and reuse the common logic section:
- extracting a common function or method;
- highlighting a common parent class;
- using any other patterns in complex situations: decoration, proxying, callback functions, and so on;

For DRY, the "rule of three" is often additionally specified. It's better not to follow it straightforwardly but to assess comprehensively. Even two times duplicated 100 lines of identical logic is quite bad. But duplicating 5 times 3 lines each is fine. These are not strict heuristics, you always need to think with your own head.

## The Principle of Separation by Universality Levels

When working on the current task, it's often discovered that some small utility or simple tool is missing. There's a temptation to quickly implement it and place it next to the business logic. But we forget that this thing is universal and may be useful in the future in other sections.

It's necessary to immediately separate logic by universality levels:
- system and application layers;
- universal utilities and final business logic;
- abstract frameworks and special cases;

Such an approach promotes better prospects for code reuse.

There are more specific named approaches that adhere to this principle: ports-and-adapters/hexagonal architecture. But we're not now going into branded frameworks, but trying to formulate more universal principles.

## The Principle of Orthogonal Development

It's necessary to try to build such a system architecture that it can be improved and developed in different directions. And do this quite independently — with minimal merge conflicts. In a well-designed codebase, business features should be added locally: in one module or package. Smeared addition of functionality across dozens of files is avoided.

If incoming new requirements don't allow convenient (localized) integration into the current codebase, this is a sure sign of an unsuitable structure. Perhaps it's worth delaying business logic development and thinking about architecture rework. So as not to accumulate technical debts in the future.

Let's give an example. A file (module) with common application constants seems, on one hand, to be a good idea — it frees the code from magic values. On the other hand, it strongly violates the principle of orthogonal development — this module will change constantly, as a result of any changes in logic. A more correct approach is "feature-scoped settings".

## Which Generally Accepted Principles We Consciously Violate

Well, that was a clickbait heading — more precisely, we don't always follow them mindlessly.

"Compatibility: don't break public APIs without versioning/migrations". Yes, it would seem like a good thing, but adhering to it leads to dirty code. You need to assess the situation, what exactly we're doing. If we're developing a public library or public WEB service — that's one situation. If our code is all internal — that's a completely different situation, in which it's more beneficial to do fully complete refactorings than to maintain backward compatibility.

"KISS & YAGNI". These are not bad principles. But they're too simple, they lack clear criteria. Usually an AI agent doesn't know in which direction the system requirements will develop further. For an AI agent, the analyst is the person working with it. For this reason, it's better to consult with the user and explicitly ask whether this or that refactoring is needed, or whether it will be overengineering.

## Being a Living Developer

This is no longer even a principle of software design and architecture, but rather a general behavioral recommendation. During iterative development, new requirements, requests for new functionality, and even initiatives to create new large functional blocks constantly arrive.

But you shouldn't rush and like a robot, immediately start specifically and straightforwardly solving the assigned task. It's necessary to act like a living developer. First you need to assess whether the current architecture is ready to accept a new batch of necessary changes? Perhaps before implementing business features, it's worth doing a number of preparatory refactorings to adhere to all the above principles.

There may also be a reverse situation. Already after implementing new requirements, we may notice emerging problems and bad-smelling code. Then it's worth immediately doing an improving refactoring, so as not to accumulate technical debts.

A living developer is also characterized by a pragmatic approach. And even to some extent useful laziness. All refactorings and improvements are done not for the holy purpose of achieving perfect clean architecture. They understand that systematic improvements will help them work more easily with the codebase in the future. But it's important not to overdo it. Application of any pattern or principle can lead to overengineering. If the requested business feature is implemented in just 10 lines, and improving the architecture will require 500 lines of new code, then of course, this is questionable refactoring.

## Consulting with a Living User

We understand that with an AI-Driven approach with a sufficiently deep level of automation and independence, development is conducted by an AI agent. It can try to be a "living" performer and try to adhere to all the above principles, but of course, there are complex and ambiguous situations. You shouldn't ignore the possibility to stop development at any moment and simply consult with a really living user in dialogue. Such joint discussion will significantly reduce the probability of negative review of the resulting code. Joint timely planning is better than separate tasks for architecture rework.
