"""Regression checks for R5 replay labels and experiment coverage."""

from copy import deepcopy
import unittest

from analyze_r5 import DATA, check_pairs, check_selection, check_timing, policies, read, run_key, snapshot_key


class ReplayLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pair = read(DATA, "r5_pairs.jsonl.gz")[0]
        fields = ("layout", "n", "cap", "seed", "time")
        cls.tick = next(
            tick for tick in read(DATA, "r5_ticks.jsonl.gz")
            if all(tick[field] == cls.pair[field] for field in fields)
        )

    def test_archived_labels_match_replay(self):
        check_pairs([self.pair], [self.tick], recompute=False)

    def test_rejects_changed_labels(self):
        for field in ("proposed_direction", "proposed_distance", "event1", "event2", "event3"):
            with self.subTest(field=field):
                pair = deepcopy(self.pair)
                pair[field] = not pair[field]
                with self.assertRaisesRegex(ValueError, field):
                    check_pairs([pair], [self.tick], recompute=False)

    def test_rejects_changed_motion_record(self):
        pair = deepcopy(self.pair)
        pair["baseline"]["direction"]["progress_two"] += 1
        with self.assertRaisesRegex(ValueError, "baseline direction progress_two"):
            check_pairs([pair], [self.tick], recompute=False)


class ReplaySelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pairs = read(DATA, "r5_pairs.jsonl.gz")
        cls.ticks = read(DATA, "r5_ticks.jsonl.gz")
        cls.source = read(DATA, "r5_source_runs.jsonl")

    def test_archived_selection_matches_source(self):
        check_selection(self.pairs, self.ticks, self.source)

    def test_rejects_duplicate_or_missing_pairs(self):
        cases = (
            (self.pairs + self.pairs[:1], "Duplicate paired snapshot"),
            (self.pairs[1:], "expected 2 paired snapshots, found 1"),
        )
        for pairs, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    check_selection(pairs, self.ticks, self.source)

    def test_rejects_duplicate_scheduled_snapshot_with_same_total(self):
        ticks = self.ticks[1:] + self.ticks[1:2]
        with self.assertRaisesRegex(ValueError, "Duplicate scheduled snapshot"):
            check_selection(self.pairs, ticks, self.source)

    def test_rejects_changed_source_sample_count(self):
        first = deepcopy(self.source[0])
        first["selection"]["False"]["sampled"] -= 1
        with self.assertRaisesRegex(ValueError, "shared=False sampled expected 2"):
            check_selection(self.pairs, self.ticks, [first, *self.source[1:]])

    def test_rejects_eligible_snapshot_outside_seeded_sample(self):
        selected = {snapshot_key(pair) for pair in self.pairs}
        index, pair = next((i, pair) for i, pair in enumerate(self.pairs) if pair["match"])
        replacement = next(tick for tick in self.ticks
                           if run_key(tick) == run_key(pair) and tick["shared"] is True
                           and snapshot_key(tick) not in selected)
        pairs = self.pairs.copy()
        pairs[index] = dict(pair, time=replacement["time"])
        with self.assertRaisesRegex(ValueError, "seeded snapshot times expected"):
            check_selection(pairs, self.ticks, self.source)


class PolicyAndTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = read(DATA, "r5_policy_runs.jsonl.gz")
        cls.timing = read(DATA, "r5_work_timing.jsonl")

    def test_rejects_duplicate_or_missing_policy_runs(self):
        key = run_key(self.policy[0])
        incomplete = [row for row in self.policy if run_key(row) != key]
        duplicate = dict(self.policy[0], rate=self.policy[0]["rate"] + 100)
        with self.assertRaisesRegex(ValueError, "Missing policy run.*2 missing"):
            policies(incomplete)
        with self.assertRaisesRegex(ValueError, "Duplicate policy run"):
            policies([*self.policy, duplicate])

    def test_rejects_short_policy_cohort(self):
        first = self.policy[0]
        short = dict(first, job0_first=first["job0_first"][:-1])
        with self.assertRaisesRegex(ValueError, "job0_first expected 24 entries, found 23"):
            policies([short, *self.policy[1:]])

    def test_rejects_duplicate_or_missing_timing_runs(self):
        with self.assertRaisesRegex(ValueError, "Missing timing run"):
            check_timing(self.timing[1:])
        with self.assertRaisesRegex(ValueError, "Duplicate timing run"):
            check_timing([*self.timing, self.timing[0]])

    def test_rejects_missing_timing_percentile(self):
        first = deepcopy(self.timing[0])
        first["timing"]["wall_ms"].pop()
        with self.assertRaisesRegex(ValueError, "wall_ms must contain valid P50 and P95"):
            check_timing([first, *self.timing[1:]])


if __name__ == "__main__":
    unittest.main()
