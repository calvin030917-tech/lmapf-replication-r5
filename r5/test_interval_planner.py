"""Planner regression tests that also run with Python assertions disabled."""

import unittest

from interval_planner import plan, safe
from warehouse import Board, W, scenario


class PlannerSafetyTests(unittest.TestCase):
    def test_plan_constructs_and_checks_seed_paths(self):
        scene, state = scenario("w1", 24, 6, 6101)
        paths, _, _, costs = plan(scene, state)
        self.assertEqual(tuple(path[0] for path in paths), state.cells)
        self.assertTrue(all(len(path) == W + 1 for path in paths))
        self.assertGreater(costs["seed_tests"], 0)

    def test_rejects_unsafe_paths(self):
        board = Board(["...T"])
        invalid = (
            ("vertex collision", ((0, 1), (2, 1))),
            ("edge swap", ((0, 1), (1, 0))),
            ("illegal move", ((0, 2),)),
            ("untraversable cell", ((2, 3),)),
        )
        for description, paths in invalid:
            with self.subTest(description=description):
                with self.assertRaises(AssertionError):
                    safe(board, paths)


if __name__ == "__main__":
    unittest.main()
