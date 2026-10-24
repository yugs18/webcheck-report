import http.server
import socket
import ssl
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from webcheck.http_client import check_url #type: ignore


FIXTURES = Path(__file__).parent / "fixtures"
CA_CERT = FIXTURES / "ca.crt"
SERVER_CERT = FIXTURES / "server.crt"
SERVER_KEY = FIXTURES / "server.key"


class QuietHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"local TLS test passed")

    def log_message(self, format, *args):
        pass


class LocalHTTPSTestServer:
    """Run a real HTTPS server on loopback."""

    def __init__(self, certfile, keyfile):
        self.server = http.server.HTTPServer(
            ("127.0.0.1", 0),
            QuietHandler,
        )

        server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_context.load_cert_chain(
            certfile=certfile,
            keyfile=keyfile,
        )

        self.server.socket = server_context.wrap_socket(
            self.server.socket,
            server_side=True,
        )

        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class TestHTTPSIntegration(unittest.TestCase):
    def run_local_check(self, client_context, certfile=SERVER_CERT, keyfile=SERVER_KEY):
        with LocalHTTPSTestServer(certfile, keyfile) as server:
            # Only this test resolves example.test to loopback.
            # Production DNS filtering remains unchanged.
            address_info = (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", server.port),
            )

            with (
                patch(
                    "webcheck.http_client.resolve_public_host",
                    return_value=[address_info],
                ),
                patch(
                    "webcheck.http_client.ssl.create_default_context",
                    return_value=client_context,
                ),
            ):
                return check_url(
                    f"https://example.test:{server.port}/",
                    timeout=3,
                )

    def test_trusted_certificate_and_matching_san_succeed(self):
        context = ssl.create_default_context(cafile=CA_CERT)

        result = self.run_local_check(context)

        self.assertEqual(
            result["status_code"], 200, msg=f"Unexpected check result: {result!r}",
        )
        self.assertIsNone(
            result["error"], msg=f"Unexpected check error: {result['error']!r}",
        )

    def test_untrusted_certificate_is_rejected(self):
        # System trust store does not include our private test CA.
        context = ssl.create_default_context()

        result = self.run_local_check(context)

        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])
        self.assertIn(
            "CERTIFICATE_VERIFY_FAILED",
            result["error"],
        )

    def test_trusted_certificate_with_wrong_san_is_rejected(self):
        context = ssl.create_default_context(cafile=CA_CERT)

        result = self.run_local_check(
            context,
            certfile=FIXTURES / "wrong-server.crt",
            keyfile=FIXTURES / "wrong-server.key",
        )

        self.assertIsNone(result["status_code"])
        self.assertIsNotNone(result["error"])
        self.assertIn(
            "CERTIFICATE_VERIFY_FAILED",
            result["error"],
        )


if __name__ == "__main__":
    unittest.main()