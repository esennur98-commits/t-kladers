#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram "Bilgilerini İndir" (JSON) paketinden DM geçmişini çıkarır.

Ne yapar:
  * Kime, ne zaman yazmışız, cevap gelmiş mi — hepsini tabloya döker.
  * Cevap oranını ve "hangi açılış cümlesi daha çok cevap almış"ı hesaplar.
  * Bir daha yazmamak için dokunulmaz listesini (iletisim_gecmisi.csv) üretir.

Şifre gerekmez: paketi Instagram uygulamasından sen indirirsin, biz sadece
kendi verini okuruz.
"""
import json
import os
import re
from html.parser import HTMLParser
from collections import Counter, defaultdict
from datetime import datetime, timezone

from . import ortak

# Bir işbirliğinin gerçekleştiğine işaret eden kelimeler (sohbetin içinde)
ISBIRLIGI_IZLERI = [
    "kargo", "adres", "gönderdik", "gönderdim", "elime ulaştı", "ulaştı",
    "paylaştım", "story", "reels", "video hazır", "yükledim", "etiketledim",
    "çok beğendi", "kod", "link",
]


def _mesaj_dosyalari(kok):
    """Export içindeki tüm inbox/message_*.json dosyalarını bul."""
    bulunan = []
    for dizin, _, dosyalar in os.walk(kok):
        if "inbox" not in dizin.replace("\\", "/").split("/"):
            continue
        for d in dosyalar:
            if re.fullmatch(r"message_\d+\.(json|html)", d):
                bulunan.append(os.path.join(dizin, d))
    return sorted(bulunan)


def _kullanici_adi_cikar(dosya_yolu, baslik):
    """
    Klasör adı "kullaniciadi_17843968..." biçimindedir; JSON export'ta nokta/alt
    çizgi korunur, HTML export'ta atılır. Başlık (görünen ad) noktalarından
    arındırılınca klasör adıyla örtüşüyorsa başlık gerçek kullanıcı adıdır;
    örtüşmüyorsa klasör adı (noktasız, yaklaşık) kullanılır.
    """
    klasor = os.path.basename(os.path.dirname(dosya_yolu))
    slug = ortak.kucuk(re.sub(r"_\d{6,}$", "", klasor))
    b = ortak.kucuk((baslik or "").strip())
    if b and re.fullmatch(r"[a-z0-9._]{2,30}", b) and re.sub(r"[._]", "", b) == slug:
        return b
    if slug and re.fullmatch(r"[a-z0-9._]+", slug):
        return slug
    return ortak.kullanici_normalize(re.sub(r"[^A-Za-z0-9._]", "", baslik or ""))


SILINMIS = {"instagramkullanicisi", "instagramuser", "instagram kullanıcısı"}


# ------------------------------------------------------------ HTML biçimi
_AYLAR = {"oca": 1, "şub": 2, "sub": 2, "mar": 3, "nis": 4, "may": 5, "haz": 6,
          "tem": 7, "ağu": 8, "agu": 8, "eyl": 9, "eki": 10, "kas": 11, "ara": 12,
          "jan": 1, "feb": 2, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
          "oct": 10, "nov": 11, "dec": 12}
_VOID = {"img", "br", "hr", "input", "meta", "link", "source"}


def _html_tarih(metin):
    """'Haz 18, 2026 6:57 am' → datetime (UTC varsayılır)."""
    m = re.match(r"\s*([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d+),\s+(\d{4})\s+(\d+):(\d+)\s*(am|pm)?",
                 metin or "", re.I)
    if not m:
        return None
    ay = _AYLAR.get(ortak.kucuk(m.group(1))[:3])
    if not ay:
        return None
    saat = int(m.group(4)) % 12
    if (m.group(6) or "").lower() == "pm":
        saat += 12
    try:
        return datetime(int(m.group(3)), ay, int(m.group(2)), saat, int(m.group(5)),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


class _IGHtml(HTMLParser):
    """Instagram HTML export'undaki mesaj kutularını (_a6-g) toplar."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.yigin = []          # [(tag, alan)]  alan: 'h' gönderen, 'p' içerik, 'o' zaman, 'x' atla
        self.baslik = None
        self.basliklar = []
        self.mesajlar = []
        self.suanki = None
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            return
        cls = dict(attrs).get("class", "") or ""
        alan = None
        if "_a6-g" in cls:
            self.suanki = {"kim": [], "metin": [], "zaman": []}
            alan = "g"
        elif "_a6-h" in cls:
            alan = "h"
        elif "_a6-p" in cls:
            alan = "p"
        elif "_a6-o" in cls:
            alan = "o"
        elif "_a6-q" in cls:     # tepkiler listesi — içerik değil
            alan = "x"
        if tag == "h1":
            self._h1 = True
        self.yigin.append((tag, alan))

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if tag == "h1":
            self._h1 = False
        while self.yigin:
            t, alan = self.yigin.pop()
            if alan == "g" and self.suanki is not None:
                m = self.suanki
                self.mesajlar.append({
                    "kim": " ".join(m["kim"]).strip(),
                    "metin": " ".join(x for x in m["metin"] if x).strip(),
                    "zaman": _html_tarih(" ".join(m["zaman"])),
                })
                self.suanki = None
            if t == tag:
                break

    def handle_data(self, veri):
        veri = veri.strip()
        if not veri:
            return
        if self._h1 and self.baslik is None:
            self.baslik = veri
        if self.suanki is None:
            return
        for _, alan in reversed(self.yigin):
            if alan == "x":
                return
            if alan == "h":
                self.suanki["kim"].append(veri); return
            if alan == "p":
                self.suanki["metin"].append(veri); return
            if alan == "o":
                self.suanki["zaman"].append(veri); return
            if alan == "g":
                return


def _html_sohbet_oku(yol):
    """Tek bir message_N.html dosyasını sözlüğe çevir (grup ise None)."""
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            p = _IGHtml()
            p.feed(f.read())
    except OSError:
        return None
    mesajlar = [m for m in p.mesajlar if m["zaman"] and m["kim"]]
    if not mesajlar:
        return None
    katilimcilar = sorted({m["kim"] for m in mesajlar})
    if len(katilimcilar) > 2:
        return None
    mesajlar.sort(key=lambda m: m["zaman"])
    baslik = p.baslik or katilimcilar[0]
    return {
        "kullanici_adi": _kullanici_adi_cikar(yol, baslik),
        "ad": baslik,
        "katilimcilar": katilimcilar,
        "mesajlar": mesajlar,
    }


def _sohbetleri_oku(kok):
    """Her ikili sohbeti (thread) normalize edilmiş sözlük olarak döndür."""
    sohbetler = []
    for yol in _mesaj_dosyalari(kok):
        if yol.endswith(".html"):
            s = _html_sohbet_oku(yol)
            if s:
                sohbetler.append(s)
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                ham = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        katilimcilar = [ortak.mojibake_duzelt(k.get("name", ""))
                        for k in ham.get("participants", [])]
        if len(katilimcilar) != 2:
            continue  # grup sohbetlerini atla
        baslik = ortak.mojibake_duzelt(ham.get("title", "")) or katilimcilar[0]
        mesajlar = []
        for m in ham.get("messages", []):
            mesajlar.append({
                "kim": ortak.mojibake_duzelt(m.get("sender_name", "")),
                "zaman": datetime.fromtimestamp(m.get("timestamp_ms", 0) / 1000, timezone.utc),
                "metin": ortak.mojibake_duzelt(m.get("content", "") or ""),
            })
        if not mesajlar:
            continue
        mesajlar.sort(key=lambda m: m["zaman"])
        sohbetler.append({
            "kullanici_adi": _kullanici_adi_cikar(yol, baslik),
            "ad": baslik,
            "katilimcilar": katilimcilar,
            "mesajlar": mesajlar,
        })
    return sohbetler


def _biz_kimiz(sohbetler, elle=None):
    """Kendi hesabımızın görünen adı: tüm sohbetlerde ortak olan gönderici."""
    if elle:
        return elle
    sayac = Counter()
    for s in sohbetler:
        for kim in {m["kim"] for m in s["mesajlar"]}:
            sayac[kim] += 1
    return sayac.most_common(1)[0][0] if sayac else ""


def analiz_et(export_kok, ben=None):
    """Export'u oku, sohbet başına özet çıkar."""
    sohbetler = _sohbetleri_oku(export_kok)
    if not sohbetler:
        return {"ben": "", "kayitlar": [], "sohbetler": []}
    ben = _biz_kimiz(sohbetler, ben)

    kayitlar = []
    for s in sohbetler:
        bizim = [m for m in s["mesajlar"] if m["kim"] == ben]
        onlarin = [m for m in s["mesajlar"] if m["kim"] != ben]
        if not bizim or s["kullanici_adi"] in SILINMIS:
            continue  # biz hiç yazmamışız ya da hesap silinmiş
        ilk = s["mesajlar"][0]
        reklam_yaniti = bool(re.search(r"replied to an ad|reklam(a|ınıza) yanıt", ilk["metin"], re.I))
        biz_basladik = ilk["kim"] == ben and not reklam_yaniti
        ilk_bizim = bizim[0]
        # Açılış = karşı taraf ilk kez cevap verene kadar attığımız mesajların tümü
        # (şablonlar çoğu zaman 3-4 ayrı balon; aynı dakikada sıralama güvenilmez)
        ilk_cevap = onlarin[0]["zaman"] if onlarin else None
        acilis = " ".join(m["metin"] for m in bizim
                          if ilk_cevap is None or m["zaman"] <= ilk_cevap)
        # İşbirliği izi yalnızca KARŞI TARAFIN yazdıklarında aranır; kendi
        # şablonumuzdaki "link / indirim kodu" kelimeleri sayılmaz.
        onlarin_metin = " ".join(m["metin"] for m in onlarin)
        iz_sayisi, _ = ortak.kelime_sayisi(onlarin_metin, ISBIRLIGI_IZLERI)
        kayitlar.append({
            "kullanici_adi": s["kullanici_adi"],
            "ad": s["ad"],
            "ilk_mesaj": ilk_bizim["zaman"].strftime("%Y-%m-%d"),
            "son_mesaj": s["mesajlar"][-1]["zaman"].strftime("%Y-%m-%d"),
            "bizim_mesaj": len(bizim),
            "onlarin_mesaj": len(onlarin),
            "cevap_verdi": "evet" if onlarin else "hayır",
            "ortak_video": "",
            "kaynak": "dm_export" if biz_basladik else "gelen_kutusu",
            "not": f"isbirligi_izi={iz_sayisi}",
            "_biz_basladik": biz_basladik,
            "_ilk_metin": acilis or ilk_bizim["metin"],
            "_gun": ilk_bizim["zaman"].weekday(),
            "_saat": ilk_bizim["zaman"].hour,
            "_iz": iz_sayisi,
        })
    return {"ben": ben, "kayitlar": kayitlar, "sohbetler": sohbetler}


# ------------------------------------------------------------------ rapor
_DURAK = set("""bir ve ile için de da bu şu o çok en gibi ama ki mi mı mu mü ben biz siz
sen çünkü ise her daha sonra kadar var yok olarak diye ya veya bize size sizin bizim
merhaba selam nasılsınız iyi günler""".split())


def _kelimeler(metin):
    return [k for k in re.findall(r"[a-zçğıöşü]{4,}", ortak.kucuk(metin)) if k not in _DURAK]


def _sablon_imzalari(kayitlar, benzerlik=0.5):
    """
    Her açılış mesajını bir şablon ailesine atar. Şablonlar çoğu zaman aynı
    dakikada atılan 3-4 balondur, export'ta sıraları karışır ve içine isim gibi
    kişisel kelimeler girer. Yöntem: kişisel (nadir) kelimeler atılır, kalan
    kelime kümesi mevcut ailelerin temsilcisiyle Jaccard benzerliğine göre
    eşleştirilir; yeterince benzeyen yoksa yeni aile açılır.
    """
    kelimeler = [set(re.findall(r"[a-zçğıöşü]{6,}", ortak.kucuk(k["_ilk_metin"])))
                 for k in kayitlar]
    sıklık = Counter(w for kume in kelimeler for w in kume)
    esik = max(3, len(kayitlar) // 100)          # %1'den az geçen kelime kişiseldir
    temsilciler = []                              # [(aile_no, kelime kümesi)]
    imzalar = []
    for kume in kelimeler:
        kume = {w for w in kume if sıklık[w] >= esik}
        en_iyi, en_iyi_j = None, 0.0
        for no, temsilci in temsilciler:
            birlesim = len(kume | temsilci)
            j = len(kume & temsilci) / birlesim if birlesim else 0.0
            if j > en_iyi_j:
                en_iyi, en_iyi_j = no, j
        if en_iyi is None or en_iyi_j < benzerlik:
            en_iyi = len(temsilciler)
            temsilciler.append((en_iyi, kume))
        imzalar.append(en_iyi)
    return imzalar


def rapor_uret(sonuc):
    """Cevap oranı, aylık dağılım ve açılış şablonu analizini metin olarak üret."""
    kayitlar = sonuc["kayitlar"]
    if not kayitlar:
        return "DM export'unda bizim yazdığımız sohbet bulunamadı."

    giden = [k for k in kayitlar if k.get("_biz_basladik", True)]
    gelen = [k for k in kayitlar if not k.get("_biz_basladik", True)]
    cevaplı = [k for k in giden if k["cevap_verdi"] == "evet"]
    isbirligi = [k for k in kayitlar if k["_iz"] >= 2]

    def oran(grup):
        return 100 * sum(1 for k in grup if k["cevap_verdi"] == "evet") / max(1, len(grup))

    # şablon aileleri (yalnızca bizim başlattığımız sohbetler)
    aileler = defaultdict(list)
    for k, imza in zip(giden, _sablon_imzalari(giden)):
        aileler[imza].append(k)
    aile_sirali = sorted(aileler.items(), key=lambda t: -len(t[1]))

    # aylık dağılım (giden)
    aylik = defaultdict(lambda: [0, 0])
    for k in giden:
        ay = k["ilk_mesaj"][:7]
        aylik[ay][0] += 1
        aylik[ay][1] += 1 if k["cevap_verdi"] == "evet" else 0

    sat = []
    ek = sat.append
    ek("# DM geçmişi analizi\n")
    ek(f"- Hesabımız (export'ta görünen ad): **{sonuc['ben']}**")
    ek(f"- Bizim yazdığımız (giden) sohbet: **{len(giden)}** · cevap veren: **{len(cevaplı)}**"
       f" (%{oran(giden):.1f})")
    ek(f"- Bize ilk yazan (gelen) sohbet: **{len(gelen)}** — bunlar keşif istatistiğine dahil değil")
    ek(f"- Karşı tarafın yazdıklarında işbirliği izi (kargo/adres/paylaştım…): "
       f"**{len(isbirligi)}** sohbet\n")

    ek("## Açılış şablonları — hangisi cevap alıyor?")
    ek("Aynı şablonla yazılan sohbetler gruplandı (isim/selam kısmı atılarak).\n")
    ek("| # | kaç kişiye | cevap oranı | şablon (örnek) |")
    ek("|---|---|---|---|")
    for i, (imza, grup) in enumerate(aile_sirali[:12], 1):
        if len(grup) < 10:
            break
        ornek = re.sub(r"\s+", " ", grup[0]["_ilk_metin"])[:140]
        ek(f"| {i} | {len(grup)} | %{oran(grup):.0f} | {ornek}… |")
    ek("")

    kisa = [k for k in giden if len(k["_ilk_metin"]) < 300]
    uzun = [k for k in giden if len(k["_ilk_metin"]) >= 300]
    ek("## Açılış uzunluğu (giden)")
    for etiket, grup in (("< 300 karakter", kisa), ("≥ 300 karakter", uzun)):
        if grup:
            ek(f"- {etiket}: {len(grup)} sohbet, cevap oranı %{oran(grup):.1f}")
    ek("")

    gunler = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
    gun_dagilim = defaultdict(list)
    saat_dagilim = defaultdict(list)
    for k in giden:
        if "_gun" in k:
            gun_dagilim[k["_gun"]].append(k)
            saat_dagilim[k["_saat"] // 3].append(k)   # 3 saatlik dilimler
    ek("## Haftanın günü / saat dilimi (giden)")
    ek("Saatler export'ta yazdığı gibidir (Instagram genelde UTC verir; Türkiye için +3 düşün).\n")
    ek("| gün | yazılan | cevap oranı |")
    ek("|---|---|---|")
    for g in range(7):
        if gun_dagilim[g]:
            ek(f"| {gunler[g]} | {len(gun_dagilim[g])} | %{oran(gun_dagilim[g]):.0f} |")
    ek("")
    ek("| saat dilimi | yazılan | cevap oranı |")
    ek("|---|---|---|")
    for d in range(8):
        if saat_dagilim[d]:
            ek(f"| {d * 3:02d}:00–{d * 3 + 3:02d}:00 | {len(saat_dagilim[d])} | %{oran(saat_dagilim[d]):.0f} |")
    ek("")
    ek("## Aylara göre (giden)")
    ek("| ay | yazılan | cevap | oran |")
    ek("|---|---|---|---|")
    for ay in sorted(aylik):
        n, c = aylik[ay]
        ek(f"| {ay} | {n} | {c} | %{100 * c / n:.0f} |")
    ek("")
    ek("## İşbirliğine dönmüş görünen sohbetler (ortaklar.txt'ye eklemeye aday)")
    ek("Karşı taraf kargo/adres/paylaştım/story gibi ifadeler kullanmış. iz = kaç farklı ifade.\n")
    for k in sorted(isbirligi, key=lambda k: (-k["_iz"], k["ilk_mesaj"]))[:80]:
        ek(f"- @{k['kullanici_adi']} — {k['ad']} ({k['ilk_mesaj']}, iz={k['_iz']})")
    return "\n".join(sat)


def ice_aktar(export_kok, ben=None):
    """Export'u analiz et, iletisim_gecmisi.csv + rapor_dm.md dosyalarını yaz."""
    sonuc = analiz_et(export_kok, ben)
    ortaklar = {ortak.kullanici_normalize(s) for s in ortak.satirlar(ortak.veri_yolu("ortaklar.txt"))}

    # Var olan geçmişle birleştir (elle eklenen kayıtlar korunur)
    mevcut = {ortak.kullanici_normalize(k["kullanici_adi"]): k for k in ortak.gecmis_oku()}
    for k in sonuc["kayitlar"]:
        k["ortak_video"] = "evet" if k["kullanici_adi"] in ortaklar else ""
        eski = mevcut.get(k["kullanici_adi"], {})
        if eski.get("ortak_video") == "evet":
            k["ortak_video"] = "evet"
        mevcut[k["kullanici_adi"]] = k

    ortak.gecmis_yaz(sorted(mevcut.values(), key=lambda k: k.get("ilk_mesaj", "")))
    rapor = rapor_uret(sonuc)
    rapor_yolu = ortak.veri_yolu("rapor_dm.md")
    with open(rapor_yolu, "w", encoding="utf-8") as f:
        f.write(rapor + "\n")
    return {"kisi": len(mevcut), "rapor": rapor_yolu, "ozet": rapor.split("\n## ")[0]}
