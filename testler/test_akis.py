#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Uçtan uca test: örnek export + örnek havuz ile tüm akış API'siz çalışır.
    python3 testler/test_akis.py
"""
import os
import shutil
import sys
import tempfile
import unittest

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
GECICI = tempfile.mkdtemp(prefix="kesif_test_")
os.environ["KESIF_VERI"] = GECICI

from kesif import dm_gecmisi, gunluk, ortak, puan, toplama  # noqa: E402

ORNEK = os.path.join(KOK, "ornek")


class Akis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ortak.veri_yolu("ortaklar.txt"), "w", encoding="utf-8") as f:
            f.write("aysenur.etkinlik\n")
        cls.dm = dm_gecmisi.ice_aktar(os.path.join(ORNEK, "export"))
        shutil.copy(os.path.join(ORNEK, "havuz_ornek.csv"), ortak.veri_yolu("havuz.csv"))
        cls.manuel = toplama.manuel_ice_aktar(os.path.join(ORNEK, "manuel_liste.txt"), "test")
        cls.gun = gunluk.liste_uret(hedef=50, tarih="2026-09-02")
        cls.havuz = {a["kullanici_adi"]: a for a in ortak.havuz_oku()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(GECICI, ignore_errors=True)

    # --- DM export
    def test_dm_export_turkce_ve_grup(self):
        gecmis = {g["kullanici_adi"]: g for g in ortak.gecmis_oku()}
        self.assertEqual(self.dm["kisi"], 3, "grup sohbeti atlanmalı")
        self.assertEqual(gecmis["aysenur.etkinlik"]["ad"], "Ayşenur Etkinlik", "mojibake düzelmeli")
        self.assertEqual(gecmis["aysenur.etkinlik"]["cevap_verdi"], "evet")
        self.assertEqual(gecmis["aysenur.etkinlik"]["ortak_video"], "evet")
        self.assertEqual(gecmis["melisanne"]["cevap_verdi"], "hayır")
        self.assertTrue(os.path.exists(ortak.veri_yolu("rapor_dm.md")))

    # --- havuz toplama
    def test_manuel_liste_normalize_ve_dedup(self):
        # @Elif.EvdeOyun ve buse.anne havuzda zaten var; link ve düz ad yeni
        self.assertEqual(self.manuel["yeni"], 2)
        self.assertIn("yeni.anne.oyun", self.havuz)
        self.assertIn("okuloncesi.atolye", self.havuz)
        # dokunulmazlar (geçmişte olanlar) havuza tekrar giremez
        havuz = ortak.havuz_oku()
        self.assertEqual(toplama.kullanici_ekle(havuz, ["@Melisanne", "zeynep.oyun"], "x"), 0)

    # --- puanlama
    def test_siralama_ve_elemeler(self):
        h = self.havuz
        self.assertEqual(h["elif.evdeoyun"]["durum"], "secildi")
        self.assertEqual(h["buse.anne"]["durum"], "secildi")
        self.assertGreater(ortak.sayi(h["elif.evdeoyun"]["puan"]), ortak.sayi(h["buse.anne"]["puan"]))
        self.assertEqual(h["aysenur.etkinlik"]["durum"], "elendi", "daha önce yazdık")
        self.assertEqual(h["dev.anne.tr"]["durum"], "elendi", "180k band dışı")
        self.assertEqual(h["minik.butik"]["durum"], "elendi", "düşük etkileşim + satış")
        self.assertEqual(h["sessiz.anne"]["durum"], "elendi", "115 gündür paylaşım yok")
        self.assertEqual(h["hamile.gunlugu"]["durum"], "elendi", "hedef yaş dışı")
        self.assertEqual(h["verisiz.hesap"]["durum"], "havuz", "verisiz kayıt zenginleştirme bekler")
        self.assertEqual(h["verisiz.hesap"]["puan"], "")
        self.assertEqual(self.gun["secilen"], 2)

    def test_puan_bilesenleri_sinirda(self):
        k = ortak.kriterler()
        p, b, _, e = puan.puanla({"takipci": 25000, "etkilesim_orani": 3.5, "biyografi":
                                  "anne 3 yaş montessori etkinlik oyun", "video_orani": 0.7,
                                  "son_paylasim": ortak.bugun(), "gonderi_30gun": 10}, k)
        self.assertEqual(e, [])
        self.assertGreater(p, 85)
        for ad, deger in b.items():
            self.assertTrue(0 <= deger <= 1, ad)

    # --- ideal profil
    def test_ideal_profil(self):
        ort = [{"takipci": 20000, "etkilesim_orani": 4, "video_orani": .7,
                "biyografi": "montessori anne etkinlik", "son_basliklar": "duyusal oyun"},
               {"takipci": 30000, "etkilesim_orani": 3, "video_orani": .5,
                "biyografi": "montessori evde etkinlik", "son_basliklar": "kes yap"}]
        profil = puan.ideal_profil_uret(ort)
        self.assertEqual(profil["takipci_medyan"], 25000)
        self.assertIn("montessori", profil["anahtar_kelimeler"])
        p_benzer, b, _, _ = puan.puanla({"takipci": 25000, "etkilesim_orani": 3, "video_orani": .6,
                                         "biyografi": "montessori etkinlik anne 4 yaş",
                                         "son_paylasim": ortak.bugun(), "gonderi_30gun": 8},
                                        ideal=profil)
        self.assertIn("benzerlik", b)
        self.assertGreater(b["benzerlik"], 0.5)

    # --- DM taslağı + işaretleme
    def test_dm_taslagi_kisisel(self):
        s = gunluk.sablonlari_oku()
        metin = gunluk.dm_taslagi(self.havuz["elif.evdeoyun"], s["ilk_mesaj"])
        self.assertIn("Merhaba Elif!", metin)
        self.assertIn("3 yaş", metin)
        self.assertNotIn("{", metin, "doldurulmamış yer tutucu kalmamalı")
        with open(self.gun["brifing"], encoding="utf-8") as f:
            self.assertIn("@elif.evdeoyun", f.read())

    def test_isaretle_sonrasi_listeye_dusmez(self):
        sonuc = gunluk.isaretle(dosya=self.gun["csv"])
        self.assertEqual(sonuc["islenen"], 2)
        gecmis = {g["kullanici_adi"] for g in ortak.gecmis_oku()}
        self.assertIn("elif.evdeoyun", gecmis)
        ertesi = gunluk.liste_uret(hedef=50, tarih="2026-09-03")
        self.assertEqual(ertesi["secilen"], 0, "mesaj atılanlar ertesi gün gelmemeli")
        h = {a["kullanici_adi"]: a for a in ortak.havuz_oku()}
        self.assertEqual(h["elif.evdeoyun"]["durum"], "mesaj_atildi")
        # ortak video işaretle → ortaklar.txt'ye girer
        gunluk.isaretle(["elif.evdeoyun"], ortak_video=True)
        self.assertIn("elif.evdeoyun", ortak.satirlar(ortak.veri_yolu("ortaklar.txt")))




class HtmlExport(unittest.TestCase):
    """Instagram'ın HTML biçimli export'u da okunmalı."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["KESIF_VERI"] = self.tmp
        ortak.VERI = self.tmp
        self.sonuc = dm_gecmisi.analiz_et(os.path.join(ORNEK, "export_html"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_html_sohbetler_okunur(self):
        k = {r["kullanici_adi"]: r for r in self.sonuc["kayitlar"]}
        self.assertEqual(self.sonuc["ben"], "tikladers")
        self.assertIn("aysenur.etkinlik", k, "başlık kullanıcı adıysa noktalı hali korunmalı")
        self.assertIn("melisanne", k, "görünen ad kullanıcı adı değilse klasör adı kullanılmalı")
        a = k["aysenur.etkinlik"]
        self.assertEqual(a["cevap_verdi"], "evet")
        self.assertEqual(a["ilk_mesaj"], "2026-06-10", "Türkçe ay kısaltması + am/pm çözülmeli")
        self.assertGreaterEqual(a["_iz"], 2, "kargo/story ifadeleri işbirliği izi saymalı")
        self.assertTrue(a["_biz_basladik"])
        self.assertEqual(k["melisanne"]["cevap_verdi"], "hayır")

    def test_gorunen_ad_ile_eleme(self):
        """HTML export klasörleri görünen adla adlandırılır; kullanıcı adı
        farklı olsa bile görünen adı eşleşen aday 'daha önce yazıldı' sayılmalı."""
        dm_gecmisi.ice_aktar(os.path.join(ORNEK, "export_html"))
        adaylar = [
            {"kullanici_adi": "melisin.dunyasi", "ad": "Melis Anne", "takipci": 20000,
             "etkilesim_orani": 3, "biyografi": "anne etkinlik", "son_paylasim": ortak.bugun()},
            {"kullanici_adi": "yepyeni.anne", "ad": "Yepyeni Bir Anne", "takipci": 20000,
             "etkilesim_orani": 3, "biyografi": "anne etkinlik", "son_paylasim": ortak.bugun()},
        ]
        sonuc = {a["kullanici_adi"]: a for a in puan.havuzu_puanla(adaylar)}
        self.assertEqual(sonuc["melisin.dunyasi"]["durum"], "elendi")
        self.assertIn("görünen ad", sonuc["melisin.dunyasi"]["not"])
        self.assertNotEqual(sonuc["yepyeni.anne"]["durum"], "elendi")

    def test_reklam_yaniti_gelen_sayilir(self):
        k = {r["kullanici_adi"]: r for r in self.sonuc["kayitlar"]}
        self.assertIn("reklam", k)
        self.assertFalse(k["reklam"]["_biz_basladik"])
        self.assertEqual(k["reklam"]["kaynak"], "gelen_kutusu")


if __name__ == "__main__":
    unittest.main(verbosity=2)
