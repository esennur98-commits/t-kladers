#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aday havuzunu doldurma ve zenginleştirme.

Kullanıcı adı kaynakları (hepsi yasal, şifresiz):
  1. Kendi gönderilerimizin yorumcuları — Graph API kendi medyamızın
     yorumlarında kullanıcı adını verir. Ortak videolarımızın altındaki
     anneler en sıcak kaynaktır.
  2. Bizi etiketleyen hesaplar (/tags).
  3. Elle topladığın listeler: hashtag/Keşfet gezerken kopyaladığın
     kullanıcı adlarını bir .txt dosyasına alt alta yapıştır.

Havuza giren her satır 'zenginlestir' adımında business_discovery ile
takipçi/etkileşim verisine kavuşur.
"""
from . import graph as graph_mod
from . import ortak


def _mevcut_indeks(havuz):
    return {ortak.kullanici_normalize(a["kullanici_adi"]): a for a in havuz}


def kullanici_ekle(havuz, kullanicilar, kaynak):
    """Havuza yeni kullanıcı adları ekle; tekrarları ve dokunulmazları atla."""
    indeks = _mevcut_indeks(havuz)
    dokunulmaz = ortak.dokunulmaz_kumesi()
    yeni = 0
    for ham in kullanicilar:
        u = ortak.kullanici_normalize(ham)
        if not u or u in indeks or u in dokunulmaz:
            continue
        indeks[u] = {
            "kullanici_adi": u,
            "kaynak": kaynak,
            "ilk_gorulme": ortak.bugun(),
            "durum": "havuz",
        }
        havuz.append(indeks[u])
        yeni += 1
    return yeni


def manuel_ice_aktar(dosya, kaynak="manuel"):
    havuz = ortak.havuz_oku()
    yeni = kullanici_ekle(havuz, ortak.satirlar(dosya), kaynak)
    ortak.havuz_yaz(havuz)
    return {"yeni": yeni, "havuz": len(havuz)}


def graph_topla(gonderi_adedi=15, yorum_adedi=50, sessiz=False):
    """Kendi gönderilerimizin yorumcuları + bizi etiketleyenler."""
    g = graph_mod.Graph(sessiz=sessiz)
    havuz = ortak.havuz_oku()
    toplam = {"yorumcu": 0, "etiket": 0}

    for gonderi in g.kendi_gonderilerim(gonderi_adedi):
        if not gonderi.get("comments_count"):
            continue
        try:
            yorumlar = g.yorumcular(gonderi["id"], yorum_adedi)
        except graph_mod.GraphHatasi as e:
            if not sessiz:
                print(f"  yorumlar alınamadı ({gonderi['id']}): {e}")
            continue
        toplam["yorumcu"] += kullanici_ekle(
            havuz, [y.get("username", "") for y in yorumlar], "yorumcu")

    try:
        etiketler = g.etiketleyenler()
        toplam["etiket"] = kullanici_ekle(
            havuz, [e.get("username", "") for e in etiketler], "etiketleyen")
    except graph_mod.GraphHatasi as e:
        if not sessiz:
            print(f"  etiketler alınamadı: {e}")

    ortak.havuz_yaz(havuz)
    return {"yeni": sum(toplam.values()), "detay": toplam, "havuz": len(havuz)}


def zenginlestir(adet=60, yenile_gun=30, sessiz=False):
    """
    Verisi eksik (ya da bayat) havuz kayıtlarını business_discovery ile doldur.
    Kişisel hesaplar API'de görünmez; onları 'elendi' olarak işaretleriz.
    """
    g = graph_mod.Graph(sessiz=sessiz)
    havuz = ortak.havuz_oku()
    bekleyen = [a for a in havuz
                if a.get("durum") not in ("mesaj_atildi", "ortak_video")
                and "API'de yok" not in (a.get("not") or "")
                and (not ortak.sayi(a.get("takipci"))
                     or (ortak.gun_farki(a.get("son_guncelleme")) or 999) > yenile_gun)]
    islenen, bulunamayan, hata = 0, 0, 0

    for aday in bekleyen[:adet]:
        u = ortak.kullanici_normalize(aday["kullanici_adi"])
        try:
            p = g.profil(u)
        except graph_mod.GraphHatasi as e:
            hata += 1
            aday["not"] = f"api hatası: {e}"[:200]
            if not sessiz:
                print(f"  @{u}: {e}")
            continue
        if not p:
            bulunamayan += 1
            aday["durum"] = "elendi"
            aday["not"] = "API'de yok (kişisel hesap olabilir) — elle bak"
            aday["son_guncelleme"] = ortak.bugun()
            continue
        aday.update(graph_mod.profil_to_aday(p, aday.get("kaynak") or "graph"))
        islenen += 1
        if not sessiz:
            print(f"  @{u}: {int(ortak.sayi(aday['takipci'])):,} takipçi, "
                  f"%{ortak.sayi(aday['etkilesim_orani']):.1f} etkileşim".replace(",", "."))

    ortak.havuz_yaz(havuz)
    return {"islenen": islenen, "bulunamayan": bulunamayan, "hata": hata,
            "kalan": max(0, len(bekleyen) - adet)}


def ortaklari_zenginlestir(sessiz=False):
    """
    ortaklar.txt'deki (bizimle ortak video yapmış) hesapların verisini çekip
    ideal_profil.json üretir — puanlama bunu benzerlik ölçütü olarak kullanır.
    """
    from . import puan as puan_mod
    import json
    g = graph_mod.Graph(sessiz=sessiz)
    kayitlar = []
    for u in ortak.satirlar(ortak.veri_yolu("ortaklar.txt")):
        u = ortak.kullanici_normalize(u)
        try:
            p = g.profil(u)
        except graph_mod.GraphHatasi as e:
            if not sessiz:
                print(f"  @{u}: {e}")
            continue
        if p:
            kayitlar.append(graph_mod.profil_to_aday(p, "ortak"))
        elif not sessiz:
            print(f"  @{u}: API'de bulunamadı")
    ortak.csv_yaz(ortak.veri_yolu("ortaklar.csv"), kayitlar, ortak.ADAY_ALANLARI)
    profil = puan_mod.ideal_profil_uret(kayitlar)
    if profil:
        with open(ortak.veri_yolu("ideal_profil.json"), "w", encoding="utf-8") as f:
            json.dump(profil, f, ensure_ascii=False, indent=2)
    return {"ortak": len(kayitlar), "profil": bool(profil)}
