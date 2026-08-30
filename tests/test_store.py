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
