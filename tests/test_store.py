import os
import tempfile
import unittest

from tally.store import Project, Source, State, today_key


def fresh(tmp):
    return State(path=os.path.join(tmp, "state.json"))


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = fresh(self.tmp)
        self.project = self.state.active

    def test_first_count_of_the_day_is_the_baseline(self):
        self.assertEqual(self.state.record_total(self.project.id, 50_000), 0)
        self.assertEqual(self.state.record_total(self.project.id, 50_800), 800)

    def test_deleting_words_never_goes_negative(self):
        self.state.record_total(self.project.id, 1000)
        self.assertEqual(self.state.record_total(self.project.id, 400), 0)
        self.assertEqual(self.state.written_today(self.project.id), 0)
        # ...and writing back up counts from the new floor
        self.assertEqual(self.state.record_total(self.project.id, 900), 500)

    def test_adding_a_document_does_not_count_as_writing(self):
        self.state.record_total(self.project.id, 1000)
        self.state.record_total(self.project.id, 1200)
        self.state.shift_baseline(self.project.id, 80_000)  # imported a manuscript
        self.state.record_total(self.project.id, 81_200)
        self.assertEqual(self.state.written_today(self.project.id), 200)

    def test_series_is_padded_and_ordered(self):
        self.state.record_total(self.project.id, 10)
        series = self.state.daily_series(self.project.id, days=5)
        self.assertEqual(len(series), 5)
        self.assertEqual(series[-1][0], today_key())
        self.assertEqual([value for _, value in series[:-1]], [0, 0, 0, 0])

    def test_streak_counts_consecutive_days(self):
        pid = self.project.id
        self.state.history[pid] = {
            "2000-01-01": {"start": 0, "end": 10},
        }
        self.state.record_total(pid, 0)
        self.state.record_total(pid, 500)
        self.assertEqual(self.state.streak(pid), 1)


class TestProjects(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = fresh(self.tmp)

    def test_default_project_exists(self):
        self.assertEqual(len(self.state.projects), 1)
        self.assertIsNotNone(self.state.active)

    def test_cannot_delete_the_last_project(self):
        self.state.remove_project(self.state.active_id)
        self.assertEqual(len(self.state.projects), 1)

    def test_add_and_switch(self):
        first = self.state.active_id
        second = self.state.add_project("Book Four")
        self.assertEqual(self.state.active_id, second.id)
        self.state.active_id = first
        self.assertEqual(self.state.active.id, first)

    def test_switching_to_an_unknown_project_is_ignored(self):
        current = self.state.active_id
        self.state.active_id = "nonsense"
        self.assertEqual(self.state.active_id, current)

    def test_deleted_project_is_gone_from_every_lookup(self):
        first = self.state.active_id
        second = self.state.add_project("Book Four")
        third = self.state.add_project("Book Five")
        self.state.active_id = first

        self.state.remove_project(second.id)

        self.assertIsNone(self.state.project(second.id))
        self.assertNotIn(second.id, [p.id for p in self.state.projects])
        self.assertEqual(len(self.state.projects), 2)
        # Deleting a project that was not active must not disturb which
        # project is active.
        self.assertEqual(self.state.active_id, first)
        self.assertEqual(self.state.active.id, first)
        self.assertIsNotNone(self.state.project(third.id))

    def test_deleting_the_active_project_falls_back_to_the_first_remaining(self):
        first = self.state.active_id
        second = self.state.add_project("Book Four")
        self.state.active_id = second.id

        self.state.remove_project(second.id)

        self.assertEqual(self.state.active_id, first)
        self.assertEqual(self.state.active.id, first)
        self.assertIsNone(self.state.project(second.id))

    def test_removing_a_project_drops_its_history(self):
        second = self.state.add_project("Book Four")
        self.state.record_total(second.id, 500)
        self.assertIn(second.id, self.state.history)

        self.state.remove_project(second.id)

        self.assertNotIn(second.id, self.state.history)

    def test_removing_an_already_removed_project_is_a_no_op(self):
        second = self.state.add_project("Book Four")
        self.state.remove_project(second.id)
        before = [p.id for p in self.state.projects]

        self.state.remove_project(second.id)  # deleting it again must not error

        self.assertEqual([p.id for p in self.state.projects], before)


class TestRemoveSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.state = fresh(self.tmp)
        self.project = self.state.active
        self.project.sources = [
            Source(kind="file", path="/tmp/one.docx"),
            Source(kind="folder", path="/tmp/chapters", recursive=True),
        ]

    def test_removes_a_matching_file_source(self):
        self.assertTrue(self.project.remove_source("/tmp/one.docx"))
        self.assertEqual([s.path for s in self.project.sources], ["/tmp/chapters"])

    def test_removes_a_matching_folder_source(self):
        self.assertTrue(self.project.remove_source("/tmp/chapters"))
        self.assertEqual([s.path for s in self.project.sources], ["/tmp/one.docx"])

    def test_leaves_sources_untouched_when_nothing_matches(self):
        self.assertFalse(self.project.remove_source("/tmp/ghost.docx"))
        self.assertEqual(len(self.project.sources), 2)

    def test_a_document_inside_a_folder_is_not_itself_a_match(self):
        # Only the folder's own path removes it — a file within it is not a
        # source in its own right.
        self.assertFalse(self.project.remove_source("/tmp/chapters/one.docx"))
        self.assertEqual(len(self.project.sources), 2)


class TestPersistence(unittest.TestCase):
    def test_round_trip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "state.json")
        state = State(path=path)
        state.active.name = "Book Four"
        state.active.goal = 1200
        state.active.sources = [
            Source(kind="file", path="/tmp/one.docx"),
            Source(kind="folder", path="/tmp/chapters", recursive=False),
        ]
        state.record_total(state.active.id, 4321)
        state.save()

        reloaded = State.load(path)
        self.assertEqual(reloaded.active.name, "Book Four")
        self.assertEqual(reloaded.active.goal, 1200)
        self.assertEqual(len(reloaded.active.sources), 2)
        self.assertFalse(reloaded.active.sources[1].recursive)
        self.assertIn(today_key(), reloaded.history[reloaded.active.id])

    def test_corrupt_file_falls_back_to_defaults(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "state.json")
        with open(path, "w") as handle:
            handle.write("{ not json")
        state = State.load(path)
        self.assertEqual(len(state.projects), 1)


if __name__ == "__main__":
    unittest.main()
