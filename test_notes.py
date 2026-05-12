"""SmartNotes birim testleri — unittest ile."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from smartnotes import database as db


class BaseTestCase(unittest.TestCase):
    """Her test için geçici veritabanı oluşturur."""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        db.DB_PATH = self._tmp.name
        db.init_db()

    def tearDown(self):
        os.unlink(self._tmp.name)


class TestNoteCRUD(BaseTestCase):

    def test_add_and_get_note(self):
        note_id = db.add_note("Test Başlık", "Test içerik", tags=["python", "test"])
        note = db.get_note(note_id)
        self.assertIsNotNone(note)
        self.assertEqual(note["title"], "Test Başlık")
        self.assertIn("python", note["tags"])

    def test_list_notes(self):
        db.add_note("Not 1", "İçerik 1", category="iş")
        db.add_note("Not 2", "İçerik 2", category="kişisel")
        db.add_note("Not 3", "İçerik 3", category="iş")
        self.assertEqual(len(db.list_notes()), 3)
        self.assertEqual(len(db.list_notes(category="iş")), 2)

    def test_update_note(self):
        note_id = db.add_note("Eski", "Eski içerik")
        db.update_note(note_id, title="Yeni", content="Yeni içerik")
        note = db.get_note(note_id)
        self.assertEqual(note["title"], "Yeni")

    def test_delete_note(self):
        note_id = db.add_note("Silinecek", "...")
        self.assertTrue(db.delete_note(note_id))
        self.assertIsNone(db.get_note(note_id))

    def test_delete_nonexistent(self):
        self.assertFalse(db.delete_note(9999))


class TestPin(BaseTestCase):

    def test_toggle_pin(self):
        note_id = db.add_note("Pin Test", "İçerik")
        self.assertTrue(db.toggle_pin(note_id))
        self.assertFalse(db.toggle_pin(note_id))

    def test_pinned_filter(self):
        id1 = db.add_note("Sabit", "...")
        db.add_note("Normal", "...")
        db.toggle_pin(id1)
        pinned = db.list_notes(pinned_only=True)
        self.assertEqual(len(pinned), 1)


class TestTags(BaseTestCase):

    def test_tag_assignment(self):
        note_id = db.add_note("Etiketli", "...", tags=["python", "proje"])
        note = db.get_note(note_id)
        self.assertEqual(set(note["tags"]), {"python", "proje"})

    def test_filter_by_tag(self):
        db.add_note("A", "...", tags=["web"])
        db.add_note("B", "...", tags=["mobile"])
        db.add_note("C", "...", tags=["web", "api"])
        self.assertEqual(len(db.list_notes(tag="web")), 2)

    def test_update_tags(self):
        note_id = db.add_note("T", "...", tags=["old"])
        db.update_note(note_id, tags=["new1", "new2"])
        note = db.get_note(note_id)
        self.assertNotIn("old", note["tags"])
        self.assertEqual(set(note["tags"]), {"new1", "new2"})


class TestSearch(BaseTestCase):

    def test_full_text_search(self):
        db.add_note("Python Dersleri", "Flask ve Django öğreniyorum")
        db.add_note("Yemek Tarifi", "Mercimek çorbası nasıl yapılır")
        results = db.search_notes("Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Dersleri")

    def test_search_in_content(self):
        db.add_note("Başlık", "Bu notta veritabanı optimizasyonu anlatılıyor")
        results = db.search_notes("veritabanı")
        self.assertEqual(len(results), 1)


class TestLinks(BaseTestCase):

    def test_link_and_unlink(self):
        id1 = db.add_note("Not A", "...")
        id2 = db.add_note("Not B", "...")
        self.assertTrue(db.link_notes(id1, id2))
        note = db.get_note(id1)
        self.assertIn(id2, [lnk["id"] for lnk in note["links"]])
        self.assertTrue(db.unlink_notes(id1, id2))
        note = db.get_note(id1)
        self.assertEqual(len(note["links"]), 0)


class TestExport(BaseTestCase):

    def test_export_markdown(self):
        db.add_note("Export MD", "Markdown denemesi", tags=["test"])
        filepath = os.path.join(tempfile.gettempdir(), "test_export.md")
        db.export_notes_markdown(filepath)
        with open(filepath, encoding="utf-8") as f:
            self.assertIn("Export MD", f.read())
        os.unlink(filepath)

    def test_export_json(self):
        import json
        db.add_note("Export JSON", "JSON denemesi")
        filepath = os.path.join(tempfile.gettempdir(), "test_export.json")
        db.export_notes_json(filepath)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data[0]["title"], "Export JSON")
        os.unlink(filepath)


class TestStats(BaseTestCase):

    def test_stats(self):
        db.add_note("A", "...", category="iş", tags=["x"])
        db.add_note("B", "...", category="kişisel")
        id3 = db.add_note("C", "...", category="iş")
        db.toggle_pin(id3)
        s = db.get_stats()
        self.assertEqual(s["total_notes"], 3)
        self.assertEqual(s["pinned_notes"], 1)
        self.assertEqual(s["categories"]["iş"], 2)


if __name__ == "__main__":
    unittest.main()
