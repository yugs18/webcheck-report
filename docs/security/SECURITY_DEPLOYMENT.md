# Security Deployment Gate — WebCheck Report

This document is a deployment checklist, not an automatically enforced firewall. The Python client deliberately pins approved DNS socket addresses and filters prohibited IPs, but it cannot inspect every route, NAT rule, transparent proxy, DNS64/NAT64 translator, cloud network path, or host-level exception.

## Current supported scope

The reviewed code is suitable only as an early-stage, manually operated CLI for URLs the operator is authorized to check. It is not approved as a standalone boundary for arbitrary user-supplied URLs, a multi-tenant service, or a production SSRF-sensitive workflow.

## Required before accepting untrusted URLs

- [ ] Run the checker in a dedicated, unprivileged container, VM, or equivalent isolated environment. Do not mount host sockets, cloud credentials, service-account tokens, or other secrets into that environment.
- [ ] Enforce outbound network policy outside Python. Deny loopback, private, link-local, shared, reserved, multicast, metadata-service, and internal organizational destinations over both IPv4 and IPv6. Account for IPv4-mapped IPv6 and any translation or routing used by the deployment.
- [ ] Default outbound TCP to ports 80 and 443 only. If custom web ports are a real product requirement, allowlist only those explicit ports at the egress layer.
- [ ] Permit DNS only to the designated resolver. Do not allow arbitrary DNS tunnelling or arbitrary UDP/TCP egress from the workload.
- [ ] Verify the rules from inside the actual runtime, including attempts to reach loopback, RFC1918 addresses, IPv4/IPv6 link-local addresses, the cloud metadata service applicable to the environment, and any internal management ranges. Verify that approved public HTTP/HTTPS checks still work.
- [ ] Ensure the rules apply to IPv4 and IPv6, and cannot be bypassed by the container bridge, host routing, NAT, or a transparent proxy.
- [ ] For long-running service use, run each check in a killable process with a supervisor deadline and resource limits. The standalone CLI adds a 10-second supervisor wait, but the library API itself cannot forcibly cancel a slow-drip HTTP/TLS operation.
- [ ] Record the tested firewall/runtime configuration and repeat the checks after network-policy or infrastructure changes.

## Timeout notes

The application validates timeout values as finite, positive numbers no greater than 300 seconds; the standalone CLI currently uses a fixed 10-second supervisor wait. Its total budget begins before DNS. The caller stops waiting for DNS when the remaining budget expires, with at most four DNS resolver threads active; a system `getaddrinfo()` call that does not return may continue in a daemon thread and retain its slot. Socket timeouts and post-operation deadline checks reduce hanging, but they do not constitute forced cancellation of a blocking HTTP/TLS call at the exact wall-clock deadline.

The standalone CLI waits at most 10 seconds for the check thread before reporting a timeout and exiting; process shutdown stops its daemon threads. A service must use a killable worker process rather than leaving blocked work in a long-running process. A supervisor is not a substitute for egress policy. Use both controls when processing untrusted input.

## Go/no-go decision

**No-go for public or multi-tenant untrusted URL input** until egress policy is actively enforced and tested, and per-check work runs behind a killable process boundary with a verified supervisor deadline. For manual use against authorized public URLs, continue to treat the tool as an early-stage diagnostic, not a security scanner or security boundary.
