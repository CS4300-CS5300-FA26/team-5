import unittest
from unittest import mock

import ai_review


class TruncateDiffTests(unittest.TestCase):
    def test_short_diff_is_unchanged(self):
        self.assertEqual(ai_review.truncate_diff("a\nb\n", limit=100), ("a\nb\n", False))

    def test_long_diff_is_cut_at_a_line_boundary(self):
        diff, truncated = ai_review.truncate_diff("line1\nline2\nline3\n", limit=9)
        self.assertEqual(diff, "line1\n")
        self.assertTrue(truncated)


class ExtractTextTests(unittest.TestCase):
    def test_joins_text_from_message_items_only(self):
        response = {
            "output": [
                {"type": "reasoning", "summary": []},
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "First."},
                        {"type": "output_text", "text": "Second."},
                    ],
                },
            ]
        }
        self.assertEqual(ai_review.extract_text(response), "First.\nSecond.")

    def test_reports_refusal(self):
        response = {
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}
            ]
        }
        self.assertIn("declined", ai_review.extract_text(response))

    def test_empty_output_gives_empty_text(self):
        self.assertEqual(ai_review.extract_text({"output": []}), "")


class BuildInputTests(unittest.TestCase):
    def test_includes_title_body_and_diff(self):
        text = ai_review.build_input("Add login", "Closes #3", "+x", truncated=False)
        self.assertIn("Add login", text)
        self.assertIn("Closes #3", text)
        self.assertIn("+x", text)
        self.assertNotIn("cut off", text)

    def test_flags_truncation(self):
        text = ai_review.build_input("t", None, "+x", truncated=True)
        self.assertIn("cut off", text)
        self.assertIn("(none)", text)


class FormatReviewTests(unittest.TestCase):
    def test_review_has_marker_and_commit(self):
        body = ai_review.format_review("Looks fine.", "abcdef1234", truncated=False)
        self.assertTrue(body.startswith(ai_review.REVIEW_MARKER))
        self.assertIn("abcdef1", body)
        self.assertIn("Looks fine.", body)


class PostReviewTests(unittest.TestCase):
    def test_posts_comment_only_review_on_the_reviewed_commit(self):
        with mock.patch.object(ai_review, "request_json", return_value={"id": 9}) as req:
            ai_review.post_review("org/repo", "5", "tok", "body", "abc123")
        url, payload, _, method = req.call_args.args
        self.assertTrue(url.endswith("/pulls/5/reviews"))
        self.assertEqual(method, "POST")
        self.assertEqual(payload, {"body": "body", "event": "COMMENT", "commit_id": "abc123"})


def review(id, login=ai_review.BOT_LOGIN, body=ai_review.REVIEW_MARKER):
    return {"id": id, "node_id": f"node{id}", "user": {"login": login}, "body": body}


class CollapsePreviousReviewsTests(unittest.TestCase):
    def collapsed_ids(self, reviews, keep_id):
        responses = [reviews] + [{"data": {}}] * len(reviews)
        with mock.patch.object(ai_review, "request_json", side_effect=responses) as req:
            ai_review.collapse_previous_reviews("org/repo", "5", "tok", keep_id)
        mutations = [c.args[1] for c in req.call_args_list[1:]]
        self.assertTrue(all(c.args[0].endswith("/graphql") for c in req.call_args_list[1:]))
        return [m["variables"]["id"] for m in mutations]

    def test_collapses_only_older_bot_reviews(self):
        reviews = [
            review(1),
            review(2, login="xamspanda"),  # a human quoting the bot
            review(3, body="plain bot review without marker"),
            review(4, body=None),  # GitHub sends null for empty review bodies
            review(5),  # the review just posted
        ]
        self.assertEqual(self.collapsed_ids(reviews, keep_id=5), ["node1"])

    def test_nothing_to_collapse_on_first_review(self):
        self.assertEqual(self.collapsed_ids([review(5)], keep_id=5), [])

    def test_graphql_error_is_a_warning_not_a_crash(self):
        responses = [[review(1)], {"errors": [{"message": "forbidden"}]}]
        with mock.patch.object(ai_review, "request_json", side_effect=responses), \
                mock.patch("builtins.print") as printed:
            ai_review.collapse_previous_reviews("org/repo", "5", "tok", keep_id=5)
        self.assertIn("::warning::", printed.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
