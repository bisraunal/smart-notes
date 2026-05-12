#  SmartNotes — Akıllı Not & Bilgi Yöneticisi

> Notlarını etiketle, ara, birbirine bağla ve düzenli tut. Terminal tabanlı, hafif ve hızlı bir kişisel bilgi yönetim sistemi.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

##  Problem

Günlük hayatta aldığımız notlar farklı uygulamalara, kağıtlara ve dosyalara dağılır. Bir bilgiyi ararken "nereye yazmıştım?" diye vakit kaybederiz. Notlar arasında bağlantı kurmak, etiketlemek ve hızlıca aramak için basit ama güçlü bir araca ihtiyaç vardır.

##  Çözüm

**SmartNotes** terminal üzerinden çalışan, SQLite tabanlı bir kişisel bilgi yönetim aracıdır:

- **Tam metin araması** ile notlarını anında bul (FTS5)
- **Etiket sistemi** ile notları kategorize et
- **Not bağlantıları** ile ilişkili bilgileri birbirine bağla
- **Sabitleme** ile önemli notları öne çıkar
- **Dışa aktarım** ile notlarını Markdown veya JSON olarak yedekle

## Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/yourusername/smart-notes.git
cd smart-notes

# Sanal ortam oluştur (önerilir)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Paketi kur
pip install -e .
```

##  Kullanım

### Not Ekleme
```bash
smartnotes add "Python Dersleri" -c "Flask framework öğrenmeye başladım" -t "python,web,öğrenme" -k eğitim
```

### Notları Listeleme
```bash
smartnotes list                    # Tüm notlar
smartnotes list -k eğitim         # Kategoriye göre
smartnotes list -t python          # Etikete göre
smartnotes list -p                 # Sadece sabitlenmiş
```

### Not Görüntüleme
```bash
smartnotes show 1                  # ID ile detaylı görüntüle
```

### Arama
```bash
smartnotes search "Flask"          # Tam metin araması
```

### Not Düzenleme
```bash
smartnotes edit 1 -T "Yeni Başlık" -t "yeni,etiketler"
```

### Sabitleme
```bash
smartnotes pin 1                   # Sabitle / kaldır
```

### Notları Bağlama
```bash
smartnotes link 1 3                # Not #1 ve #3'ü bağla
smartnotes unlink 1 3              # Bağlantıyı kaldır
```

### Etiketler & İstatistikler
```bash
smartnotes tags                    # Tüm etiketleri listele
smartnotes stats                   # Genel istatistikler
```

### Dışa Aktarım
```bash
smartnotes export -f md            # Markdown olarak
smartnotes export -f json -o backup.json  # JSON olarak
```

##  Proje Yapısı

```
smart-notes/
├── smartnotes/
│   ├── __init__.py       # Paket bilgisi
│   ├── cli.py            # Click CLI komutları + Rich arayüz
│   └── database.py       # SQLite CRUD, FTS5 arama, etiket & bağlantı yönetimi
├── tests/
│   └── test_notes.py     # Pytest birim testleri
├── setup.py              # Paket kurulum dosyası
├── requirements.txt      # Bağımlılıklar
├── .gitignore
├── LICENSE
└── README.md
```

##  Teknik Detaylar

| Bileşen          | Teknoloji                  |
|-------------------|----------------------------|
| Dil              | Python 3.10+               |
| Veritabanı       | SQLite3 + FTS5             |
| CLI Framework    | Click                      |
| Terminal UI      | Rich                       |
| Test Framework   | Pytest                     |

**Veritabanı Şeması:**
- `notes` — Başlık, içerik, kategori, pin durumu, tarihler
- `tags` — Etiket isimleri (unique)
- `note_tags` — Not-etiket ilişkisi (many-to-many)
- `note_links` — Notlar arası bağlantılar (many-to-many)
- `notes_fts` — FTS5 tam metin arama indeksi (otomatik trigger ile senkron)

## Testler

```bash
pytest tests/ -v
```

Testler geçici veritabanı kullanır, gerçek verileriniz etkilenmez.

ın

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.
