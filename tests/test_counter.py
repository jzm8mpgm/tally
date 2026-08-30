import os
import tempfile
import unittest
import zipfile

from tally.counter import (
    Count,
    CountCache,
    UnreadableDocument,
    count_file,
    count_text,
    documents_in_folder,
    is_supported,
    is_temp_file,
)

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_docx(path, paragraphs, table_cells=()):
    body = []
    for text in paragraphs:
        body.append(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>")
    if table_cells:
        cells = "".join(
            f"<w:tc><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:tc>"
            for text in table_cells
        )
        body.append(f"<w:tbl><w:tr>{cells}</w:tr></w:tbl>")
    document = f"<w:document {W}><w:body>{''.join(body)}</w:body></w:document>"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document)
    return path


class TestCounting(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_counts_words_in_paragraphs(self):
        path = make_docx(
            self.path("chapter.docx"),
            ["The night shift begins", "with a phone call"],
        )
        self.assertEqual(count_file(path).words, 8)

    def test_paragraphs_do_not_run_together(self):
        path = make_docx(self.path("a.docx"), ["one", "two"])
        self.assertEqual(count_file(path).words, 2)

    def test_counts_table_text(self):
        path = make_docx(
            self.path("t.docx"), ["Intro line"], table_cells=["alpha", "beta gamma"]
        )
        self.assertEqual(count_file(path).words, 5)

    def test_punctuation_only_tokens_are_not_words(self):
        self.assertEqual(count_text("hello — world").words, 2)
        self.assertEqual(count_text("* * *").words, 0)

    def test_hyphenated_words_count_once(self):
        self.assertEqual(count_text("state-of-the-art care").words, 2)

    def test_characters_exclude_spaces(self):
        self.assertEqual(count_text("ab cd").characters, 4)

    def test_plain_text_files(self):
        path = self.path("notes.md")
        with open(path, "w") as handle:
            handle.write("# Heading\n\nsome words here\n")
        # The lone "#" is markup, not prose.
        self.assertEqual(count_file(path).words, 4)

    def test_bad_zip_raises(self):
        path = self.path("broken.docx")
        with open(path, "w") as handle:
            handle.write("not a zip")
        with self.assertRaises(UnreadableDocument):
            count_file(path)

    def test_missing_body_raises(self):
        path = self.path("empty.docx")
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("hello.txt", "hi")
        with self.assertRaises(UnreadableDocument):
            count_file(path)

    def test_count_addition(self):
        self.assertEqual(Count(2, 5) + Count(3, 4), Count(5, 9))


class TestClassification(unittest.TestCase):
    def test_word_lock_files_are_ignored(self):
        self.assertTrue(is_temp_file("~$draft.docx"))
        self.assertFalse(is_supported("~$draft.docx"))
        self.assertFalse(is_supported(".hidden.docx"))

    def test_supported_extensions(self):
        self.assertTrue(is_supported("Chapter 1.DOCX"))
        self.assertTrue(is_supported("notes.md"))
        self.assertFalse(is_supported("scan.pdf"))


class TestFolderScan(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "part two"))
        make_docx(os.path.join(self.dir, "one.docx"), ["a b c"])
        make_docx(os.path.join(self.dir, "part two", "two.docx"), ["d e"])
        make_docx(os.path.join(self.dir, "~$one.docx"), ["ignored"])

    def test_recursive(self):
        found = documents_in_folder(self.dir, recursive=True)
        self.assertEqual([os.path.basename(p) for p in found], ["one.docx", "two.docx"])

    def test_non_recursive(self):
        found = documents_in_folder(self.dir, recursive=False)
        self.assertEqual([os.path.basename(p) for p in found], ["one.docx"])

    def test_missing_folder_is_empty(self):
        self.assertEqual(documents_in_folder("/nope/nowhere"), [])


class TestCache(unittest.TestCase):
    def test_recount_after_change(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "draft.docx")
        make_docx(path, ["one two"])
        cache = CountCache()
        self.assertEqual(cache.count(path).words, 2)
        make_docx(path, ["one two three four"])
        os.utime(path, (0, 0))  # force a different mtime
        self.assertEqual(cache.count(path).words, 4)

    def test_missing_file_raises(self):
        with self.assertRaises(UnreadableDocument):
            CountCache().count("/nope/missing.docx")


if __name__ == "__main__":
    unittest.main()
