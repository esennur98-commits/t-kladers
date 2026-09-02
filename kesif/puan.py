#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aday puanlama motoru.

Puan 0–100. Her bileşen 0–1 arası hesaplanır, kriterler.json'daki
ağırlıklarla çarpılır ve mevcut bileşenler üzerinden normalize edilir.
Her aday için "neden bu puan" gerekçeleri de üretilir — listeye körlemesine
güvenmek yerine bakıp karar verebilesin diye.
"""
import json
import os
import re
import statistics
from collections import Counter

from . import ortak

_DURAK = set("""bir ile için ama daha çok gibi olarak sonra kadar var yok bu şu her
oldu olur diye ise hem yine bugün burada www com http https instagram link
takip hesap sayfa paylaş paylaşım video reels story""".split())


# ------------------------------------------------------------- yardımcılar
def _bant(deger, alt, ideal_alt, ideal_ust, ust):
    """Trapez skor: ideal aralıkta 1.0, kenarlara doğru doğrusal düşer."""
    if deger <= alt or deger >= ust:
        return 0.0
    if ideal_alt <= deger <= ideal_ust:
        return 1.0
    if deger < ideal_alt:
        return (deger - alt) / max(1e-9, ideal_alt - alt)
    return (ust - deger) / max(1e-9, ust - ideal_ust)


def _basamak(sayi, *tablo):
    """Kaç sinyal bulunduğuna göre basamaklı skor: (1 sinyal, 2 sinyal, ...) ; üstü 1.0."""
    if sayi <= 0:
        return 0.0
    return tablo[sayi - 1] if sayi <= len(tablo) else 1.0


def _metin(aday):
    return f"{aday.get('biyografi', '')} {aday.get('son_basliklar', '')} {aday.get('ad', '')}"


# ------------------------------------------------------------ ideal profil
def ideal_profil_uret(kayitlar):
    """
    Bizimle ortak video yapmış hesaplardan "ideal partner" imzası çıkar:
    takipçi/etkileşim medyanı + en sık geçen anlamlı kelimeler.
    """
    kayitlar = [k for k in kayitlar if ortak.sayi(k.get("takipci")) > 0]
    if not kayitlar:
        return None
    kelime_sayac = Counter()
    for k in kayitlar:
        for kelime in set(re.findall(r"[a-zçğıöşü]{4,}", ortak.kucuk(_metin(k)))):
            if kelime not in _DURAK:
                kelime_sayac[kelime] += 1
    esik = max(2, len(kayitlar) // 4)
    kelimeler = {k: n / len(kayitlar) for k, n in kelime_sayac.items() if n >= esik}
    return {
        "ortak_sayisi": len(kayitlar),
        "takipci_medyan": statistics.median(ortak.sayi(k["takipci"]) for k in kayitlar),
        "etkilesim_medyan": statistics.median(
            ortak.sayi(k.get("etkilesim_orani")) for k in kayitlar),
        "video_orani_medyan": statistics.median(
            ortak.sayi(k.get("video_orani")) for k in kayitlar),
        "anahtar_kelimeler": dict(sorted(kelimeler.items(), key=lambda t: -t[1])[:60]),
    }


def ideal_profil_oku():
    yol = os.path.join(ortak.VERI, "ideal_profil.json")
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------- puanlama
def puanla(aday, kriter=None, ideal=None):
    """(puan, bileşenler, gerekçeler, elemeler) döndür."""
    k = kriter or ortak.kriterler()
    kel = k["anahtar_kelimeler"]
    metin = _metin(aday)
    gerekce, eleme, bilesen = [], [], {}

    takipci = ortak.sayi(aday.get("takipci"))
    er = ortak.sayi(aday.get("etkilesim_orani"))

    # 1) takipçi bandı
    t = k["takipci"]
    bilesen["takipci"] = _bant(takipci, t["min"] * 0.8, t["ideal_min"],
                               t["ideal_max"], t["max"] * 1.25)
    if takipci < t["min"] or takipci > t["max"]:
        eleme.append(f"takipçi {int(takipci):,} — {t['min']:,}-{t['max']:,} bandı dışında"
                     .replace(",", "."))
    elif t["ideal_min"] <= takipci <= t["ideal_max"]:
        gerekce.append(f"takipçi {int(takipci):,}".replace(",", ".") + " (ideal band)")

    # 2) etkileşim oranı
    e = k["etkilesim_orani"]
    bilesen["etkilesim"] = min(1.0, er / e["ideal"]) if er > 0 else 0.0
    if er >= e["ideal"]:
        gerekce.append(f"etkileşim %{er:.1f} — güçlü")
    elif er and er < e["min"]:
        eleme.append(f"etkileşim %{er:.1f} — eşiğin (%{e['min']}) altında")

    # 3) içerik uyumu (anne + eğitim kelimeleri)
    anne_n, anne_k = ortak.kelime_sayisi(metin, kel["anne"])
    egitim_n, egitim_k = ortak.kelime_sayisi(metin, kel["egitim"])
    bilesen["icerik"] = 0.4 * _basamak(anne_n, 0.7) + 0.6 * _basamak(egitim_n, 0.5, 0.8)
    if egitim_k:
        gerekce.append("içerik: " + ", ".join(egitim_k[:4]))
    if anne_n == 0 and egitim_n == 0:
        eleme.append("biyografi/başlıklarda anne veya çocuk etkinliği izi yok")

    # 4) 2–8 yaş uyumu
    yas_n, yas_k = ortak.kelime_sayisi(metin, kel["yas_2_8"])
    disi_n, disi_k = ortak.kelime_sayisi(metin, k["yas_2_8_disi"])
    bilesen["yas_uyumu"] = max(0.0, _basamak(yas_n, 0.75) - 0.35 * min(1, disi_n))
    if yas_k:
        gerekce.append("yaş sinyali: " + ", ".join(yas_k[:3]))
    if disi_k and not yas_k:
        eleme.append("hedef yaş dışı sinyal (" + ", ".join(disi_k[:2]) + "), 2-8 yaş izi yok")

    # 5) video ağırlığı (bizden istenen çıktı video)
    bilesen["video"] = min(1.0, ortak.sayi(aday.get("video_orani")) / 0.6)

    # 6) aktiflik
    gecen = ortak.gun_farki(aday.get("son_paylasim"))
    a = k["aktiflik"]
    tazelik = 1.0 if gecen is None else max(0.0, 1 - gecen / (a["son_paylasim_gun_limit"] * 2))
    sıklık = min(1.0, ortak.sayi(aday.get("gonderi_30gun")) / a["ideal_gonderi_30gun"])
    bilesen["aktiflik"] = 0.5 * tazelik + 0.5 * sıklık
    if gecen is not None and gecen > a["son_paylasim_gun_limit"]:
        eleme.append(f"son paylaşım {gecen} gün önce")

    # 7) ortak video yaptıklarımıza benzerlik
    if ideal and ideal.get("anahtar_kelimeler"):
        m = ortak.kucuk(metin)
        toplam = sum(ideal["anahtar_kelimeler"].values()) or 1
        eslesen = sum(w for kelime, w in ideal["anahtar_kelimeler"].items() if kelime in m)
        bilesen["benzerlik"] = min(1.0, (eslesen / toplam) * 2.5)
        if bilesen["benzerlik"] > 0.5:
            gerekce.append("ortak video yaptıklarımıza içerik olarak benziyor")

    # cezalar / sert elemeler
    sponsor = ortak.sayi(aday.get("sponsor_orani"))
    s = k["sponsor"]
    ceza = 0.0
    if sponsor >= s["eleme_orani"]:
        eleme.append(f"gönderilerin %{sponsor * 100:.0f}'ı reklam — hesap doygun")
    elif sponsor >= s["uyari_orani"]:
        ceza += 0.10
        gerekce.append(f"uyarı: reklam oranı %{sponsor * 100:.0f}")
    olumsuz_n, olumsuz_k = ortak.kelime_sayisi(metin, kel["olumsuz"])
    if olumsuz_n:
        ceza += 0.10 * min(2, olumsuz_n)
        gerekce.append("uyarı: satış/ilgisiz sinyal — " + ", ".join(olumsuz_k[:2]))
    takip = ortak.sayi(aday.get("takip"))
    if takipci and takip > takipci:
        ceza += 0.05
        gerekce.append("uyarı: takip ettiği kişi takipçisinden fazla")

    agirlik = k["agirliklar"]
    kullanilan = {b: agirlik.get(b, 0) for b in bilesen}
    toplam_agirlik = sum(kullanilan.values()) or 1
    ham = sum(bilesen[b] * kullanilan[b] for b in bilesen) / toplam_agirlik
    puan = round(max(0.0, min(1.0, ham - ceza)) * 100, 1)
    return puan, bilesen, gerekce, eleme


def havuzu_puanla(kayitlar, kriter=None, ideal=None, gecmis=None):
    """
    Havuzun tamamını puanla. Daha önce mesaj attıklarımız otomatik elenir.
    Kayıtlara 'puan', 'durum' ve '_gerekce' alanlarını yazar.
    """
    k = kriter or ortak.kriterler()
    ideal = ideal if ideal is not None else ideal_profil_oku()
    gecmis = gecmis if gecmis is not None else ortak.dokunulmaz_kumesi()
    sonuc = []
    for aday in kayitlar:
        aday = dict(aday)
        kullanici = ortak.kullanici_normalize(aday.get("kullanici_adi"))
        aday["kullanici_adi"] = kullanici
        aday.setdefault("_gerekce", [])
        aday.setdefault("_eleme", [])

        # Kalıcı durumlar puanlamayla değişmez
        if aday.get("durum") in ("mesaj_atildi", "ortak_video"):
            sonuc.append(aday)
            continue
        if kullanici in gecmis:
            aday["durum"] = "elendi"
            aday["not"] = "daha önce mesaj attık / ortak çalıştık"
            aday["puan"] = ""
            sonuc.append(aday)
            continue
        # Verisi çekilmemiş kayıt: puanlama anlamsız, zenginleştirme bekler
        if not ortak.sayi(aday.get("takipci")):
            aday["puan"] = ""
            if "API'de yok" not in (aday.get("not") or ""):
                aday["durum"] = "havuz"
                aday["not"] = "veri bekleniyor (zenginlestir)"
            sonuc.append(aday)
            continue

        puan, bilesen, gerekce, eleme = puanla(aday, k, ideal)
        aday["puan"] = puan
        aday["_bilesen"] = bilesen
        aday["_gerekce"] = gerekce
        aday["_eleme"] = eleme
        if eleme:
            aday["durum"] = "elendi"
            aday["not"] = "; ".join(eleme)[:300]
        else:
            # önceki gün seçilmiş ama mesaj atılmamışsa 'secildi' kalır
            aday["durum"] = "secildi" if aday.get("durum") == "secildi" else "havuz"
            aday["not"] = ""
        sonuc.append(aday)
    sonuc.sort(key=lambda a: -(ortak.sayi(a.get("puan"), -1)))
    return sonuc
