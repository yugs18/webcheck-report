# WebCheck Report — Development Roadmap

## Project vision

Build a reliable, understandable web-diagnostics tool; use its development to strengthen practical Python, networking, HTTP, secure-programming, testing, and product-development skills; and validate demand before investing in larger features.

## Current status

**Stage:** CLI prototype with initial connection pinning implemented. Phase 2 hardening remains in progress.

**Latest verified automated test result for the uploaded source snapshot:** 18 tests passing. A separate local HTTP smoke test succeeded during review; a real external HTTPS handshake could not be confirmed because external DNS resolution failed in that environment.

### Implemented

- [x] Standalone modular Python project and CLI.
- [x] HTTP/HTTPS URL syntax validation.
- [x] DNS resolution and filtering to approved `is_global` IP-address candidates.
- [x] Direct TCP connection to a chosen approved `getaddrinfo()` socket address.
- [x] Custom HTTP and HTTPS connection classes that use the pinned socket for the request.
- [x] Default TLS client context and original hostname passed to TLS wrapping.
- [x] GET request, response status/header capture, elapsed-time metadata, and normalized errors.
- [x] Redirect reporting without automatically following redirects.
- [x] Timestamped JSON reports and configurable output paths.
- [x] CLI exit codes and unit tests for core behaviors.
- [x] Standard-library-only dependency policy.

## Phase 1 — Stabilize the foundation

**Goal:** Make the initial CLI workflow predictable and testable.

- [x] Build the basic CLI workflow.
- [x] Generate and save JSON reports.
- [x] Test important success and failure outcomes.
- [x] Add initial URL and destination checks.
- [x] Document installation, usage, tests, and security limitations.

**Completion criteria:** Documented commands work, test results are repeatable, and changes are committed to version control. Git commit/push state must be verified in the developer's actual repository; it cannot be inferred from this uploaded-file review.

## Phase 2 — Harden network safety

**Goal:** Make the destination policy explicit and ensure the actual TCP connection uses a validated address.

### Implemented so far

- [x] Resolve hostname candidates with `socket.getaddrinfo()`.
- [x] Filter non-global candidates and fail if none remain.
- [x] Connect directly to the selected approved socket address.
- [x] Use the pinned connection for the HTTP request rather than opening a separate `urllib` connection.
- [x] Keep redirects disabled.
- [x] Preserve the original hostname for HTTPS TLS identity with the default client SSL context.
- [x] Add unit tests for mixed DNS answers, all-prohibited answers, DNS errors, exact socket destination, request construction, redirect behavior, and the TLS hostname argument.

### Remaining work

- [ ] Add deterministic tests for connection failure across multiple approved candidates and socket cleanup.
- [ ] Add a local HTTPS integration test that verifies a trusted certificate/SAN and confirms rejection of an invalid certificate; never disable TLS verification to make a test pass.
- [ ] Expand IPv4 and IPv6 edge-case coverage, including loopback, private, link-local, reserved, IPv4-mapped IPv6, and unusual scoped addresses as applicable.
- [ ] Decide and test how internationalized/Unicode hostnames are supported or rejected, including correct Host authority formatting.
- [ ] Test that the configured timeout behavior is documented accurately and consider a total operation deadline; DNS resolution can exceed the socket timeout.
- [ ] Review `ipaddress.is_global` against the project's explicit destination policy and supported Python versions.
- [ ] Keep direct-connection and proxy behavior explicit; ensure no future transport feature can silently use an unvalidated target.
- [ ] Add regression tests for any discovered edge cases and document remaining limitations.
- [ ] Evaluate network egress restrictions as additional defense in depth.

**Completion criteria:** The destination policy is documented, the connection path is tested end to end where feasible, TLS verification remains enabled, retries and cleanup are covered, and remaining risks are clearly stated. Do not treat this phase as complete yet.

## Phase 3 — Reliability and usability

**Goal:** Make results predictable and easier to integrate into developer workflows.

- [ ] Review error messages for clarity and consistency.
- [ ] Review elapsed-time semantics and timeout behavior.
- [ ] Add tests for report-write failures and remaining CLI edge cases.
- [ ] Define stable JSON result fields and behavior for redirects and HTTP error statuses.
- [ ] Add type annotations and documentation where they improve clarity.
- [ ] Run the complete test suite after every meaningful change.

**Completion criteria:** Users can understand the results and failures, and changes can be made without breaking existing behavior.

## Phase 4 — Validate the problem and market

**Goal:** Establish whether the tool solves a problem people actually need solved.

- [ ] Identify likely users, such as developers, small web agencies, and website operators.
- [ ] Speak with at least five potential users.
- [ ] Learn how they currently diagnose website availability and HTTP failures.
- [ ] Demonstrate the CLI and record repeated pain points.
- [ ] Test willingness to pay for a specific solution instead of assuming demand.
- [ ] Prioritize next steps using feedback.

**Completion criteria:** A target user and problem are supported by evidence.

## Phase 5 — Expand the CLI based on evidence

Potential features; none are commitments until the core safety and user need justify them:

- [ ] Multiple-target checks with sensible concurrency limits.
- [ ] Additional response and timing diagnostics.
- [ ] Structured error categories.
- [ ] Comparisons between saved reports.
- [ ] Configurable checks and output formats.
- [ ] Batch execution and improved summaries.

## Phase 6 — Distribution and productization

**Goal:** Make the project easy to install, use, and maintain.

- [ ] Define a stable CLI interface.
- [ ] Package the project for straightforward installation.
- [ ] Add troubleshooting documentation.
- [ ] Add continuous integration to run tests automatically.
- [ ] Choose an appropriate open-source or commercial license.
- [ ] Establish versioning, release practices, and issue tracking.
- [ ] Explore a paid offering only if users demonstrate willingness to pay.

A dashboard, hosted service, accounts, database, subscription system, and AI features are deliberately deferred until evidence justifies the additional complexity.

## Phase 7 — Long-term opportunities

Possible directions, depending on validated demand:

- Historical diagnostics and trend analysis.
- Scheduled monitoring and alerts.
- Team workflows.
- A web interface.
- Developer-tool integrations.
- A hosted service or other commercial distribution model.

Each direction requires an independent assessment of user value, cost, operations, and security.

## Development rules

1. Understand the problem before building the feature.
2. Keep changes small enough to test and review.
3. Add regression tests for bugs and security issues.
4. Never claim a security guarantee the implementation has not established.
5. Keep secrets, virtual environments, and generated reports out of Git.
6. Use authorized targets and avoid unnecessary network traffic.
7. Prefer useful, reliable functionality over feature count.
8. Validate demand before building infrastructure.
9. Protect sleep and sustainability; consistent progress beats burnout.

## Immediate next actions

1. Replace the old README and roadmap with the current versions.
2. Add the standard-library-only `requirements.txt`.
3. Run `python -m unittest discover -s tests -v` and confirm all tests pass.
4. Add automated local HTTP and HTTPS transport integration tests, building on the one-off local HTTP smoke test.
5. Address Phase 2's remaining DNS/IP, retry, timeout, and TLS cases before claiming hardened SSRF protection.
