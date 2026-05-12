"""Veritabanı katmanı - SQLite ile not saklama, etiketleme ve bağlantı yönetimi."""

import sqlite3
import os
from datetime import datetime
from typing import Optional


DB_PATH = os.path.join(os.path.expanduser("~"), ".smartnotes", "notes.db")


def get_connection() -> sqlite3.Connection:
    """Veritabanı bağlantısı oluşturur, yoksa dizini ve tabloları yaratır."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Tabloları oluşturur (ilk çalıştırmada)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            content     TEXT    NOT NULL DEFAULT '',
            category    TEXT    DEFAULT 'genel',
            is_pinned   INTEGER DEFAULT 0,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT    NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id  INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS note_links (
            source_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            PRIMARY KEY (source_id, target_id),
            FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
            USING fts5(title, content, content=notes, content_rowid=id);

        -- Triggers: FTS indeksini senkron tut
        CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
            INSERT INTO notes_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
        END;

        CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
            INSERT INTO notes_fts(notes_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
            INSERT INTO notes_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END;
    """)

    conn.commit()
    conn.close()


# ── CRUD İşlemleri ──────────────────────────────────────────────

def add_note(title: str, content: str, category: str = "genel",
             tags: Optional[list[str]] = None) -> int:
    """Yeni not ekler, etiketleri bağlar. Oluşturulan not ID'sini döner."""
    conn = get_connection()
    now = datetime.now().isoformat()

    cursor = conn.execute(
        "INSERT INTO notes (title, content, category, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, content, category, now, now),
    )
    note_id = cursor.lastrowid

    if tags:
        _attach_tags(conn, note_id, tags)

    conn.commit()
    conn.close()
    return note_id


def get_note(note_id: int) -> Optional[dict]:
    """Tek bir notu etiketleri ve bağlantılarıyla birlikte döner."""
    conn = get_connection()

    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        conn.close()
        return None

    note = dict(row)
    note["tags"] = _get_tags_for_note(conn, note_id)
    note["links"] = _get_links_for_note(conn, note_id)

    conn.close()
    return note


def list_notes(category: Optional[str] = None, tag: Optional[str] = None,
               pinned_only: bool = False) -> list[dict]:
    """Notları filtrelerle listeler."""
    conn = get_connection()
    query = "SELECT DISTINCT n.* FROM notes n"
    joins, conditions, params = [], [], []

    if tag:
        joins.append("JOIN note_tags nt ON nt.note_id = n.id "
                      "JOIN tags t ON t.id = nt.tag_id")
        conditions.append("t.name = ?")
        params.append(tag)

    if category:
        conditions.append("n.category = ?")
        params.append(category)

    if pinned_only:
        conditions.append("n.is_pinned = 1")

    sql = query + " " + " ".join(joins)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY n.is_pinned DESC, n.updated_at DESC"

    rows = conn.execute(sql, params).fetchall()
    notes = []
    for r in rows:
        d = dict(r)
        d["tags"] = _get_tags_for_note(conn, d["id"])
        notes.append(d)

    conn.close()
    return notes


def update_note(note_id: int, title: Optional[str] = None,
                content: Optional[str] = None, category: Optional[str] = None,
                tags: Optional[list[str]] = None) -> bool:
    """Notu günceller. Değişen alanları parametre olarak ver."""
    conn = get_connection()
    now = datetime.now().isoformat()

    fields, params = ["updated_at = ?"], [now]
    if title is not None:
        fields.append("title = ?"); params.append(title)
    if content is not None:
        fields.append("content = ?"); params.append(content)
    if category is not None:
        fields.append("category = ?"); params.append(category)

    params.append(note_id)
    result = conn.execute(
        f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", params
    )

    if tags is not None:
        conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
        _attach_tags(conn, note_id, tags)

    conn.commit()
    updated = result.rowcount > 0
    conn.close()
    return updated


def delete_note(note_id: int) -> bool:
    """Notu siler."""
    conn = get_connection()
    result = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


def toggle_pin(note_id: int) -> Optional[bool]:
    """Notun pin durumunu tersine çevirir, yeni durumu döner."""
    conn = get_connection()
    row = conn.execute("SELECT is_pinned FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        conn.close()
        return None
    new_val = 0 if row["is_pinned"] else 1
    conn.execute("UPDATE notes SET is_pinned = ? WHERE id = ?", (new_val, note_id))
    conn.commit()
    conn.close()
    return bool(new_val)


# ── Arama ───────────────────────────────────────────────────────

def search_notes(query: str) -> list[dict]:
    """FTS5 tam metin araması yapar."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT n.*, highlight(notes_fts, 0, '>>>', '<<<') AS hl_title, "
        "       highlight(notes_fts, 1, '>>>', '<<<') AS hl_content "
        "FROM notes_fts fts "
        "JOIN notes n ON n.id = fts.rowid "
        "WHERE notes_fts MATCH ? "
        "ORDER BY rank",
        (query,),
    ).fetchall()

    notes = []
    for r in rows:
        d = dict(r)
        d["tags"] = _get_tags_for_note(conn, d["id"])
        notes.append(d)

    conn.close()
    return notes


# ── Bağlantılar (Not Arası Link) ───────────────────────────────

def link_notes(source_id: int, target_id: int) -> bool:
    """İki notu birbirine bağlar."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO note_links (source_id, target_id) VALUES (?, ?)",
            (source_id, target_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def unlink_notes(source_id: int, target_id: int) -> bool:
    """İki not arasındaki bağlantıyı kaldırır."""
    conn = get_connection()
    result = conn.execute(
        "DELETE FROM note_links WHERE source_id = ? AND target_id = ?",
        (source_id, target_id),
    )
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


# ── Etiketler ───────────────────────────────────────────────────

def list_all_tags() -> list[dict]:
    """Tüm etiketleri kullanım sayısıyla birlikte döner."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT t.name, COUNT(nt.note_id) AS count "
        "FROM tags t LEFT JOIN note_tags nt ON nt.tag_id = t.id "
        "GROUP BY t.id ORDER BY count DESC"
    ).fetchall()
    tags = [dict(r) for r in rows]
    conn.close()
    return tags


# ── İstatistikler ───────────────────────────────────────────────

def get_stats() -> dict:
    """Genel istatistikleri döner."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM notes").fetchone()["c"]
    pinned = conn.execute("SELECT COUNT(*) AS c FROM notes WHERE is_pinned=1").fetchone()["c"]
    tag_count = conn.execute("SELECT COUNT(*) AS c FROM tags").fetchone()["c"]
    link_count = conn.execute("SELECT COUNT(*) AS c FROM note_links").fetchone()["c"]

    cats = conn.execute(
        "SELECT category, COUNT(*) AS c FROM notes GROUP BY category ORDER BY c DESC"
    ).fetchall()

    conn.close()
    return {
        "total_notes": total,
        "pinned_notes": pinned,
        "total_tags": tag_count,
        "total_links": link_count,
        "categories": {r["category"]: r["c"] for r in cats},
    }


# ── Dışa Aktarım ───────────────────────────────────────────────

def export_notes_markdown(filepath: str):
    """Tüm notları tek bir Markdown dosyasına aktarır."""
    notes = list_notes()
    lines = ["# SmartNotes — Dışa Aktarım\n"]
    for n in notes:
        pin = " 📌" if n["is_pinned"] else ""
        tags_str = ", ".join(f"`{t}`" for t in n["tags"]) if n["tags"] else "—"
        lines.append(f"## {n['title']}{pin}\n")
        lines.append(f"**Kategori:** {n['category']}  |  **Etiketler:** {tags_str}")
        lines.append(f"**Oluşturulma:** {n['created_at'][:16]}\n")
        lines.append(n["content"] + "\n")
        lines.append("---\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def export_notes_json(filepath: str):
    """Tüm notları JSON dosyasına aktarır."""
    import json
    notes = list_notes()
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


# ── Yardımcı Fonksiyonlar ──────────────────────────────────────

def _attach_tags(conn: sqlite3.Connection, note_id: int, tags: list[str]):
    for tag_name in tags:
        tag_name = tag_name.strip().lower()
        if not tag_name:
            continue
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
        tag_id = conn.execute(
            "SELECT id FROM tags WHERE name = ?", (tag_name,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO note_tags (note_id, tag_id) VALUES (?, ?)",
            (note_id, tag_id),
        )


def _get_tags_for_note(conn: sqlite3.Connection, note_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT t.name FROM tags t "
        "JOIN note_tags nt ON nt.tag_id = t.id "
        "WHERE nt.note_id = ?",
        (note_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _get_links_for_note(conn: sqlite3.Connection, note_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT n.id, n.title FROM notes n "
        "JOIN note_links nl ON (nl.target_id = n.id AND nl.source_id = ?) "
        "   OR (nl.source_id = n.id AND nl.target_id = ?)",
        (note_id, note_id),
    ).fetchall()
    return [{"id": r["id"], "title": r["title"]} for r in rows]
