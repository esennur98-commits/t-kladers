#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Günün listesini üretir: puanı en yüksek N aday + her biri için kişiye özel
DM taslağı. Mesajı araç GÖNDERMEZ — sen okuyup, düzeltip elle atarsın.
(Otomatik DM gönderimi Instagram kurallarına aykırıdır ve hesabı riske atar.)
"""
import os
import re

from . import ortak
from . import puan as puan_mod

SABLON_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "sablonlar", "dm.md")


def sablonlari_oku(yol=None):
    """dm.md dosyasını '## isim' başlıklarına göre parçala."""
    yol = yol or SABLON_YOLU
    if not os.path.exists(yol):
        return {}
    with open(yol, encoding="utf-8") as f:
        ham = f.read()
    sablonlar, isim, govde = {}, None, []
    for satir in ham.splitlines():
        if satir.startswith("## "):
            if isim:
                sablonlar[isim] = "\n".join(govde).strip()
            isim, govde = satir[3:].strip(), []
        elif isim:
            govde.append(satir)
    if isim:
        sablonlar[isim] = "\n".join(govde).strip()
    return sablonlar


def _ilk_ad(aday):
    ad = (aday.get("ad") or "").strip()
    ad = re.sub(r"[^\wÇĞİÖŞÜçğıöşü ]", " ", ad).strip()
    parca = [p for p in ad.split() if len(p) > 1]
    return parca[0].capitalize() if parca else "Merhaba"


def _kanca(aday, kriter):
    """Adayın içeriğinden kişiselleştirme kancası çıkar."""
    metin = f"{aday.get('biyografi', '')} {aday.get('son_basliklar', '')}"
    _, egitim = ortak.kelime_sayisi(metin, kriter["anahtar_kelimeler"]["egitim"])
    _, yas = ortak.kelime_sayisi(metin, kriter["anahtar_kelimeler"]["yas_2_8"])
    # en özgül (en uzun) eşleşen kelimeyi seç: "montessori" > "oyun"
    kanca = max(egitim, key=len) if egitim else "çocuk etkinliği"
    return f"{kanca} içeriklerinizi", (yas[0] if yas else "")


def dm_taslagi(aday, sablon, kriter=None):
    k = kriter or ortak.kriterler()
    kanca, yas = _kanca(aday, k)
    return (sablon
            .replace("{ad}", _ilk_ad(aday))
            .replace("{kanca}", kanca)
            .replace("{yas}", yas or "2-8 yaş")
            .replace("{kullanici}", "@" + aday.get("kullanici_adi", "")))


def liste_uret(hedef=None, min_puan=None, sablon_adi="ilk_mesaj", tarih=None):
    """Havuzu puanla, günün listesini CSV + brifing olarak yaz."""
    k = ortak.kriterler()
    hedef = hedef or k["gunluk"]["hedef_kisi"]
    min_puan = k["gunluk"]["min_puan"] if min_puan is None else min_puan
    tarih = tarih or ortak.bugun()

    havuz = ortak.havuz_oku()
    puanli = puan_mod.havuzu_puanla(havuz)
    ortak.havuz_yaz(puanli)

    uygun = [a for a in puanli
             if a["durum"] in ("havuz", "secildi") and ortak.sayi(a["puan"], -1) >= min_puan]
    secilen = uygun[:hedef]
    devreden = sum(1 for a in secilen if a["durum"] == "secildi")
    for a in secilen:
        a["durum"] = "secildi"
    ortak.havuz_yaz(puanli)

    csv_yolu = ortak.csv_yaz(ortak.veri_yolu("gunluk", f"{tarih}.csv"),
                             secilen, ortak.ADAY_ALANLARI)

    sablonlar = sablonlari_oku()
    sablon = sablonlar.get(sablon_adi) or next(iter(sablonlar.values()), "{ad}, merhaba!")
    veri_eksik = sum(1 for a in puanli if not ortak.sayi(a.get("takipci")))

    sat = [f"# {tarih} — günün {len(secilen)} adayı\n",
           f"- Havuz: {len(puanli)} kayıt · uygun: {len(uygun)} · seçilen: {len(secilen)}",
           f"- Verisi henüz çekilmemiş kayıt: {veri_eksik} "
           f"(`python3 -m kesif zenginlestir` ile doldur)",
           f"- Eşik: {min_puan} puan · önceki günlerden devreden (henüz mesaj atılmamış): {devreden}\n"]
    if devreden:
        sat.append("> Devredenler mesaj atılana kadar listede kalır. Attıklarını "
                   "`python3 -m kesif isaretle --dosya <bugünün csv'si>` ile işaretle.\n")
    if len(secilen) < hedef:
        sat.append(f"> ⚠️ Hedef {hedef} kişiydi, {len(secilen)} çıktı. Havuzu besle: "
                   f"`topla-graph`, `manuel` veya eşiği düşür (`--min-puan`).\n")
    for i, a in enumerate(secilen, 1):
        sat.append(f"## {i}. @{a['kullanici_adi']} — {a['puan']} puan")
        sat.append(f"- {a.get('ad', '')} · {int(ortak.sayi(a['takipci'])):,}".replace(",", ".")
                   + f" takipçi · etkileşim %{ortak.sayi(a['etkilesim_orani']):.1f}"
                   + f" · video oranı %{ortak.sayi(a['video_orani']) * 100:.0f}"
                   + f" · kaynak: {a.get('kaynak', '')}")
        sat.append(f"- instagram.com/{a['kullanici_adi']}")
        if a.get("biyografi"):
            sat.append(f"- bio: {a['biyografi'][:180]}")
        if a.get("_gerekce"):
            sat.append("- neden: " + "; ".join(a["_gerekce"]))
        sat.append("\n```\n" + dm_taslagi(a, sablon, k) + "\n```\n")

    brifing_yolu = ortak.veri_yolu("gunluk", f"{tarih}.md")
    with open(brifing_yolu, "w", encoding="utf-8") as f:
        f.write("\n".join(sat) + "\n")
    return {"secilen": len(secilen), "devreden": devreden, "uygun": len(uygun),
            "havuz": len(puanli), "csv": csv_yolu, "brifing": brifing_yolu,
            "veri_eksik": veri_eksik}


def isaretle(kullanicilar=None, dosya=None, ortak_video=False, notu=""):
    """
    Mesaj attığın kişileri geçmişe yaz — böylece bir daha listeye düşmezler.
    `dosya` bir günlük CSV ya da satır satır kullanıcı adı içeren .txt olabilir.
    """
    hedefler = [ortak.kullanici_normalize(u) for u in (kullanicilar or [])]
    if dosya:
        if dosya.endswith(".csv"):
            hedefler += [ortak.kullanici_normalize(r.get("kullanici_adi", ""))
                         for r in ortak.csv_oku(dosya)]
        else:
            hedefler += [ortak.kullanici_normalize(s) for s in ortak.satirlar(dosya)]
    hedefler = [u for u in dict.fromkeys(hedefler) if u]

    gecmis = {ortak.kullanici_normalize(k["kullanici_adi"]): k for k in ortak.gecmis_oku()}
    havuz_indeks = {ortak.kullanici_normalize(a["kullanici_adi"]): a
                    for a in ortak.havuz_oku()}
    yeni = 0
    for u in hedefler:
        aday = havuz_indeks.get(u, {})
        kayit = gecmis.get(u, {"kullanici_adi": u, "bizim_mesaj": 0, "onlarin_mesaj": 0,
                               "cevap_verdi": "hayır", "kaynak": "kesif"})
        kayit["ad"] = kayit.get("ad") or aday.get("ad", "")
        kayit["ilk_mesaj"] = kayit.get("ilk_mesaj") or ortak.bugun()
        kayit["son_mesaj"] = ortak.bugun()
        kayit["bizim_mesaj"] = int(ortak.sayi(kayit.get("bizim_mesaj"))) + 1
        if ortak_video:
            kayit["ortak_video"] = "evet"
        if notu:
            kayit["not"] = notu
        if u not in gecmis:
            yeni += 1
        gecmis[u] = kayit
        if u in havuz_indeks:
            havuz_indeks[u]["durum"] = "ortak_video" if ortak_video else "mesaj_atildi"

    ortak.gecmis_yaz(sorted(gecmis.values(), key=lambda k: k.get("ilk_mesaj", "")))
    ortak.havuz_yaz(list(havuz_indeks.values()))
    if ortak_video:
        yol = ortak.veri_yolu("ortaklar.txt")
        mevcut = set(ortak.satirlar(yol))
        with open(yol, "a", encoding="utf-8") as f:
            for u in hedefler:
                if u not in mevcut:
                    f.write(u + "\n")
    return {"islenen": len(hedefler), "yeni": yeni, "gecmis": len(gecmis)}
