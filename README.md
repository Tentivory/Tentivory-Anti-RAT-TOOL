# Tentivory-Anti-RAT-TOOL

Bu depo, Discord ve Telegram üzerinden veri çalan RAT (Remote Access Trojan) türevlerinin haberleşme hattı (Webhook/Token) öğelerini tespit edip etkisiz hale getirmeye yardımcı olmak üzere eğitim ve savunma amaçlı geliştirilmiş araçları içerir.

Önemli: Bu araçlar yalnızca yasal yetki ve izin altında, güvenlik araştırması, olay müdahalesi veya eğitim amaçlı kullanılmalıdır. Yetkisiz kullanım suç teşkil edebilir. Kullanıcılar yerel yasalarına, hizmet sağlayıcılarının kullanım koşullarına ve etik kurallara uymaktan sorumludur.

## Yenilikler (önerilen iyileştirmeler)
- Dry-run (test) modu: Gerçek tahribat yapmadan hangi hedeflerin etkilenebileceğini görmek için kullanılır.
- Girdi doğrulama ve maskeleme: Webhook URL'leri ve token formatları doğrulanır; günlüklerde tam gizli bilgiler gösterilmez.
- Non-interactive (CLI) kullanım: Otomasyon için `--discord`, `--telegram`, `--auto` gibi bayraklar eklendi.
- Hata yönetimi: Ağ zaman aşımı, istisnalar ve hata geri bildirimleri ele alınmalı/ele alındı.
- Toplu işlem desteği: Otomatik deşifre edilen hedefleri sınırlı paralellik ile toplu işlemek mümkün.

(Ana dosyada bu özelliklerden bazıları uygulanmış veya uygulanmaya hazır hale getirilmiştir; detaylar için `TENTİVORY-RAT-İMHA.py` dosyasını inceleyin.)

## Kurulum
1. Python 3.8+ yüklü olduğundan emin olun.
2. Gerekli kütüphaneleri yükleyin:

```bash
pip install -r requirements.txt
# veya (küçük proje için)
pip install rich requests
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

## Önerilen kullanım ve güvenlik
- Önce `--dry-run` ile çalıştırarak hedeflerin doğruluğunu ve etkiyi gözlemleyin.
- Üretim/gerçek operasyonlarda `--yes` bayrağını yalnızca tam yetkili olduğunuz durumlarda kullanın.
- Loglama yapılırken tam token/webhook bilgilerini göstermeyin; araç maskelenmiş çıktılar üretmelidir.
- Ağ çağrıları için uygun zaman aşımları ve yeniden deneme (retry) mantığı uygulayın.
- Hizmet sağlayıcılarının (Discord/Telegram) kullanım koşullarına uymaya dikkat edin; toplu veya otomatik istekler rate limit'e takılabilir.

## Geliştirme ve Test
- Birim testleri: Validation fonksiyonları, `dry-run` davranışı ve wrapper'lar için test yazılması önerilir.
- Ağ çağrılarını kullanan kodlar için entegrasyon testleri yerine simüle edilmiş/mock ortamlar kullanın.

## Katkıda bulunma
- Katkılar hoş karşılanır; lütfen öncelikle bir issue açın ve planınızı tartışın.
- Güvenlik açığı bildirimleri için doğrudan repo sahibi ile iletişime geçin; yanlış kullanım raporlamaları hassasiyetle ele alınacaktır.

## Lisans
Bu projede açıkça belirtilmiş bir lisans yoksa, araçların kullanımı ve paylaşımıyla ilgili açık izin almadığınız sürece dikkatli olunuz. Bir lisans eklenmesi önerilir (ör. MIT, Apache-2.0) ve yasal sorumlulukların netleştirilmesi tavsiye edilir.

## İletişim
Sorular, hatalar veya sorumluluk bildirimleri için repo sahibi ile GitHub üzerinden iletişime geçin.
