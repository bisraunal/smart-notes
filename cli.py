"""Komut satırı arayüzü — Click + Rich ile renkli, kullanıcı dostu CLI."""

import click

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from smartnotes import database as db

if RICH_AVAILABLE:
    console = Console()
else:
    class _FallbackConsole:
        """Rich yüklü değilse düz metin çıktısı."""
        def print(self, text="", **kwargs):
            import re
            clean = re.sub(r"\[/?[^\]]*\]", "", str(text))
            print(clean)
    console = _FallbackConsole()


# ── Ana Grup ────────────────────────────────────────────────────

@click.group()
@click.version_option(version="1.0.0", prog_name="SmartNotes")
def cli():
    """📝 SmartNotes — Akıllı Not & Bilgi Yöneticisi

    Notlarını etiketle, ara, birbirine bağla ve organize et.
    """
    db.init_db()


# ── Not Ekleme ──────────────────────────────────────────────────

@cli.command()
@click.argument("title")
@click.option("-c", "--content", prompt="İçerik", help="Not içeriği")
@click.option("-t", "--tags", default="", help="Virgülle ayrılmış etiketler")
@click.option("-k", "--category", default="genel", help="Kategori (varsayılan: genel)")
def add(title, content, tags, category):
    """Yeni not ekle."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    note_id = db.add_note(title, content, category, tag_list)

    console.print(
        Panel(
            f"[bold green]✓ Not eklendi![/]\n\n"
            f"[bold]ID:[/] {note_id}\n"
            f"[bold]Başlık:[/] {title}\n"
            f"[bold]Kategori:[/] {category}\n"
            f"[bold]Etiketler:[/] {', '.join(tag_list) or '—'}",
            title="📝 Yeni Not",
            border_style="green",
        )
    )


# ── Not Listeleme ───────────────────────────────────────────────

@cli.command(name="list")
@click.option("-k", "--category", default=None, help="Kategoriye göre filtrele")
@click.option("-t", "--tag", default=None, help="Etikete göre filtrele")
@click.option("-p", "--pinned", is_flag=True, help="Sadece sabitlenmiş notlar")
def list_notes(category, tag, pinned):
    """Notları listele (filtreleme destekli)."""
    notes = db.list_notes(category=category, tag=tag, pinned_only=pinned)

    if not notes:
        console.print("[yellow]Hiç not bulunamadı.[/]")
        return

    table = Table(
        title="📋 Notlarım",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=5, justify="center")
    table.add_column("📌", width=3, justify="center")
    table.add_column("Başlık", style="bold white", min_width=20)
    table.add_column("Kategori", style="magenta", width=12)
    table.add_column("Etiketler", style="cyan", min_width=15)
    table.add_column("Güncelleme", style="dim", width=12)

    for n in notes:
        pin = "📌" if n["is_pinned"] else ""
        tags_str = ", ".join(n["tags"]) if n["tags"] else "—"
        updated = n["updated_at"][:10]
        table.add_row(str(n["id"]), pin, n["title"], n["category"], tags_str, updated)

    console.print(table)
    console.print(f"\n[dim]Toplam: {len(notes)} not[/]")


# ── Not Görüntüleme ────────────────────────────────────────────

@cli.command()
@click.argument("note_id", type=int)
def show(note_id):
    """Bir notu detaylı görüntüle."""
    note = db.get_note(note_id)
    if not note:
        console.print(f"[red]Hata: #{note_id} ID'li not bulunamadı.[/]")
        return

    pin = " 📌 Sabitlenmiş" if note["is_pinned"] else ""
    tags_str = ", ".join(f"[cyan]#{t}[/]" for t in note["tags"]) or "[dim]Etiket yok[/]"

    links_str = ""
    if note["links"]:
        links_str = "\n\n[bold]🔗 Bağlantılı Notlar:[/]\n" + "\n".join(
            f"  → #{lnk['id']} {lnk['title']}" for lnk in note["links"]
        )

    content_md = Markdown(note["content"])

    console.print(
        Panel(
            f"[bold]Kategori:[/] {note['category']}{pin}\n"
            f"[bold]Etiketler:[/] {tags_str}\n"
            f"[bold]Oluşturulma:[/] {note['created_at'][:16]}\n"
            f"[bold]Güncelleme:[/] {note['updated_at'][:16]}\n"
            f"\n{'─' * 40}\n",
            title=f"📝 #{note['id']} — {note['title']}",
            border_style="blue",
        )
    )
    console.print(content_md)
    if links_str:
        console.print(links_str)


# ── Not Düzenleme ───────────────────────────────────────────────

@cli.command()
@click.argument("note_id", type=int)
@click.option("--title", "-T", default=None, help="Yeni başlık")
@click.option("--content", "-c", default=None, help="Yeni içerik")
@click.option("--category", "-k", default=None, help="Yeni kategori")
@click.option("--tags", "-t", default=None, help="Yeni etiketler (virgülle ayrılmış)")
def edit(note_id, title, content, category, tags):
    """Var olan bir notu düzenle."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    success = db.update_note(note_id, title=title, content=content,
                             category=category, tags=tag_list)
    if success:
        console.print(f"[green]✓ Not #{note_id} güncellendi.[/]")
    else:
        console.print(f"[red]Hata: #{note_id} ID'li not bulunamadı.[/]")


# ── Not Silme ───────────────────────────────────────────────────

@cli.command()
@click.argument("note_id", type=int)
@click.confirmation_option(prompt="Bu notu silmek istediğinize emin misiniz?")
def delete(note_id):
    """Bir notu sil (onay gerekir)."""
    if db.delete_note(note_id):
        console.print(f"[green]✓ Not #{note_id} silindi.[/]")
    else:
        console.print(f"[red]Hata: #{note_id} ID'li not bulunamadı.[/]")


# ── Sabitleme ───────────────────────────────────────────────────

@cli.command()
@click.argument("note_id", type=int)
def pin(note_id):
    """Notu sabitle / sabitlemeyi kaldır."""
    result = db.toggle_pin(note_id)
    if result is None:
        console.print(f"[red]Hata: #{note_id} ID'li not bulunamadı.[/]")
    elif result:
        console.print(f"[green]📌 Not #{note_id} sabitlendi.[/]")
    else:
        console.print(f"[yellow]📌 Not #{note_id} sabitleme kaldırıldı.[/]")


# ── Arama ───────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
def search(query):
    """Notlarda tam metin araması yap."""
    results = db.search_notes(query)

    if not results:
        console.print(f"[yellow]'{query}' için sonuç bulunamadı.[/]")
        return

    table = Table(
        title=f"🔍 Arama: '{query}'",
        box=box.ROUNDED,
        title_style="bold yellow",
    )
    table.add_column("ID", style="dim", width=5, justify="center")
    table.add_column("Başlık", style="bold white", min_width=25)
    table.add_column("Etiketler", style="cyan")
    table.add_column("Önizleme", style="dim", max_width=40)

    for n in results:
        tags_str = ", ".join(n["tags"]) if n["tags"] else "—"
        preview = n.get("hl_content", n["content"])[:60] + "..."
        # >>> <<< işaretlerini renklendir
        preview = preview.replace(">>>", "[bold yellow]").replace("<<<", "[/]")
        table.add_row(str(n["id"]), n["title"], tags_str, preview)

    console.print(table)
    console.print(f"\n[dim]{len(results)} sonuç bulundu.[/]")


# ── Not Bağlantıları ───────────────────────────────────────────

@cli.command()
@click.argument("source_id", type=int)
@click.argument("target_id", type=int)
def link(source_id, target_id):
    """İki notu birbirine bağla."""
    if source_id == target_id:
        console.print("[red]Bir notu kendisine bağlayamazsınız.[/]")
        return

    if db.link_notes(source_id, target_id):
        console.print(
            f"[green]🔗 Not #{source_id} ↔ #{target_id} bağlantısı oluşturuldu.[/]"
        )
    else:
        console.print("[red]Bağlantı oluşturulamadı (notlar mevcut mi?).[/]")


@cli.command()
@click.argument("source_id", type=int)
@click.argument("target_id", type=int)
def unlink(source_id, target_id):
    """İki not arasındaki bağlantıyı kaldır."""
    if db.unlink_notes(source_id, target_id):
        console.print(
            f"[yellow]🔗 Not #{source_id} ↔ #{target_id} bağlantısı kaldırıldı.[/]"
        )
    else:
        console.print("[red]Bağlantı bulunamadı.[/]")


# ── Etiketler ───────────────────────────────────────────────────

@cli.command()
def tags():
    """Tüm etiketleri listele."""
    all_tags = db.list_all_tags()
    if not all_tags:
        console.print("[yellow]Henüz etiket yok.[/]")
        return

    table = Table(title="🏷️  Etiketler", box=box.SIMPLE_HEAVY)
    table.add_column("Etiket", style="cyan bold")
    table.add_column("Not Sayısı", justify="center")

    for t in all_tags:
        bar = "█" * t["count"]
        table.add_row(f"#{t['name']}", f"{t['count']}  {bar}")

    console.print(table)


# ── İstatistikler ───────────────────────────────────────────────

@cli.command()
def stats():
    """Not istatistiklerini göster."""
    s = db.get_stats()

    cat_lines = "\n".join(
        f"  • {cat}: {cnt}" for cat, cnt in s["categories"].items()
    ) or "  Henüz kategori yok"

    console.print(
        Panel(
            f"[bold]📊 Toplam Not:[/]       {s['total_notes']}\n"
            f"[bold]📌 Sabitlenmiş:[/]      {s['pinned_notes']}\n"
            f"[bold]🏷️  Etiket Sayısı:[/]   {s['total_tags']}\n"
            f"[bold]🔗 Bağlantı Sayısı:[/]  {s['total_links']}\n\n"
            f"[bold]Kategoriler:[/]\n{cat_lines}",
            title="📈 SmartNotes İstatistikleri",
            border_style="green",
        )
    )


# ── Dışa Aktarım ───────────────────────────────────────────────

@cli.command()
@click.option("--format", "-f", "fmt", type=click.Choice(["md", "json"]),
              default="md", help="Çıktı formatı")
@click.option("--output", "-o", default=None, help="Çıktı dosya yolu")
def export(fmt, output):
    """Notları Markdown veya JSON olarak dışa aktar."""
    if output is None:
        output = f"smartnotes_export.{fmt}"

    if fmt == "md":
        db.export_notes_markdown(output)
    else:
        db.export_notes_json(output)

    console.print(f"[green]✓ Notlar '{output}' dosyasına aktarıldı.[/]")


# ── Giriş Noktası ──────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
