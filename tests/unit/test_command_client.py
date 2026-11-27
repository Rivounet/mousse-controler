from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock
import urllib.error

from mousse_controler import command_client


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return self.body


class CommandClientTests(unittest.TestCase):
    def config(self, directory: str) -> Path:
        path = Path(directory) / "controller.json"
        path.write_text(json.dumps({
            "command_token_dpapi": "protected-token",
            "command_port": 43210,
        }), encoding="utf-8")
        return path

    def test_invoke_builds_authenticated_bounded_loopback_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            before = int(time.time() * 1000)
            with (
                mock.patch.object(
                    command_client, "unprotect", return_value=b"local-token",
                ) as unprotect,
                mock.patch.object(
                    command_client.urllib.request,
                    "urlopen",
                    return_value=_Response(b'{"accepted":true}'),
                ) as urlopen,
            ):
                result = command_client.invoke(
                    self.config(directory), "transport_status", {"detail": True},
                )
            after = int(time.time() * 1000)

        self.assertEqual(result, {"accepted": True})
        unprotect.assert_called_once_with("protected-token")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:43210/v1/command")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer local-token")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)
        payload = json.loads(request.data)
        self.assertEqual(payload["command"], "transport_status")
        self.assertEqual(payload["arguments"], {"detail": True})
        self.assertEqual(payload["ttl_ms"], 5_000)
        self.assertLessEqual(before, payload["issued_at_ms"])
        self.assertLessEqual(payload["issued_at_ms"], after)
        self.assertTrue(payload["command_id"])

    def test_http_error_is_translated_with_status_and_response(self) -> None:
        failure = urllib.error.HTTPError(
            "http://127.0.0.1/v1/command",
            403,
            "Forbidden",
            {},
            io.BytesIO(b'{"error":"denied"}'),
        )
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(
                    command_client, "unprotect", return_value=b"local-token",
                ),
                mock.patch.object(
                    command_client.urllib.request, "urlopen", side_effect=failure,
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, 'command rejected.*403.*"denied"',
                ):
                    command_client.invoke(self.config(directory), "stop")


if __name__ == "__main__":
    unittest.main()
