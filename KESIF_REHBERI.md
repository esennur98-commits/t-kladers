# Tıkladers Influencer Keşif Rehberi

> Amaç: Instagram'da 10-50 bin takipçili, 2-8 yaş çocuğu olan, kaliteli
> içerik üreten anneleri bulmak; oyun hediye edip video çekmelerini istemek.
> Hedef: her gün 50 yeni, puanlanmış, mesaj taslağı hazır aday.

## Önce dürüst bir cevap: şifre vermek gerekmiyor (ve vermemelisin)

- Instagram şifresiyle giriş yapan, DM atan, profil gezen otomasyonlar
  Instagram'ın kullanım koşullarına aykırı; **hesap kısıtlama/kapatma** ile
  sonuçlanıyor. Yılların takipçisini riske atmaya değmez.
- Bu araç şifre istemez. İki yasal kaynak kullanır:
  1. **Kendi verin** — Instagram'ın "Bilgilerini indir" paketi (DM geçmişi).
  2. **Resmi Graph API** — herkese açık işletme/içerik üretici hesap
     metrikleri, kendi gönderilerimizin yorumcuları, bizi etiketleyenler.
- Araç DM **göndermez**; taslak hazırlar, sen okuyup elle atarsın. Günde
  kaç kişiye yazacağın senin kararın; kişiselleştirilmiş 25-40 mesaj/gün
  üstünde spam filtresine takılma riski belirgin şekilde artar.

## Neyi ne kadar otomatik yapabiliriz?

| Adım | Otomatik mi? | Nasıl |
|---|---|---|
| Daha önce yazdıklarımızı çıkarma, cevap oranı, hangi açılış işe yaramış | ✅ tam | `dm-analiz` (export paketinden) |
| Ortak video yapanların ortak özelliklerini çıkarma (ideal profil) | ✅ tam | `ortaklar` (Graph API) |
| Yeni kullanıcı adı bulma | 🟡 yarı | yorumcular + etiketleyenler otomatik (`topla-graph`); hashtag/Keşfet taraması elle (`manuel`) |
| Takipçi/etkileşim/içerik verisini çekme | ✅ tam | `zenginlestir` (Graph API, sadece işletme/üretici hesaplar) |
| Puanlama, eleme, daha önce yazılanları ayıklama | ✅ tam | `gunluk` |
| Kişiye özel DM taslağı | ✅ tam | `gunluk` brifingi |
| DM gönderme | ❌ bilerek yok | sen gönderirsin |

API'nin vermediği tek şey "takipçi listesi" ve "benzer hesaplar". Bu yüzden
günde 50 aday için havuzun sürekli beslenmesi gerekir; aşağıda nasıl
15-20 dakikada 150+ ham kullanıcı adı toplanacağı anlatılıyor.

## Kurulum (5 dakika, bağımlılık yok)

```bash
python3 --version          # 3.9+ yeterli, pip'e gerek yok
python3 testler/test_akis.py   # örnek veriyle her şey çalışıyor mu
```

Kişisel veriler `veri/` klasöründe tutulur ve `.gitignore` ile repodan
dışlanmıştır. Başka bir klasör istersen: `export KESIF_VERI=/yol/veri`.

### 1) DM geçmişini içe aktar (bir kere, sonra ayda bir)

Instagram → Ayarlar → Hesaplar merkezi → Bilgileriniz ve izinleriniz →
Bilgilerini indir → **JSON** biçimi, "Mesajlar" seçili. Zip gelince aç:

```bash
python3 -m kesif dm-analiz ~/Downloads/instagram-tikladers-2026-09-02
```

Üretir:
- `veri/iletisim_gecmisi.csv` — kime ne zaman yazdık, cevap geldi mi
- `veri/rapor_dm.md` — cevap oranı, aylık dağılım, **hangi kelimeler cevap
  aldı / almadı**, işbirliğine dönmüş sohbetler

Bu liste "dokunulmaz"dır: buradaki kimse bir daha günlük listeye düşmez.

### 2) Ortak video paylaşanları tanımla

`veri/ortaklar.txt` dosyasına, bizimle ortak video paylaşmış hesapların
kullanıcı adlarını satır satır yaz (`rapor_dm.md` sonundaki liste yardımcı
olur). Graph API kuruluysa:

```bash
python3 -m kesif ortaklar
```

`veri/ideal_profil.json` üretir: ortakların takipçi/etkileşim medyanı ve
ortak kelime imzası. Puanlama bundan sonra "ortaklarımıza benzeyen"
adaylara ek puan verir.

### 3) Graph API kurulumu (şifresiz resmi yol, bir kere)

1. Instagram hesabı **İşletme** veya **İçerik Üretici** olmalı ve bir
   Facebook sayfasına bağlanmalı (Instagram → Ayarlar → Hesap türü).
2. developers.facebook.com → Uygulama oluştur → "İşletme" tipi →
   Instagram Graph API ürününü ekle.
3. Graph API Explorer'dan şu izinlerle jeton al: `instagram_basic`,
   `pages_show_list`, `instagram_manage_comments`. Jetonu "uzun ömürlü"
   jetona çevir (60 gün; süresi dolunca aynı yerden yenile).
4. Instagram işletme hesabı ID'sini bul:
   `GET /me/accounts?fields=instagram_business_account`
5. Terminale (şifre değil, jeton — repoya asla yazma):

```bash
export IG_KULLANICI_ID="1784140000000000"
export IG_JETON="EAAG...uzun jeton..."
```

### 4) Havuzu besle

```bash
# a) kendi gönderilerimizin yorumcuları + bizi etiketleyenler (en sıcak kaynak)
python3 -m kesif topla-graph --gonderi 20 --yorum 80

# b) elle toplanan hesaplar (hashtag/Keşfet gezerken kopyala, alt alta yapıştır)
python3 -m kesif manuel liste.txt --kaynak "hashtag:evdeetkinlik"
```

`liste.txt` şu biçimlerin hepsini kabul eder: `@ad`, `ad`, `instagram.com/ad`.

**Elle toplama nasıl hızlı olur (15-20 dk → 150+ ad):**
- Ortak video yapmış annelerin son videolarının **yorumcuları** ve o
  videoda **etiketlenen** hesaplar.
- Hashtag'ler: `#evdeetkinlik #okulöncesietkinlik #montessorianne
  #duyusaloyun #annebebek #anneçocuketkinlik #incemotor #kesyap
  #anaokuluetkinlik #evdeoyun` — "En iyi" değil **"Son"** sekmesi; küçük
  hesaplar orada.
- Bir iyi hesabın profilindeki "Önerilen hesaplar" oku (▾) — Instagram'ın
  kendi benzerlik motoru, ücretsiz.
- Rakip/benzer markaların (eğitici oyuncak, kitap) etiketlendiği gönderiler.

### 5) Verileri çek, puanla, günün listesini al

```bash
python3 -m kesif zenginlestir --adet 100   # API'den takipçi/etkileşim/başlıklar
python3 -m kesif gunluk --hedef 50         # puanla + brifing + DM taslakları
```

Çıktı: `veri/gunluk/2026-09-02.md` — her aday için puan, gerekçe, bio,
link ve kişiye özel DM taslağı; `veri/gunluk/2026-09-02.csv` — aynı liste
tablo olarak.

Graph API kurmadan da çalışır: `veri/havuz.csv`'ye takipçi/etkileşim
sütunlarını elle girersen puanlama aynı şekilde işler (örnek:
`ornek/havuz_ornek.csv`).

### 6) Mesaj attıklarını işaretle (her günün sonunda, 10 saniye)

```bash
python3 -m kesif isaretle --dosya veri/gunluk/2026-09-02.csv
# ya da tek tek:
python3 -m kesif isaretle elif.evdeoyun buse.anne
# ortak video paylaşıldığında:
python3 -m kesif isaretle elif.evdeoyun --ortak-video
```

İşaretlenmeyen adaylar ertesi gün listede **kalır** (kaybolmasın diye);
işaretlenenler bir daha asla gelmez.

## Günlük rutin (yaklaşık 30-40 dakika)

```
09:00  python3 -m kesif topla-graph          # 2 dk, otomatik
09:05  15 dk hashtag/yorumcu taraması → liste.txt → python3 -m kesif manuel liste.txt
09:20  python3 -m kesif zenginlestir --adet 150
09:25  python3 -m kesif gunluk --hedef 50    # brifingi aç
09:30  brifingden mesajları oku, kişiselleştir, gönder
gün sonu  python3 -m kesif isaretle --dosya veri/gunluk/BUGUN.csv
haftada 1 python3 -m kesif durum + rapor_dm.md'ye bak, kriterler.json'u ayarla
```

Havuz büyüdükçe elle tarama ihtiyacı azalır: ortak videoların altına
gelen her yorumcu ertesi sabah otomatik havuza düşer.

## Puanlama nasıl çalışıyor? (`kriterler.json`'dan ayarlanır)

| Bileşen | Ağırlık | Ne ölçer |
|---|---|---|
| takipçi | 20 | 15-35k ideal; 10-50k dışı **elenir** |
| etkileşim | 25 | (beğeni+yorum)/takipçi; %3.5+ tam puan, %1 altı **elenir** |
| içerik | 18 | bio+son başlıklarda anne / etkinlik / montessori / okul öncesi kelimeleri |
| yaş uyumu | 12 | "3 yaş", "okul öncesi", "anasınıfı" gibi 2-8 yaş izleri; hamile/ergen izi + yaş izi yok → **elenir** |
| video | 10 | son gönderilerde Reels oranı (bizden istenen çıktı video) |
| aktiflik | 8 | son paylaşım tazeliği + 30 günde gönderi; 21+ gün sessiz → **elenir** |
| benzerlik | 15 | ortak video yaptıklarımızın kelime imzasına yakınlık (ideal_profil varsa) |

Cezalar: reklam oranı %40+ (−10), %70+ elenir; satış/butik/sipariş
kelimeleri (−10/−20); takip ettiği > takipçi (−5).
Daha önce mesaj attığımız herkes otomatik elenir.

Her aday için "neden" satırı brifingde yazar — puanı körü körüne değil,
bakarak kullan. Kriterleri değiştirmek için sadece `kriterler.json`'u
düzenle, kod dokunma.

## DM şablonları

`kesif/sablonlar/dm.md` içinde 4 şablon: `ilk_mesaj`, `hatirlatma`,
`kabul_sonrasi`, `video_sonrasi`. Yer tutucular: `{ad}`, `{kanca}` (adayın
içeriğinden çıkarılan konu), `{yas}`, `{kullanici}`.
`python3 -m kesif gunluk --sablon hatirlatma` ile diğer şablonla üretilir.

Yasal not: hediye karşılığı paylaşımlar Türkiye'de Reklam Kurulu
düzenlemesine göre `#işbirliği` etiketiyle işaretlenmeli; `kabul_sonrasi`
şablonu bunu anneye hatırlatır.

## Dosyalar

```
kriterler.json          kriterler ve ağırlıklar (tek ayar dosyası)
kesif/                  araç (Python 3, dış bağımlılık yok)
  dm_gecmisi.py         export → iletişim geçmişi + rapor
  graph.py              Instagram Graph API istemcisi
  toplama.py            havuz besleme + zenginleştirme + ideal profil
  puan.py               puanlama motoru
  gunluk.py             günün listesi + DM taslakları + işaretleme
  sablonlar/dm.md       DM şablonları
ornek/                  örnek export + örnek havuz (test/deneme için)
testler/test_akis.py    uçtan uca test (API'siz)
veri/                   SENİN verin — repoya girmez (.gitignore)
```
