# Tentivory-Anti-RAT-TOOL

> UYARI (ÖNEMLİ — DİKKATLE OKUYUN)
>
> Bu araçların yetkisiz veya izinsiz kullanımı ciddi hukuki sonuçlar doğurabilir. Bu depo ve içindeki araçlar yalnızca
> - yazılı izin verilmiş olay müdahalesi,
> - doğrudan yetki verilmiş güvenlik araştırması veya
> - eğitim/deneme amaçlı izole ortamlarda
> kullanım içindir. Herhangi bir hedefe karşı işlem yapmadan önce aşağıdakileri sağlayın:
>
> 1. Hedef sistemin sahibi veya yetkilisinden yazılı izin (e-posta/kontrat) alınmış olmalıdır.
> 2. Gerçek müdahale veya hedefe yönelik değişiklikler yapmadan önce `--dry-run` kullanarak etkiyi doğrulayın.
> 3. Gerçek işlem gerçekleştirilmeden önce en az bir onaylayıcı (2. onay) ve operasyonel kayıt (audit log) bulundurun.
> 4. Toplu/otomatik işlemler öncesi hizmet sağlayıcıların (Discord, Telegram) kullanım koşullarını ve rate-limit politikalarını kontrol edin.
> 5. Hukuki belirsizlik durumunda veya şüphede mutlaka bir hukuk danışmanına başvurun.
>
> Bu gerekliliklerin yerine getirilmemesi durumunda yazar/maintainer sorumluluk kabul etmez; izinsiz kullanım raporlanacak ve gerekli hukuki adımlar atılacaktır.

Bu depo, Discord ve Telegram üzerinden veri çalan RAT (Remote Access Trojan) türevlerinin haberleşme hattı (Webhook/Token) öğelerini tespit edip etkisiz hale getirmeye yardımcı olmak üzere eğitim ve savunma amaçlı geliştirilmiş araçları içerir.

## Yenilikler (önerilen iyileştirmeler)
- Dry-run (test) modu: Gerçek tahribat yapmadan hangi hedeflerin etkilenebileceğini görmek için kullanılır.
- Girdi doğrulama ve maskeleme: Webhook URL'leri ve token formatları doğrulanır; günlüklerde tam gizli bilgiler gösterilmez.
- Non-interactive (CLI) kullanım: Otomasyon için `--discord`, `--telegram`, `--auto` gibi bayraklar eklendi veya eklenebilir.
- Hata yönetimi: Ağ zaman aşımı, istisnalar ve hata geri bildirimleri ele alınmalı/ele alındı.
- Toplu işlem desteği: Otomatik deşifre edilen hedefleri sınırlı paralellik ile toplu işlemek mümkün.

(Ana dosyada bu özelliklerden bazıları uygulanmış veya uygulanmaya hazır hale getirilmiştir; detaylar için `TENTİVORY-RAT-İMHA.py` dosyasını inceleyin.)

## Kurulum
1. Python 3.8+ yüklü olduğundan emin olun.
2. Gerekli kütüphaneleri yükleyin:

```bash
pip install -r requirements.txt
# veya (küçük proje için)
pip install aiohttp rich
```

## Hızlı kullanım
Etkileşimli modda çalıştırmak için:

```bash
python TENTİVORY-RAT-İMHA.py
```

Non-interactive (komut satırı) örnekleri:

- Tek bir Discord webhook'u test et (dry-run):

```bash
python TENTİVORY-RAT-İMHA.py --discord "https://discord.com/api/webhooks/ID/TOKEN" --dry-run
```

- Tek bir Telegram bot token'ını silme denemesi (onay istenmeyecek):

```bash
python TENTİVORY-RAT-İMHA.py --telegram "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11" --yes
```

- Otomatik deşifre ve toplu işlem (varsayılan paralellik 4):

```bash
python TENTİVORY-RAT-İMHA.py --auto
```

- Paralel işçi sayısını ayarlama:

```bash
python TENTİVORY-RAT-İMHA.py --auto --concurrency 8
```

## Kritik kullanım talimatları ve sorumluluk
- Her zaman önce `--dry-run` ile çalıştırın; gerçek etkileri gözlemlemeden doğrudan silme/spam işlemi başlatmayın.
- `--yes` bayrağını yalnızca yazılı izin sahibiyseniz ve gerekli onay süreçleri tamamlandıysa kullanın.
- Loglama yapılırken tam token/webhook bilgilerini göstermeyin; araç maskelenmiş çıktılar üretmelidir.
- Ağ çağrıları için uygun zaman aşımları ve yeniden deneme (retry) mantığı kullanın; 429 (Rate Limit) durumunda `Retry-After` başlığına uyun.
- Hizmet sağlayıcılarının (Discord/Telegram) politikalarına uyun; toplu veya otomatik istekler rate limit'e, IP bloklamaya veya hesap yaptırımlarına yol açabilir.

## Geliştirme ve Test
- Birim testleri: Validation fonksiyonları, `dry-run` davranışı ve wrapper'lar için test yazılması önerilir.
- Ağ çağrılarını kullanan kodlar için entegrasyon testleri yerine simüle edilmiş/mock ortamlar kullanın.

## Katkıda bulunma
- Katkılar hoş karşılanır; lütfen öncelikle bir issue açın ve planınızı tartışın.
- Güvenlik açığı bildirimleri için doğrudan repo sahibi ile iletişime geçin; yanlış kullanım raporlamaları hassasiyetle ele alınacaktır.

## Lisans
Bu proje için repo sahibi tarafından eklenen lisans: `LICENSE` dosyasında "All Rights Reserved" bildirimi bulunmaktadır. Yetkisiz kopyalama, dağıtım veya türev yapma yasaktır. İzin talepleri için repo sahibi ile iletişime geçin.

## İletişim
Sorular, hatalar veya sorumluluk bildirimleri için repo sahibi ile GitHub üzerinden iletişime geçin.
