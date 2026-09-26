from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import MagicMock, patch

import auto_checkin


class Response:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body

    def json(self):
        return self.body


class CheckInTests(unittest.TestCase):
    def run_with_responses(self, *responses):
        session = MagicMock()
        session.__enter__.return_value = session
        session.request.side_effect = responses
        with patch.object(auto_checkin.requests, "Session", return_value=session):
            with redirect_stdout(StringIO()):
                result = auto_checkin.run_once("test-cookie", 1, 1)
        return result, session

    def test_already_checked_in_skips_post(self):
        result, session = self.run_with_responses(Response(200, {
            "object": "me", "moemoepoint": 5,
            "has_checked_in_today": True, "has_unread_messages": False,
        }))
        self.assertTrue(result)
        self.assertEqual(session.request.call_count, 1)
        self.assertEqual(session.request.call_args.args[0], "GET")

    def test_conflict_already_exists_is_success(self):
        result, session = self.run_with_responses(
            Response(200, {
                "object": "me", "moemoepoint": 5,
                "has_checked_in_today": False, "has_unread_messages": False,
            }),
            Response(409, {"code": "ALREADY_EXISTS", "detail": "Already checked in."}),
        )
        self.assertTrue(result)
        self.assertEqual(session.request.call_args.args[0], "POST")
        self.assertIn("/api/v1/me/check-ins", session.request.call_args.args[1])

    def test_expired_cookie_is_failure(self):
        result, session = self.run_with_responses(Response(401, {
            "code": "INVALID_CREDENTIAL", "detail": "Credential expired.",
        }))
        self.assertFalse(result)
        self.assertEqual(session.request.call_count, 1)

    def test_status_error_can_still_check_in(self):
        result, session = self.run_with_responses(
            Response(503, {"code": "SERVICE_UNAVAILABLE"}),
            Response(200, {
                "object": "check_in", "moemoepoint_awarded": 0,
                "moemoepoint": 5,
            }),
        )
        self.assertTrue(result)
        self.assertEqual(session.request.call_count, 2)

    def test_retired_route_is_failure(self):
        result, session = self.run_with_responses(
            Response(404, {"code": "NOT_FOUND"}),
            Response(404, {"code": "NOT_FOUND"}),
        )
        self.assertFalse(result)
        self.assertEqual(session.request.call_count, 2)

    def test_multiple_cookies_and_precedence(self):
        self.assertEqual(
            auto_checkin.collect_cookies(None, "one\ntwo\none", "old"),
            ["one", "two"],
        )
        self.assertEqual(
            auto_checkin.collect_cookies(None, '["one", "two"]', "old"),
            ["one", "two"],
        )


if __name__ == "__main__":
    unittest.main()
