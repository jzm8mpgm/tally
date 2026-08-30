import os
import tempfile
import unittest

from tally.engine import Engine, _prune_nested, source_for
from tally.store import State

from .test_counter import make_docx


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.docs = os.path.join(self.tmp, "Book")
        os.makedirs(self.docs)
        make_docx(os.path.join(self.docs, "one.docx"), ["a b c d"])
        make_docx(os.path.join(self.docs, "two.docx"), ["e f"])

        self.state = State(path=os.path.join(self.tmp, "state.json"))
        self.state.active.sources = [source_for(self.docs)]
        self.engine = Engine(self.state)

    def tearDown(self):
        self.engine.stop()

    def test_totals_across_a_folder(self):
        snapshot = self.engine.refresh()
        self.assertEqual(snapshot.total, 6)
        self.assertEqual(snapshot.readable, 2)
        self.assertEqual(snapshot.problems, 0)

    def test_documents_sorted_by_size(self):
        snapshot = self.engine.refresh()
        self.assertEqual([d.name for d in snapshot.documents], ["one", "two"])

    def test_missing_files_are_flagged_not_fatal(self):
        self.state.active.sources.append(source_for("/nope/ghost.docx"))
        snapshot = self.engine.refresh()
        self.assertEqual(snapshot.total, 6)
        self.assertEqual(snapshot.problems, 1)
        self.assertTrue(snapshot.documents[-1].missing)

    def test_a_file_and_its_folder_are_not_double_counted(self):
        self.state.active.sources.append(
            source_for(os.path.join(self.docs, "one.docx"))
        )
        self.assertEqual(self.engine.refresh().total, 6)

    def test_importing_a_manuscript_is_not_counted_as_writing(self):
        self.engine.refresh()
        self.assertEqual(self.engine.written_today, 0)
        big = os.path.join(self.tmp, "manuscript.docx")
        make_docx(big, [" ".join(["word"] * 500)])
        self.state.active.sources.append(source_for(big))
        self.engine.sources_changed()
        self.assertEqual(self.engine.snapshot.total, 506)
        self.assertEqual(self.engine.written_today, 0)

    def test_editing_a_document_does_count_as_writing(self):
        self.engine.refresh()
        path = os.path.join(self.docs, "two.docx")
        make_docx(path, ["e f g h i"])
        os.utime(path, (1, 1))
        self.engine.refresh()
        self.assertEqual(self.engine.snapshot.total, 9)
        self.assertEqual(self.engine.written_today, 3)

    def test_watch_directories(self):
        self.state.active.sources.append(
            source_for(os.path.join(self.docs, "one.docx"))
        )
        self.assertEqual(
            self.engine.watch_directories(self.state.active), {self.docs}
        )


class TestPruneNested(unittest.TestCase):
    def test_child_directories_are_dropped(self):
        kept = _prune_nested(frozenset({"/a", "/a/b", "/c"}))
        self.assertEqual(sorted(kept), ["/a", "/c"])

    def test_similar_prefixes_are_kept(self):
        kept = _prune_nested(frozenset({"/a", "/ab"}))
        self.assertEqual(sorted(kept), ["/a", "/ab"])


if __name__ == "__main__":
    unittest.main()
