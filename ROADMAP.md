# WebCheck Report — Development Roadmap

## Project vision

Build a reliable, understandable web-diagnostics tool; use its development to strengthen practical Python, networking, HTTP, secure-programming, testing, and product-development skills; and validate demand before investing in larger features.

## Current status

**Stage:** CLI prototype. Application-level Phase 2 hardening is complete for manual checks of authorized public URLs; the production/untrusted-input gate remains open. Do not treat the tool as production-hardened or as a security boundary for arbitrary URLs.

**Local verification:** 49 tests passed on Python 3.13.5 in the final review worktree. The suite includes local HTTPS integration tests using test-only certificates. A GitHub Actions matrix has been added for Python 3.12, 3.13, and 3.14; those remote CI jobs must pass before release. Re-run the suite in the actual checkout before committing.

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

- [x] Resolve hostname candidates with `socket.getaddrinfo()` through a bounded caller-wait helper.
- [x] Filter non-global candidates and fail if none remain.
- [x] Connect directly to the selected approved socket address.
- [x] Use the pinned connection for the HTTP request rather than opening a separate `urllib` connection.
- [x] Keep redirects disabled.
- [x] Preserve the original hostname for HTTPS TLS identity with the default client SSL context.
- [x] Add unit tests for mixed DNS answers, all-prohibited answers, DNS errors, exact socket destination, request construction, redirect behavior, and the TLS hostname argument.

### Security review status (2026-10-20)

The code-level review checklist below has been addressed for the reviewed source snapshot. This means the review and documentation tasks are complete; it does **not** mean the tool is production-hardened or appropriate for untrusted targets.

- [x] Add deterministic tests for connection failure across multiple approved candidates and socket cleanup; repair the test assertion typo so socket cleanup is genuinely asserted.
- [x] Verify local HTTPS behavior with a trusted certificate and matching SAN, and reject untrusted or wrong-SAN certificates. Keep certificate verification enabled.
- [x] Cover IPv4/IPv6 loopback, private, link-local, reserved, IPv4-mapped, multicast, and scoped-address policy cases in the reviewed suite.
- [x] Test IDNA hostname normalization and Host-header formatting; reject scoped IPv6 literals explicitly.
- [x] Validate timeout input: finite positive numeric values only, with a 300-second maximum.
- [x] Bound caller waiting for system DNS resolution and cap outstanding resolver workers at four. A timed-out resolver call cannot be forcibly cancelled and may retain its bounded worker slot until the OS resolver returns.
- [x] Start the operation budget before DNS and pass the remaining budget to DNS and subsequent socket operations.
- [x] Reject responses detected as late and guarantee response/connection cleanup on that path.
- [x] Review `ipaddress.is_global` and strengthen the policy to reject multicast, scoped, unspecified, loopback, link-local, private, and reserved address properties explicitly in addition to requiring global classification.
- [x] Document direct connections and proxy behavior; the client intentionally bypasses environment-configured HTTP proxies.
- [x] Add regression coverage for destination filtering, bounded DNS wait, invalid timeouts, timeout overrun/cleanup, TLS validation, retries, and redirect behavior.
- [x] Add a Python 3.12/3.13/3.14 GitHub Actions test matrix.
- [x] Evaluate egress restrictions and record a deployment gate in `SECURITY_DEPLOYMENT.md`: external firewall/network policy is mandatory before the tool accepts untrusted URLs as a service.
- [ ] For any long-running service, run each check in a killable process with a supervisor deadline so slow-drip HTTP/TLS operations cannot outlive the per-check budget. The standalone CLI already has a 10-second supervisor wait and process-exit boundary; direct library callers still need their own supervisor.
- [ ] Configure and verify host/container/network egress policy in the actual deployment environment before processing untrusted URLs. This cannot be proved or applied from a source-code patch alone.

**Phase 2 conclusion:** The application-level code review is complete for the current manual CLI use case, with 49 tests passing on Python 3.13.5. The standalone CLI applies a 10-second supervisor wait and exits when a check exceeds it; the library-level `check_url()` call remains best-effort. This does **not** mark the product production-hardened. A killable per-check process boundary and enforced outbound network policy remain release blockers for any service or workflow that accepts untrusted URLs.

## Phase 3 — Reliability and usability

**Goal:** Make results predictable and easier to integrate into developer workflows.

- [x] Review error messages for clarity and consistency.
- [x] Review elapsed-time semantics and timeout behavior.
- [x] Add tests for report-write failures and remaining CLI edge cases.
- [x] Define stable JSON result fields and behavior for redirects and HTTP error statuses.
- [x] Add type annotations and documentation where they improve clarity.
- [x] Run the complete test suite after every meaningful change.

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
- [x] Add continuous integration to run tests automatically (Python 3.12/3.13/3.14 matrix; verify remote runs before release).
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

1. Apply the reviewed source, tests, documentation, fixtures, and CI workflow in the actual checkout.
2. Run `python -m unittest discover -s tests -v` and confirm all tests pass locally; verify the Python-version CI matrix when pushed.
3. Before accepting untrusted URLs, enforce and verify egress restrictions and replace the best-effort HTTP/TLS timeout with a boundary that can stop slow-drip operations.
4. Keep the production/untrusted-input warning until those security gates are satisfied.
