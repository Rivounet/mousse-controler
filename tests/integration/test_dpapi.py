from __future__ import annotations

import base64
import os
import unittest

from mousse_controler import dpapi


class DpapiBoundaryTests(unittest.TestCase):
    def test_current_user_round_trip_uses_an_opaque_blob(self) -> None:
        secret = os.urandom(32)

        protected = dpapi.protect(secret)

        self.assertNotEqual(base64.b64decode(protected), secret)
        self.assertEqual(dpapi.unprotect(protected), secret)

    def test_malformed_base64_is_rejected_before_dpapi(self) -> None:
        with self.assertRaises(ValueError):
            dpapi.unprotect("not valid base64 !")


if __name__ == "__main__":
    unittest.main()
