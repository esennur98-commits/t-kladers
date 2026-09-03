#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ortak altyapı: kriter dosyası, Türkçe metin yardımcıları, CSV okuma/yazma.

Hiçbir dış bağımlılık yok — sadece Python standart kütüphanesi.
"""
import csv
import json
import os
import re
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERI = os.environ.get("KESIF_VERI", os.path.join(KOK, "veri"))
KRITER_YOLU = os.environ.get("KESIF_KRITER", os.path.join(KOK, "kriterler.json"))

# Aday havuzu CSV kolonları (sıra sabittir; yeni kolon sona eklenir)
ADAY_ALANLARI = [
    "kullanici_adi", "ad", "takipci", "takip", "gonderi_sayisi", "biyografi",
    "ort_begeni", "ort_yorum", "etkilesim_orani", "video_orani", "sponsor_orani",
    "son_paylasim", "gonderi_30gun", "son_basliklar",
    "kaynak", "ilk_gorulme", "son_guncelleme", "durum", "puan", "not",
]

# İletişim geçmişi CSV kolonları
GECMIS_ALANLARI = [
    "kullanici_adi", "ad", "ilk_mesaj", "son_mesaj", "bizim_mesaj", "onlarin_mesaj",
    "cevap_verdi", "ortak_video", "kaynak", "not",
]

DURUMLAR = ("havuz", "elendi", "secildi", "mesaj_atildi", "cevap_verdi", "ortak_video")


# --------------------------------------------------------------- kriterler
_kriter_onbellek = {}


def kriterler(yol=None):
    """kriterler.json'u oku (bir kez okur, önbelleğe alır)."""
    yol = yol or KRITER_YOLU
    if yol not in _kriter_onbellek:
        with open(yol, encoding="utf-8") as f:
            _kriter_onbellek[yol] = json.load(f)
    return _kriter_onbellek[yol]


# ---------------------------------------------------------- Türkçe metin
_KUCUK = str.maketrans("IİĞÜŞÖÇ", "ıiğüşöç")


def kucuk(s):
    """Türkçe duyarlı küçük harfe çevirme (I→ı, İ→i)."""
    return (s or "").translate(_KUCUK).lower()


def kullanici_normalize(s):
    """@ ve boşlukları at, küçük harfe indir, linkten kullanıcı adı çıkar."""
    s = (s or "").strip()
    m = re.search(r"instagram\.com/([A-Za-z0-9._]+)", s)
    if m:
        s = m.group(1)
    s = s.lstrip("@").strip().strip("/")
    return kucuk(s)


def mojibake_duzelt(s):
    """
    Instagram JSON export'u Türkçe karakterleri latin-1 kaçışlarıyla yazar
    ("Ã§" gibi). Düzeltilebiliyorsa düzelt, olmuyorsa dokunma.
    """
    if not s:
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def kelime_sayisi(metin, kelimeler):
    """metin içinde kaç farklı anahtar kelime geçiyor + hangileri."""
    m = kucuk(metin)
    bulunan = [k for k in kelimeler if kucuk(k) in m]
    return len(bulunan), bulunan


# ------------------------------------------------------------------ tarih
def bugun():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def tarih_oku(s):
    """ISO benzeri tarihleri datetime'a çevir; olmazsa None."""
    if not s:
        return None
    s = str(s).strip().replace("Z", "+0000")
    for kalip in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            d = datetime.strptime(s, kalip)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def gun_farki(s, referans=None):
    """Verilen tarihten bugüne kaç gün geçmiş (bilinmiyorsa None)."""
    d = tarih_oku(s)
    if not d:
        return None
    ref = referans or datetime.now(timezone.utc)
    return max(0, (ref - d).days)


# -------------------------------------------------------------------- CSV
def veri_yolu(*parcalar):
    yol = os.path.join(VERI, *parcalar)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    return yol


def csv_oku(yol):
    """CSV'yi sözlük listesi olarak oku; dosya yoksa boş liste."""
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def csv_yaz(yol, kayitlar, alanlar):
    os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        y = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        y.writeheader()
        for k in kayitlar:
            y.writerow({a: k.get(a, "") for a in alanlar})
    return yol


def sayi(x, varsayilan=0.0):
    """CSV'den gelen metni sayıya çevir (virgül/nokta, boş, None toleranslı)."""
    if x is None or x == "":
        return varsayilan
    try:
        return float(str(x).replace(",", ".").replace(" ", ""))
    except ValueError:
        return varsayilan


# ------------------------------------------------------- havuz & geçmiş
def havuz_oku():
    return csv_oku(veri_yolu("havuz.csv"))


def havuz_yaz(kayitlar):
    return csv_yaz(veri_yolu("havuz.csv"), kayitlar, ADAY_ALANLARI)


def gecmis_oku():
    return csv_oku(veri_yolu("iletisim_gecmisi.csv"))


def gecmis_yaz(kayitlar):
    return csv_yaz(veri_yolu("iletisim_gecmisi.csv"), kayitlar, GECMIS_ALANLARI)


def ad_normalize(s):
    """Görünen adı karşılaştırma için sadeleştir: küçük harf, emoji/noktalama yok."""
    s = kucuk(s)
    s = re.sub(r"[^a-z0-9çğıöşü ]", " ", s)
    return " ".join(s.split())


def ad_katla(s):
    """Görünen adı en kaba biçime indirger: süslü unicode ve aksan atılır,
    boşluk/noktalama silinir ('𝐆𝐨̈𝐤𝐭𝐮𝐠 | Oyun' → 'goktugoyun')."""
    import unicodedata
    s = unicodedata.normalize("NFKD", kucuk(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ç", "c").replace("ö", "o").replace("ü", "u")
    return re.sub(r"[^a-z0-9]", "", s)


def dokunulmaz_adlar():
    """
    Daha önce yazdıklarımızın GÖRÜNEN adları. Instagram'ın HTML export'u
    sohbetleri kullanıcı adıyla değil görünen adla adlandırır; bu yüzden
    eleme yalnızca kullanıcı adına bakarsa yazılmış kişiler yeniden listeye
    girer. Tek kelimelik yaygın adlar (Merve, Eda…) belirsizdir; onlar ayrı
    kümede döner.
    """
    kesin, belirsiz = set(), set()
    for k in gecmis_oku():
        ad = ad_normalize(k.get("ad", ""))
        if not ad:
            continue
        hedef = kesin if len(ad.split()) >= 2 or len(ad) >= 9 else belirsiz
        hedef.add(ad)
        hedef.add(ad_katla(k.get("ad", "")))
    return kesin, belirsiz


def dokunulmaz_kumesi():
    """
    Bir daha mesaj atılmayacak / havuza girmeyecek kullanıcılar:
    daha önce mesaj attıklarımız, ortak video yaptıklarımız ve kara liste.
    """
    kume = {kullanici_normalize(k.get("kullanici_adi")) for k in gecmis_oku()}
    for satir in _satirlar(veri_yolu("kara_liste.txt")):
        kume.add(kullanici_normalize(satir))
    for satir in _satirlar(veri_yolu("ortaklar.txt")):
        kume.add(kullanici_normalize(satir))
    kume.discard("")
    return kume


def _satirlar(yol):
    """Metin dosyasını satır satır oku; # yorum satırlarını ve boşları at."""
    if not os.path.exists(yol):
        return []
    with open(yol, encoding="utf-8") as f:
        return [s.strip() for s in f if s.strip() and not s.strip().startswith("#")]


satirlar = _satirlar
