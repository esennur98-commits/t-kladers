# Tıkladers Görsel Dil Rehberi

> 8 oyunun analizinden çıkarılmıştır: magic_potion, popsicle_sticks_sun,
> community_places_sort, letter_sorting_fruits, winter_pompom,
> animal_and_food, sandvic_oyunu, ponpon_kodlama.
> Masaüstü arşivi (50+ oyun) geldikçe güncellenecek.

## 1. İllüstrasyon stili (en belirleyici özellik)
- **Zengin, dokulu, hazır illüstrasyonlar** kullanılır: suluboya meyveler,
  sevimli suluboya hayvanlar (koala, maymun, penguen, kaplumbağa),
  detaylı flat-vektör sahneler (hastane, park, tren istasyonu).
- İllüstrasyonlarda **gölge, doku ve elle boyanmış his** vardır.
- ❌ ASLA: basit kodlanmış geometrik şekiller, kalın tek renk konturlu
  "çizilmiş" grafikler, diyagram görünümü.
- Karakterler sevimli/kawaii; bazen yüz eklenir (güneş yüzü, penguen).

## 2. Renk hikayesi: oyun başına TEK tema
Her oyunun tek baskın pastel atmosferi vardır; sayfa dolusu karışık renk yok:
- winter_pompom → buz mavisi monokrom + kar taneleri
- magic_potion → lavanta/mor yıldızlı gece + pembe bulutlar
- popsicle_sun → açık gökyüzü mavisi + beyaz bulutlar
- animal_and_food → krem/şeftali çerçeve + açık yeşil paneller
- letter_fruits → açık mavi zemin + pastel mozaik kenar şeritleri
Vurgu renkleri malzemeden gelir (meyve, jeton, desen); zemin sakindir.

## 3. Sayfa anatomisi
- **Logo**: her sayfada üst ortada, küçük (gerçek tıkladers logosu).
- **Kenar/çerçeve dekoru**: tema burada yaşar — köşelerde suluboya
  hayvanlar, kenarlarda mozaik şeritler, köşe penguenleri, kar taneleri.
- **İç alan**: sade, ferah çalışma alanı (beyaz/çok açık zemin panel).
- **Kapak**: tam sayfa tek kahraman illüstrasyon (piknik sepeti, iksir
  şişesi, güneş). Başlık metni genellikle YOK.

## 4. Kart ve bileşen dili
- Paneller çok yuvarlak köşeli; bazen tam hap/kapsül uçlu şeritler.
- Konturlar ince ya da hiç yok; ağır çizgi kullanılmaz.
- **Kesikli çizgi = kesim işareti** (kartların dışında, mavi/gri tonda).
- Jetonlar: beyaz daire içinde illüstrasyon, kesme için kesikli çember.
- Cevap alanları: boş beyaz kutu/daire, içerik hizasıyla birebir aynı boyut.

## 5. Metin kullanımı
- Neredeyse hiç metin yok; oyunlar okuma gerektirmez, yönerge görseldir.
- Harf/sayı gerektiğinde yumuşak rozet/düğme içinde tek karakter
  (letter_fruits'teki krem harf düğmeleri gibi).

## 6. Yapı şablonu (tipik 5-6 sayfa)
1. Kapak — kahraman illüstrasyon
2-5. Oyun sayfaları — kart gridleri / mat / çalışma şeritleri
6. Kesilecek parçalar — jetonlar/kartlar

## 7. Üretim notu (Claude için)
Kodla çizilmiş düz vektör bu dili YAKALAMAZ. Doğru yaklaşım:
- Zengin/suluboya öğeler: AI görsel üretimi (ör. higgsfield) veya
  Canva'nın kendi stok öğeleri; arka planlar yumuşak, dokulu.
- Mevcut bir tıkladers tasarımını `copy-design` ile çoğaltıp içinde
  `edit-design` ile çalışmak marka sürekliliği için en güvenli yol.
- Kesikli kesim çizgileri, logo konumu, panel yuvarlaklığı korunmalı.
