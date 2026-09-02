#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Graph API istemcisi (resmi, şifresiz yol).

Gerekenler:
  * Instagram hesabın "İşletme" ya da "İçerik Üretici" olmalı ve bir
    Facebook sayfasına bağlı olmalı.
  * developers.facebook.com'dan bir uygulama açıp uzun ömürlü erişim jetonu
    al (izinler: instagram_basic, pages_show_list, instagram_manage_comments).
  * Ortam değişkenleri:
        export IG_KULLANICI_ID="17841400000000000"
        export IG_JETON="EAAG..."

Jeton koda yazılmaz, repoya girmez — sadece ortam değişkeninden okunur.

Sınırlar (dürüst olalım):
  * business_discovery yalnızca İşletme/İçerik Üretici hesapları döndürür;
    kişisel hesaplar "bulunamadı" olarak işaretlenir.
  * API takipçi listesi vermez. Yeni kullanıcı adı kaynakları: kendi
    gönderilerimizin yorumcuları, bizi etiketleyenler ve elle topladığın
    hashtag listeleri.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import ortak

TABAN = "https://graph.facebook.com"


class GraphHatasi(RuntimeError):
    pass


class Graph:
    def __init__(self, kullanici_id=None, jeton=None, kriter=None, sessiz=False):
        k = kriter or ortak.kriterler()
        self.surum = k["graph"]["surum"]
        self.bekleme = k["graph"]["istekler_arasi_bekleme_sn"]
        self.gonderi_adedi = k["graph"]["son_gonderi_adedi"]
        self.kullanici_id = kullanici_id or os.environ.get("IG_KULLANICI_ID", "")
        self.jeton = jeton or os.environ.get("IG_JETON", "")
        self.sessiz = sessiz
        self.son_istek = 0.0
        if not (self.kullanici_id and self.jeton):
            raise GraphHatasi(
                "IG_KULLANICI_ID ve IG_JETON ortam değişkenleri gerekli. "
                "Kurulum için KESIF_REHBERI.md → 'Graph API kurulumu'."
            )

    # --------------------------------------------------------------- alt kat
    def _bekle(self):
        gecen = time.time() - self.son_istek
        if gecen < self.bekleme:
            time.sleep(self.bekleme - gecen)
        self.son_istek = time.time()

    def istek(self, yol, **parametreler):
        """Tek bir GET; hız sınırında üstel bekleyerek 4 kez dener."""
        parametreler["access_token"] = self.jeton
        url = f"{TABAN}/{self.surum}/{yol.lstrip('/')}?{urllib.parse.urlencode(parametreler)}"
        gecikme = 5
        for deneme in range(4):
            self._bekle()
            try:
                with urllib.request.urlopen(url, timeout=30) as cevap:
                    return json.loads(cevap.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                govde = e.read().decode("utf-8", "replace")
                try:
                    hata = json.loads(govde).get("error", {})
                except json.JSONDecodeError:
                    hata = {"message": govde}
                kod = hata.get("code")
                if kod in (4, 17, 32, 613) and deneme < 3:      # hız sınırı
                    if not self.sessiz:
                        print(f"  … hız sınırı, {gecikme}sn bekleniyor")
                    time.sleep(gecikme)
                    gecikme *= 2
                    continue
                raise GraphHatasi(f"[{kod}] {hata.get('message', govde)}")
            except urllib.error.URLError as e:
                if deneme < 3:
                    time.sleep(gecikme)
                    gecikme *= 2
                    continue
                raise GraphHatasi(str(e))
        raise GraphHatasi("istek başarısız")

    # ------------------------------------------------------------ sorgular
    def profil(self, kullanici_adi):
        """
        business_discovery ile bir hesabın herkese açık metriklerini çek.
        Hesap yoksa / kişiselse None döner.
        """
        u = ortak.kullanici_normalize(kullanici_adi)
        alanlar = (
            f"business_discovery.username({u})"
            "{username,name,biography,followers_count,follows_count,media_count,"
            f"media.limit({self.gonderi_adedi})"
            "{caption,like_count,comments_count,timestamp,media_product_type,media_type}}"
        )
        try:
            cevap = self.istek(self.kullanici_id, fields=alanlar)
        except GraphHatasi as e:
            if "does not exist" in str(e) or "[110]" in str(e) or "[24]" in str(e):
                return None
            raise
        return cevap.get("business_discovery")

    def kendi_gonderilerim(self, adet=25):
        cevap = self.istek(
            f"{self.kullanici_id}/media",
            fields="id,caption,timestamp,permalink,media_product_type,comments_count",
            limit=adet,
        )
        return cevap.get("data", [])

    def yorumcular(self, gonderi_id, adet=50):
        """Kendi gönderimizin yorumcuları — kullanıcı adı içerir."""
        cevap = self.istek(f"{gonderi_id}/comments",
                           fields="username,text,timestamp", limit=adet)
        return cevap.get("data", [])

    def etiketleyenler(self, adet=50):
        """Bizi gönderisinde etiketleyen hesaplar."""
        cevap = self.istek(f"{self.kullanici_id}/tags",
                           fields="username,caption,timestamp", limit=adet)
        return cevap.get("data", [])


# ----------------------------------------------------- profil → aday satırı
def profil_to_aday(p, kaynak="graph"):
    """business_discovery cevabını havuz.csv satırına çevir."""
    gonderiler = (p.get("media") or {}).get("data", []) or []
    n = max(1, len(gonderiler))
    begeni = sum(g.get("like_count", 0) or 0 for g in gonderiler) / n
    yorum = sum(g.get("comments_count", 0) or 0 for g in gonderiler) / n
    takipci = p.get("followers_count", 0) or 0
    video = sum(1 for g in gonderiler
                if g.get("media_product_type") in ("REELS", "VIDEO")
                or g.get("media_type") == "VIDEO")
    basliklar = " ".join((g.get("caption") or "")[:400] for g in gonderiler)
    sponsor_kelime = ortak.kriterler()["anahtar_kelimeler"]["sponsor"]
    sponsorlu = sum(1 for g in gonderiler
                    if ortak.kelime_sayisi(g.get("caption") or "", sponsor_kelime)[0] > 0)
    zamanlar = sorted(t for t in (g.get("timestamp") for g in gonderiler) if t)
    son_30 = sum(1 for t in zamanlar if (ortak.gun_farki(t) or 999) <= 30)

    return {
        "kullanici_adi": ortak.kullanici_normalize(p.get("username", "")),
        "ad": p.get("name", ""),
        "takipci": takipci,
        "takip": p.get("follows_count", 0) or 0,
        "gonderi_sayisi": p.get("media_count", 0) or 0,
        "biyografi": (p.get("biography") or "").replace("\n", " "),
        "ort_begeni": round(begeni, 1),
        "ort_yorum": round(yorum, 1),
        "etkilesim_orani": round(100 * (begeni + yorum) / takipci, 2) if takipci else 0,
        "video_orani": round(video / n, 2),
        "sponsor_orani": round(sponsorlu / n, 2),
        "son_paylasim": (zamanlar[-1][:10] if zamanlar else ""),
        "gonderi_30gun": son_30,
        "son_basliklar": basliklar[:1500].replace("\n", " "),
        "kaynak": kaynak,
        "son_guncelleme": ortak.bugun(),
        "durum": "havuz",
    }
