# HTTPS Test Fixtures

These certificates and private keys are used exclusively by the local HTTPS
integration tests for WebCheck Report.

- `ca.crt`: Test certificate authority certificate.
- `server.crt` and `server.key`: Test server certificate and private key.
- `wrong-server.crt` and `wrong-server.key`: Certificate and key used to test
  hostname-verification failure.

These are test-only credentials. Never reuse them in production or for real
services.

The CA private key and certificate-generation artifacts are intentionally
excluded because the integration tests do not require them.