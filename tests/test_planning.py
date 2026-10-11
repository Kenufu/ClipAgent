import unittest

from clipagent.planning import (
    build_timeline,
    make_srt,
    parse_request,
    repair_duration,
    review_timeline_evidence,
    srt_max_end,
    validate_timeline,
)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.assets = [
            {"id": "a", "duration": 30.0},
            {"id": "b", "duration": 30.0},
        ]
        self.cues = [
            {"id": "a:t1", "asset_id": "a", "start": 1.0, "end": 5.0, "text": "The problem is slow search.", "words": []},
            {"id": "a:t2", "asset_id": "a", "start": 7.0, "end": 12.0, "text": "The solution is a source linked timeline.", "words": []},
            {"id": "b:t1", "asset_id": "b", "start": 2.0, "end": 7.0, "text": "The demonstration result is a short video.", "words": []},
            {"id": "b:t2", "asset_id": "b", "start": 9.0, "end": 13.0, "text": "The speaker closes the session.", "words": []},
        ]

    def test_request_parsing_and_order(self):
        options = parse_request(
            "Create a 12-25 second recap covering the problem, solution, and demonstration result; put demonstration result first and export vertically."
        )
        self.assertEqual(options["topics"], ["the problem", "solution", "demonstration result"])
        self.assertEqual(options["aspect"], "9:16")
        self.assertEqual((options["min_seconds"], options["max_seconds"]), (12, 25))
        timeline, unresolved = build_timeline(self.assets, self.cues, options)
        self.assertEqual(unresolved, [])
        self.assertEqual(timeline[0]["asset_id"], "b")
        self.assertEqual(len(timeline), 3)
        self.assertGreater(validate_timeline(timeline, self.assets), 12)

    def test_subtitles_remap_after_reorder(self):
        timeline = [
            {"asset_id": "b", "start": 2.0, "end": 7.0, "evidence_ids": ["b:t1"]},
            {"asset_id": "a", "start": 1.0, "end": 5.0, "evidence_ids": ["a:t1"]},
        ]
        srt = make_srt(timeline, self.cues)
        self.assertIn("00:00:05,000 --> 00:00:09,000", srt)
        self.assertIn("The demonstration result", srt.splitlines()[2])
        self.assertEqual(srt_max_end(srt), 9.0)

    def test_repair_removes_only_optional_clip(self):
        timeline = [
            {"asset_id": "a", "start": 1.0, "end": 5.0, "evidence_ids": ["a:t1"], "required": True},
            {"asset_id": "b", "start": 9.0, "end": 13.0, "evidence_ids": ["b:t2"], "required": False},
        ]
        revised, _ = repair_duration(timeline, self.cues, self.assets, {"min_seconds": 3, "max_seconds": 5}, 8.0)
        self.assertEqual(len(revised), 1)
        self.assertEqual(revised[0]["evidence_ids"], ["a:t1"])

    def test_rejects_out_of_bounds(self):
        with self.assertRaisesRegex(ValueError, "out-of-bounds"):
            validate_timeline([{"asset_id": "a", "start": 29, "end": 31}], self.assets)

    def test_manual_trim_rechecks_word_level_evidence(self):
        cue = {
            "id": "a:t1", "asset_id": "a", "start": 1.0, "end": 5.0,
            "text": "The problem is slow search.",
            "words": [
                {"start": 1.0, "end": 1.5, "text": "The"},
                {"start": 1.6, "end": 2.2, "text": "problem"},
                {"start": 3.0, "end": 3.5, "text": "is"},
                {"start": 3.6, "end": 4.2, "text": "slow"},
                {"start": 4.3, "end": 5.0, "text": "search."},
            ],
        }
        clip = {
            "asset_id": "a", "start": 2.9, "end": 5.0,
            "evidence_ids": ["a:t1"], "required": True, "score": 1.0,
        }
        reviewed, topics, unresolved = review_timeline_evidence(
            [clip], [cue], ["problem"], annotate=True
        )
        self.assertFalse(reviewed[0]["required"])
        self.assertEqual(reviewed[0]["score"], 0.0)
        self.assertEqual(topics[0]["evidence_ids"], [])
        self.assertIn("problem", unresolved[0])

    def test_manual_edit_rebuilds_evidence_ids(self):
        clips = [{"asset_id": "a", "start": 7.0, "end": 12.0, "evidence_ids": ["a:t1"]}]
        reviewed, topics, unresolved = review_timeline_evidence(
            clips, self.cues, ["solution"], annotate=True
        )
        self.assertEqual(reviewed[0]["evidence_ids"], ["a:t2"])
        self.assertTrue(reviewed[0]["required"])
        self.assertEqual(topics[0]["evidence_ids"], ["a:t2"])
        self.assertEqual(unresolved, [])

    def test_unverified_partial_cue_without_word_times(self):
        clips = [{"asset_id": "b", "start": 2.0, "end": 3.0}]
        reviewed, topics, unresolved = review_timeline_evidence(
            clips, self.cues, ["demonstration result"], annotate=True
        )
        self.assertEqual(reviewed[0]["evidence_ids"], [])
        self.assertFalse(topics[0]["verified"])
        self.assertEqual(len(unresolved), 1)

    def test_partial_multiword_topic_is_not_verified(self):
        clips = [{"asset_id": "a", "start": 1.0, "end": 5.0}]
        _, topics, unresolved = review_timeline_evidence(
            clips, self.cues, ["problem solution"]
        )
        self.assertFalse(topics[0]["verified"])
        self.assertEqual(len(unresolved), 1)


if __name__ == "__main__":
    unittest.main()
