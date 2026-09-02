#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tıkladers influencer keşif — komut satırı.

    python3 -m kesif dm-analiz  <export_klasoru>   # DM geçmişini içe aktar + rapor
    python3 -m kesif manuel     <liste.txt>        # elle toplanan kullanıcı adları
    python3 -m kesif topla-graph                   # yorumcular + etiketleyenler (API)
    python3 -m kesif zenginlestir [--adet 60]      # takipçi/etkileşim verisi çek (API)
    python3 -m kesif ortaklar                      # ortak video yapanlardan ideal profil (API)
    python3 -m kesif gunluk [--hedef 50]           # günün listesi + DM taslakları
    python3 -m kesif isaretle --dosya veri/gunluk/2026-09-02.csv   # mesaj attım
    python3 -m kesif durum                         # havuz özeti
"""
import argparse
import sys

from . import ortak


def _yazdir(sozluk):
    for k, v in sozluk.items():
        if not str(k).startswith("_"):
            print(f"  {k}: {v}")


def cmd_dm_analiz(a):
    from . import dm_gecmisi
    s = dm_gecmisi.ice_aktar(a.export, a.ben)
    print(s["ozet"])
    print(f"\n→ {s['kisi']} kişi iletisim_gecmisi.csv'ye yazıldı; tam rapor: {s['rapor']}")


def cmd_manuel(a):
    from . import toplama
    _yazdir(toplama.manuel_ice_aktar(a.dosya, a.kaynak))


def cmd_topla_graph(a):
    from . import toplama
    _yazdir(toplama.graph_topla(a.gonderi, a.yorum))


def cmd_zenginlestir(a):
    from . import toplama
    _yazdir(toplama.zenginlestir(a.adet, a.yenile_gun))


def cmd_ortaklar(a):
    from . import toplama
    _yazdir(toplama.ortaklari_zenginlestir())


def cmd_gunluk(a):
    from . import gunluk
    s = gunluk.liste_uret(a.hedef, a.min_puan, a.sablon)
    _yazdir(s)
    if s["veri_eksik"]:
        print(f"\n! {s['veri_eksik']} kaydın verisi yok — önce `zenginlestir` çalıştır "
              f"ya da CSV'ye elle takipçi/etkileşim gir.")


def cmd_isaretle(a):
    from . import gunluk
    _yazdir(gunluk.isaretle(a.kullanici, a.dosya, a.ortak_video, a.not_))


def cmd_durum(_a):
    from collections import Counter
    havuz = ortak.havuz_oku()
    gecmis = ortak.gecmis_oku()
    print(f"  havuz: {len(havuz)} kayıt")
    for durum, n in Counter(h.get("durum") or "?" for h in havuz).most_common():
        print(f"    {durum}: {n}")
    for kaynak, n in Counter(h.get("kaynak") or "?" for h in havuz).most_common():
        print(f"    kaynak {kaynak}: {n}")
    verisiz = sum(1 for h in havuz if not ortak.sayi(h.get("takipci")))
    print(f"    verisi çekilmemiş: {verisiz}")
    cevap = sum(1 for g in gecmis if g.get("cevap_verdi") == "evet")
    print(f"  iletişim geçmişi: {len(gecmis)} kişi, {cevap} cevap, "
          f"{sum(1 for g in gecmis if g.get('ortak_video') == 'evet')} ortak video")
    print(f"  veri klasörü: {ortak.VERI}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="kesif", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = p.add_subparsers(dest="komut", required=True)

    s = alt.add_parser("dm-analiz", help="Instagram export'undan DM geçmişini çıkar")
    s.add_argument("export", help="'Bilgilerini indir' paketinin açıldığı klasör")
    s.add_argument("--ben", help="Kendi hesabımızın görünen adı (otomatik bulunur)")
    s.set_defaults(f=cmd_dm_analiz)

    s = alt.add_parser("manuel", help="elle toplanan kullanıcı adlarını havuza ekle")
    s.add_argument("dosya")
    s.add_argument("--kaynak", default="manuel", help="ör. hashtag:anneetkinlik")
    s.set_defaults(f=cmd_manuel)

    s = alt.add_parser("topla-graph", help="yorumcular + etiketleyenler (Graph API)")
    s.add_argument("--gonderi", type=int, default=15, help="kaç gönderiye bakılsın")
    s.add_argument("--yorum", type=int, default=50, help="gönderi başına kaç yorum")
    s.set_defaults(f=cmd_topla_graph)

    s = alt.add_parser("zenginlestir", help="havuzdaki hesapların verisini çek (Graph API)")
    s.add_argument("--adet", type=int, default=60)
    s.add_argument("--yenile-gun", type=int, default=30, help="kaç günden eski veri yenilensin")
    s.set_defaults(f=cmd_zenginlestir)

    s = alt.add_parser("ortaklar", help="ortaklar.txt'den ideal profil çıkar (Graph API)")
    s.set_defaults(f=cmd_ortaklar)

    s = alt.add_parser("gunluk", help="günün adayları + DM taslakları")
    s.add_argument("--hedef", type=int)
    s.add_argument("--min-puan", type=float)
    s.add_argument("--sablon", default="ilk_mesaj")
    s.set_defaults(f=cmd_gunluk)

    s = alt.add_parser("isaretle", help="mesaj attıklarını geçmişe yaz")
    s.add_argument("kullanici", nargs="*")
    s.add_argument("--dosya", help="günlük CSV ya da satır satır .txt")
    s.add_argument("--ortak-video", action="store_true", help="ortak video paylaşıldı")
    s.add_argument("--not", dest="not_", default="")
    s.set_defaults(f=cmd_isaretle)

    s = alt.add_parser("durum", help="havuz ve geçmiş özeti")
    s.set_defaults(f=cmd_durum)

    a = p.parse_args(argv)
    try:
        a.f(a)
    except Exception as e:  # kullanıcıya iz dökümü değil, tek satır hata
        print(f"HATA: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
