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
            if re.fullmatch(r"message_\d+\.json", d):
                bulunan.append(os.path.join(dizin, d))
    return sorted(bulunan)


def _kullanici_adi_cikar(dosya_yolu, baslik):
    """
    Klasör adı genelde "kullaniciadi_17843968..." biçiminde olur; sondaki
    sayı bloğunu atınca kullanıcı adı kalır. Olmazsa başlıktan türetiriz.
    """
    klasor = os.path.basename(os.path.dirname(dosya_yolu))
    ad = re.sub(r"_\d{6,}$", "", klasor)
    if ad and re.fullmatch(r"[A-Za-z0-9._]+", ad):
        return ortak.kullanici_normalize(ad)
    return ortak.kullanici_normalize(re.sub(r"[^A-Za-z0-9._]", "", baslik or ""))


def _sohbetleri_oku(kok):
    """Her ikili sohbeti (thread) normalize edilmiş sözlük olarak döndür."""
    sohbetler = []
    for yol in _mesaj_dosyalari(kok):
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
        if not bizim:
            continue  # biz hiç yazmamışız: gelen kutusu trafiği, keşif verisi değil
        ilk_bizim = bizim[0]
        tum_metin = " ".join(m["metin"] for m in s["mesajlar"])
        iz_sayisi, _ = ortak.kelime_sayisi(tum_metin, ISBIRLIGI_IZLERI)
        kayitlar.append({
            "kullanici_adi": s["kullanici_adi"],
            "ad": s["ad"],
            "ilk_mesaj": ilk_bizim["zaman"].strftime("%Y-%m-%d"),
            "son_mesaj": s["mesajlar"][-1]["zaman"].strftime("%Y-%m-%d"),
            "bizim_mesaj": len(bizim),
            "onlarin_mesaj": len(onlarin),
            "cevap_verdi": "evet" if onlarin else "hayır",
            "ortak_video": "",
            "kaynak": "dm_export",
            "not": f"isbirligi_izi={iz_sayisi}",
            "_ilk_metin": ilk_bizim["metin"],
            "_iz": iz_sayisi,
        })
    return {"ben": ben, "kayitlar": kayitlar, "sohbetler": sohbetler}


# ------------------------------------------------------------------ rapor
_DURAK = set("""bir ve ile için de da bu şu o çok en gibi ama ki mi mı mu mü ben biz siz
sen çünkü ise her daha sonra kadar var yok olarak diye ya veya bize size sizin bizim
merhaba selam nasılsınız iyi günler""".split())


def _kelimeler(metin):
    return [k for k in re.findall(r"[a-zçğıöşü]{4,}", ortak.kucuk(metin)) if k not in _DURAK]


def rapor_uret(sonuc):
    """Cevap oranı, aylık dağılım ve açılış cümlesi analizini metin olarak üret."""
    kayitlar = sonuc["kayitlar"]
    if not kayitlar:
        return "DM export'unda bizim yazdığımız sohbet bulunamadı."

    toplam = len(kayitlar)
    cevaplı = [k for k in kayitlar if k["cevap_verdi"] == "evet"]
    isbirligi = [k for k in kayitlar if k["_iz"] >= 3]

    # açılış mesajı uzunluğu ↔ cevap oranı
    kisa = [k for k in kayitlar if len(k["_ilk_metin"]) < 300]
    uzun = [k for k in kayitlar if len(k["_ilk_metin"]) >= 300]

    # kelime bazlı cevap oranı (en az 5 kez geçen kelimeler)
    gecti, cevapladi = Counter(), Counter()
    for k in kayitlar:
        for kelime in set(_kelimeler(k["_ilk_metin"])):
            gecti[kelime] += 1
            if k["cevap_verdi"] == "evet":
                cevapladi[kelime] += 1
    kelime_orani = sorted(
        ((kelime, cevapladi[kelime] / n, n) for kelime, n in gecti.items() if n >= 5),
        key=lambda t: (-t[1], -t[2]),
    )

    # aylık dağılım
    aylik = defaultdict(lambda: [0, 0])
    for k in kayitlar:
        ay = k["ilk_mesaj"][:7]
        aylik[ay][0] += 1
        aylik[ay][1] += 1 if k["cevap_verdi"] == "evet" else 0

    sat = []
    ek = sat.append
    ek("# DM geçmişi analizi\n")
    ek(f"- Hesabımız (export'ta görünen ad): **{sonuc['ben']}**")
    ek(f"- Mesaj attığımız kişi sayısı: **{toplam}**")
    ek(f"- Cevap veren: **{len(cevaplı)}** (%{100 * len(cevaplı) / toplam:.1f})")
    ek(f"- İşbirliği izi güçlü sohbet (kargo/adres/paylaştım geçen): **{len(isbirligi)}**"
       f" (%{100 * len(isbirligi) / toplam:.1f})\n")

    ek("## Açılış mesajı uzunluğu")
    for etiket, grup in (("< 300 karakter", kisa), ("≥ 300 karakter", uzun)):
        if grup:
            oran = 100 * sum(1 for k in grup if k["cevap_verdi"] == "evet") / len(grup)
            ek(f"- {etiket}: {len(grup)} mesaj, cevap oranı %{oran:.1f}")
    ek("")

    if kelime_orani:
        ek("## İlk mesajda geçtiğinde cevap oranı en yüksek kelimeler")
        ek("| kelime | cevap oranı | kaç mesajda |")
        ek("|---|---|---|")
        for kelime, oran, n in kelime_orani[:15]:
            ek(f"| {kelime} | %{100 * oran:.0f} | {n} |")
        ek("")
        ek("## En düşük cevap oranlı kelimeler (bunlardan kaçın)")
        ek("| kelime | cevap oranı | kaç mesajda |")
        ek("|---|---|---|")
        for kelime, oran, n in kelime_orani[-8:]:
            ek(f"| {kelime} | %{100 * oran:.0f} | {n} |")
        ek("")

    ek("## Aylara göre")
    ek("| ay | yazılan | cevap | oran |")
    ek("|---|---|---|---|")
    for ay in sorted(aylik):
        n, c = aylik[ay]
        ek(f"| {ay} | {n} | {c} | %{100 * c / n:.0f} |")
    ek("")
    ek("## İşbirliğine dönmüş görünen sohbetler (ortaklar.txt'ye eklemeye aday)")
    for k in sorted(isbirligi, key=lambda k: -k["_iz"])[:40]:
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
