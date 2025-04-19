import sys
import os
import yt_dlp
import whisper
import torch
import ffmpeg
import threading
import subprocess
from datetime import timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog, 
                            QTextEdit, QProgressBar, QGroupBox, QMessageBox, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QClipboard

class VideoDownloadThread(QThread):
    progress_signal = pyqtSignal(str)
    download_progress = pyqtSignal(float)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, output_path):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.video_path = None

    def run(self):
        try:
            self.progress_signal.emit("Video indirme işlemi başlatıldı...")
            
            def my_hook(d):
                if d['status'] == 'downloading':
                    p = d.get('_percent_str', '0%')
                    p = p.replace('%', '')
                    try:
                        self.download_progress.emit(float(p))
                    except:
                        pass
                    self.progress_signal.emit(f"İndiriliyor: {p}%")
                elif d['status'] == 'finished':
                    self.progress_signal.emit(f"İndirme tamamlandı. Dönüştürülüyor...")

            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                'outtmpl': os.path.join(self.output_path, '%(title)s.%(ext)s'),
                'progress_hooks': [my_hook],
                'noplaylist': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                self.video_path = os.path.join(self.output_path, f"{info['title']}.mp4")
                
            self.finished_signal.emit(self.video_path)
            
        except Exception as e:
            self.error_signal.emit(f"Video indirme hatası: {str(e)}")

class WhisperTranscriptionThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, video_path, model_size, output_path):
        super().__init__()
        self.video_path = video_path
        self.model_size = model_size
        self.output_path = output_path

    def run(self):
        try:
            self.progress_signal.emit(f"Transkripsiyon başlatılıyor, model yükleniyor: {self.model_size}")
            # Whisper modelini yükle
            model = whisper.load_model(self.model_size)
            
            self.progress_signal.emit("Model yüklendi. Ses transkribe ediliyor...")
            
            # Whisper ile transkripsiyon yap
            result = model.transcribe(self.video_path, verbose=False)
            
            # Transkripsiyon sonucunu SRT formatında kaydet
            srt_path = os.path.splitext(self.video_path)[0] + ".srt"
            if self.output_path:
                srt_filename = os.path.basename(os.path.splitext(self.video_path)[0] + ".srt")
                srt_path = os.path.join(self.output_path, srt_filename)
            
            self.progress_signal.emit(f"Transkripsiyon tamamlandı. SRT dosyası oluşturuluyor: {srt_path}")
            
            with open(srt_path, "w", encoding="utf-8") as srt_file:
                i = 1
                for segment in result["segments"]:
                    # SRT formatı: sıra numarası, zaman aralıkları ve metin
                    start_time = str(timedelta(seconds=segment["start"]))[:-3].replace(".", ",")
                    end_time = str(timedelta(seconds=segment["end"]))[:-3].replace(".", ",")
                    text = segment["text"].strip()
                    
                    srt_file.write(f"{i}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{text}\n\n")
                    i += 1
            
            self.finished_signal.emit(srt_path)
            
        except Exception as e:
            self.error_signal.emit(f"Transkripsiyon hatası: {str(e)}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Ana pencere özelliklerini ayarla
        self.setWindowTitle("Vidwhis")
        self.setMinimumSize(800, 600)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana layout
        main_layout = QVBoxLayout(central_widget)
        
        # URL bölümü
        url_group = QGroupBox("Video URL")
        url_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Video URL'sini girin")
        
        self.paste_button = QPushButton("Yapıştır")
        self.paste_button.clicked.connect(self.paste_from_clipboard)
        
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.paste_button)
        
        url_group.setLayout(url_layout)
        main_layout.addWidget(url_group)
        
        # Yerel video seçme bölümü
        local_group = QGroupBox("Yerel Video")
        local_layout = QHBoxLayout()
        
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText("Yerel video dosyası seçin")
        self.local_path_input.setReadOnly(True)
        
        self.browse_button = QPushButton("Dosya Seç")
        self.browse_button.clicked.connect(self.browse_local_video)
        
        local_layout.addWidget(self.local_path_input)
        local_layout.addWidget(self.browse_button)
        
        local_group.setLayout(local_layout)
        main_layout.addWidget(local_group)
        
        # Model seçme bölümü
        model_group = QGroupBox("Whisper Model Seçimi")
        model_layout = QHBoxLayout()
        
        model_label = QLabel("Model:")
        self.model_selector = QComboBox()
        self.model_selector.addItems(["tiny", "base", "small", "medium", "medium.en", "large-v3", "turbo"])
        self.model_selector.setCurrentText("base")  # Varsayılan olarak base modeli seçili
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_selector)
        
        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)
        
        # Çıktı dizini seçme bölümü
        output_group = QGroupBox("Çıktı Konumu")
        output_layout = QHBoxLayout()
        
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Çıktı dizini seçin")
        self.output_path_input.setReadOnly(True)
        
        self.output_browse_button = QPushButton("Dizin Seç")
        self.output_browse_button.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(self.output_path_input)
        output_layout.addWidget(self.output_browse_button)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # İşlem butonları
        action_group = QGroupBox("İşlemler")
        action_layout = QHBoxLayout()
        
        self.download_button = QPushButton("İndir ve Transkribe Et")
        self.download_button.clicked.connect(self.start_download_transcribe)
        
        self.transcribe_button = QPushButton("Sadece Transkribe Et")
        self.transcribe_button.clicked.connect(self.start_transcribe_only)
        
        action_layout.addWidget(self.download_button)
        action_layout.addWidget(self.transcribe_button)
        
        action_group.setLayout(action_layout)
        main_layout.addWidget(action_group)
        
        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Log alanı
        log_group = QGroupBox("İşlem Günlüğü")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # Varsayılan çıktı yolunu ayarla
        self.output_path_input.setText(os.path.expanduser("~/Downloads"))
        
        # Thread değişkenleri
        self.download_thread = None
        self.transcribe_thread = None
        self.current_video_path = None
        
    def log_message(self, message):
        """Log mesajı ekler"""
        self.log_text.append(message)
        # Otomatik olarak aşağı kaydırma
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def paste_from_clipboard(self):
        """Panodan URL yapıştır"""
        clipboard = QApplication.clipboard()
        self.url_input.setText(clipboard.text())
    
    def browse_local_video(self):
        """Yerel video dosyası seç"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Video Dosyası Seç", 
            "", 
            "Video Dosyaları (*.mp4 *.avi *.mkv *.mov *.webm);;Tüm Dosyalar (*)"
        )
        
        if file_path:
            self.local_path_input.setText(file_path)
            self.current_video_path = file_path
    
    def browse_output_dir(self):
        """Çıktı dizini seç"""
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Çıktı Dizini Seç", 
            self.output_path_input.text() or os.path.expanduser("~")
        )
        
        if dir_path:
            self.output_path_input.setText(dir_path)
    
    def start_download_transcribe(self):
        """Video indir ve transkribe et"""
        url = self.url_input.text().strip()
        output_path = self.output_path_input.text()
        model_size = self.model_selector.currentText()
        
        if not url:
            QMessageBox.warning(self, "Hata", "Lütfen bir video URL'si girin.")
            return
        
        if not output_path:
            QMessageBox.warning(self, "Hata", "Lütfen bir çıktı dizini seçin.")
            return
        
        self.progress_bar.setValue(0)
        self.log_message(f"URL: {url}")
        self.log_message(f"Model: {model_size}")
        self.log_message(f"Çıktı dizini: {output_path}")
        
        # Download işlemi başlat
        self.download_thread = VideoDownloadThread(url, output_path)
        self.download_thread.progress_signal.connect(self.log_message)
        self.download_thread.download_progress.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        self.download_thread.error_signal.connect(self.log_message)
        
        self.download_thread.start()
        
        # Butonları devre dışı bırak
        self.download_button.setEnabled(False)
        self.transcribe_button.setEnabled(False)
    
    def start_transcribe_only(self):
        """Sadece transkripsiyon yap"""
        video_path = self.local_path_input.text()
        output_path = self.output_path_input.text()
        model_size = self.model_selector.currentText()
        
        if not video_path:
            QMessageBox.warning(self, "Hata", "Lütfen bir video dosyası seçin.")
            return
        
        if not output_path:
            output_path = os.path.dirname(video_path)
        
        self.progress_bar.setValue(0)
        self.log_message(f"Video: {video_path}")
        self.log_message(f"Model: {model_size}")
        self.log_message(f"Çıktı dizini: {output_path}")
        
        # Transkripsiyon işlemini başlat
        self.start_transcription(video_path, model_size, output_path)
    
    def on_download_finished(self, video_path):
        """Video indirme tamamlandığında çağrılır"""
        self.current_video_path = video_path
        self.log_message(f"Video indirme tamamlandı: {video_path}")
        
        # Transkripsiyon işlemini başlat
        output_path = self.output_path_input.text()
        model_size = self.model_selector.currentText()
        
        self.start_transcription(video_path, model_size, output_path)
    
    def start_transcription(self, video_path, model_size, output_path):
        """Transkripsiyon işlemini başlatır"""
        self.log_message("Transkripsiyon işlemi başlatılıyor...")
        
        self.transcribe_thread = WhisperTranscriptionThread(video_path, model_size, output_path)
        self.transcribe_thread.progress_signal.connect(self.log_message)
        self.transcribe_thread.finished_signal.connect(self.on_transcription_finished)
        self.transcribe_thread.error_signal.connect(self.log_message)
        
        self.transcribe_thread.start()
    
    def on_transcription_finished(self, srt_path):
        """Transkripsiyon tamamlandığında çağrılır"""
        self.log_message(f"Transkripsiyon tamamlandı: {srt_path}")
        self.progress_bar.setValue(100)
        
        QMessageBox.information(
            self, 
            "İşlem Tamamlandı", 
            f"Transkripsiyon işlemi tamamlandı.\nSRT dosyası: {srt_path}"
        )
        
        # Butonları etkinleştir
        self.download_button.setEnabled(True)
        self.transcribe_button.setEnabled(True)
    
    def update_progress(self, value):
        """İlerleme çubuğunu günceller"""
        self.progress_bar.setValue(int(value))

def check_dependencies():
    """Gerekli bağımlılıkları kontrol eder"""
    missing = []
    
    # FFmpeg kontrolü
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.SubprocessError, FileNotFoundError):
        missing.append("FFmpeg")
    
    # PyTorch kontrolü
    try:
        import torch
    except ImportError:
        missing.append("PyTorch")
    
    # Whisper kontrolü
    try:
        import whisper
    except ImportError:
        missing.append("OpenAI Whisper")
    
    # YT-DLP kontrolü
    try:
        import yt_dlp
    except ImportError:
        missing.append("yt-dlp")
    
    return missing

def main():
    app = QApplication(sys.argv)
    
    # Bağımlılıkları kontrol et
    missing_deps = check_dependencies()
    if missing_deps:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Eksik Bağımlılıklar")
        msg.setText(f"Aşağıdaki bağımlılıklar eksik:\n{', '.join(missing_deps)}")
        msg.setInformativeText("Lütfen eksik bağımlılıkları yükleyin ve tekrar deneyin.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        return
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
