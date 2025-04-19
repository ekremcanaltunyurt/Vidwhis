# Vidwhis

Bu uygulama, herhangi bir URL'den video indirme ve OpenAI Whisper modeli kullanarak otomatik olarak İngilizce altyazı (SRT) dosyası oluşturma işlevselliği sağlar.

## Özellikler

- Herhangi bir video URL'sinden en yüksek kalitede video indirme
- YouTube ve diğer popüler video platformlarından indirme desteği (yt-dlp kullanarak)
- Yerel video dosyalarından transkripsiyon yapabilme
- OpenAI Whisper modeli ile konuşma tanıma ve altyazı oluşturma

## Kurulum

1. Aşağıdaki bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

2. [FFmpeg](https://ffmpeg.org/download.html) yüklü olmalıdır. Windows için [FFmpeg indir](https://www.gyan.dev/ffmpeg/builds/) adresinden indirebilirsiniz.

## Kullanım

Uygulamayı başlatmak için:

```bash
python main.py
```

### Video İndirme ve Transkripsiyon

1. "Video URL" alanına video bağlantısını girin veya "Yapıştır" düğmesine tıklayarak panodaki bağlantıyı yapıştırın.
2. "Whisper Model Seçimi" açılır menüsünden istediğiniz model boyutunu seçin.
3. "Çıktı Konumu" bölümünden dosyaların kaydedileceği dizini seçin.
4. "İndir ve Transkribe Et" düğmesine tıklayın.

### Yerel Video Dosyası Transkripsiyon

1. "Yerel Video" bölümünde "Dosya Seç" düğmesine tıklayarak bilgisayarınızdaki bir video dosyasını seçin.
2. İstediğiniz Whisper modelini seçin.
3. Çıktı konumunu belirleyin.
4. "Sadece Transkribe Et" düğmesine tıklayın.

## Whisper Modelleri

- **tiny**: En küçük model, hızlı ama daha az doğru
- **base**: Temel model, iyi bir hız/doğruluk dengesi
- **small**: Orta boyutlu model, daha iyi doğruluk
- **medium**: Büyük model, yüksek doğruluk
- **large-v3**: En büyük ve en doğru model, ancak en yavaş olanı
- **turbo**: En büyük ve en doğru model, ancak daha hızlı ama daha az doğru

## Gereksinimler

- Python 3.7+
- PyQt6
- OpenAI Whisper
- yt-dlp
- FFmpeg
- PyTorch
