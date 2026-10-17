# WebCheck Report — Development Roadmap

## Project Vision

Build WebCheck Report from scratch into a reliable web diagnostics tool that solves a real problem, develops strong engineering skills, and has the potential to become a sustainable software product.

The development strategy is to build a small, functional product first, improve its correctness and security, and validate demand before investing in larger features.

## Current Status

**Stage:** CLI prototype implemented.

**Latest verified test result:** 21 tests passing.

### Completed

- [x] Initialized a standalone Git repository.
- [x] Created a dedicated Python virtual environment.
- [x] Established a modular project structure.
- [x] Implemented HTTP/HTTPS URL validation.
- [x] Added hostname resolution and non-public IP address checks.
- [x] Implemented HTTP GET requests.
- [x] Captured HTTP status codes, response headers, and elapsed time.
- [x] Added timeout and network-error handling.
- [x] Implemented redirect reporting without automatic redirect following.
- [x] Implemented timestamped JSON report generation.
- [x] Added configurable report output paths.
- [x] Implemented CLI exit codes.
- [x] Added automated tests for URL validation, HTTP handling, network safety, report generation, and CLI behavior.
- [x] Verified that the full suite passes: 21 tests.
- [x] Configured Git ignore rules for the virtual environment, Python caches, local environment files, and generated reports.

## Phase 1 — Stabilize the Foundation

**Goal:** Make the current CLI predictable, maintainable, and easy to use.

- [x] Build the initial CLI workflow.
- [x] Generate and save JSON reports.
- [x] Test important success and failure cases.
- [x] Add initial network safety checks.
- [x] Review and finalize the README and roadmap.
- [x] Review the staged changes and create a clean Git commit.
- [x] Push the verified changes to the remote repository.
- [x] Verify that the repository is clean after pushing.

**Completion criteria:** The documented commands work, tests pass, and the source code and tests are safely committed to version control.

## Phase 2 — Harden Network Safety

**Goal:** Reduce the risk of the tool connecting to unintended or dangerous destinations.

- [ ] Study DNS resolution, address selection, and connection establishment in Python.
- [ ] Understand the DNS-rebinding and time-of-check/time-of-use weakness in the current design.
- [ ] Design connection-time destination enforcement.
- [ ] Prevent access to loopback, private, link-local, reserved, and other prohibited destinations.
- [ ] Consider IPv4, IPv6, and mixed DNS responses.
- [ ] Preserve TLS certificate and hostname verification when making HTTPS requests.
- [ ] Review redirect behavior and ensure future redirect support cannot bypass destination restrictions.
- [ ] Add regression tests for security-sensitive cases.
- [ ] Evaluate whether enforced network egress restrictions are needed.
- [ ] Document remaining limitations.

**Completion criteria:** The security model is explicit, its key guarantees are tested, and remaining risks are clearly documented.

**Important:** This phase must be completed before treating the tool as suitable for untrusted target URLs or production SSRF-sensitive environments.

## Phase 3 — Improve Reliability and Usability

**Goal:** Make the CLI more useful for real diagnostic work.

- [ ] Review error messages for clarity and consistency.
- [ ] Separate URL validation, network policy, HTTP execution, reporting, and CLI responsibilities cleanly.
- [ ] Review timeout handling and elapsed-time measurements.
- [ ] Define and test consistent behavior for HTTP errors, redirects, and connection failures.
- [ ] Make JSON output predictable and easy for other programs to consume.
- [ ] Add tests for report-writing failures and other uncovered edge cases.
- [ ] Review command-line help and invalid-argument behavior.
- [ ] Add type annotations and improve code documentation where useful.
- [ ] Run the full test suite after each meaningful change.

**Completion criteria:** Users can understand the results, failures are handled consistently, and future changes can be made without breaking existing behavior.

## Phase 4 — Validate the Problem and Market

**Goal:** Establish whether WebCheck Report solves a problem people care about enough to use or pay for.

- [ ] Identify potential users, such as developers, small web agencies, and website operators.
- [ ] Speak with at least five potential users.
- [ ] Ask how they currently check website availability and diagnose HTTP failures.
- [ ] Identify repeated frustrations with existing tools and workflows.
- [ ] Demonstrate the current CLI to potential users.
- [ ] Record feedback and rank the most common problems.
- [ ] Test whether users would pay for a solution to a specific problem.
- [ ] Choose the next features based on evidence rather than assumptions.

**Completion criteria:** A specific target user and a validated problem are identified, with evidence guiding the product's next direction.

## Phase 5 — Expand the CLI Based on Evidence

**Goal:** Add only features that materially improve the product for its intended users.

Potential candidates:

- [ ] Multiple-target checks.
- [ ] Additional response and timing diagnostics.
- [ ] More structured error categories.
- [ ] Report comparison between runs.
- [ ] Configurable checks and output formats.
- [ ] Batch execution with sensible limits.
- [ ] Better summaries for developers and operators.

These features are candidates, not commitments. Their priority depends on feedback, security requirements, and implementation cost.

**Completion criteria:** The additional features solve demonstrated user problems without compromising reliability or safety.

## Phase 6 — Distribution and Productization

**Goal:** Make the tool easy to install, use, and maintain.

Potential work:

- [ ] Define a stable public CLI interface.
- [ ] Package the project for straightforward installation.
- [ ] Add usage examples and troubleshooting documentation.
- [ ] Add continuous integration to run tests automatically.
- [ ] Select an appropriate open-source or commercial license.
- [ ] Establish versioning and release practices.
- [ ] Decide how bugs and feature requests will be tracked.
- [ ] Explore a paid offering only if users demonstrate willingness to pay.

A dashboard, hosted service, accounts, database, subscriptions, and AI features are deliberately deferred until the core product and market demand justify them.

## Phase 7 — Long-Term Opportunities

Possible future directions, depending on validated demand:

- Historical diagnostics and trend analysis.
- Scheduled monitoring and alerts.
- Team workflows.
- A web interface.
- Integrations with developer tools.
- A hosted service or other commercial distribution model.

Each direction requires a separate assessment of user value, cost, operational complexity, and security.

## Development Rules

1. Understand the problem before writing the feature.
2. Keep changes small enough to test and review.
3. Add regression tests for bugs and security issues.
4. Never claim a security guarantee that the implementation has not established.
5. Keep secrets, virtual environments, and generated reports out of Git.
6. Use authorized targets and avoid unnecessary network traffic.
7. Prefer useful, reliable functionality over feature count.
8. Validate demand before building infrastructure.
9. Protect sleep and sustainability; consistent progress beats burnout.

## Immediate Next Actions

1. Finalize the documentation.
2. Review and commit the current implementation.
3. Push the commit and verify the remote repository.
4. Begin Phase 2 by studying and addressing DNS-rebinding and connection-time destination enforcement.
5. Re-run the complete test suite and add regression tests as the implementation improves.
