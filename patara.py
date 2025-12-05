# ==============================================================================
#               PATARA BİLİMSEL VERİ PLATFORMU v1.3 (Final)
# ==============================================================================
# Geliştirici: Ege Kaan Yükün
# Akademik Danışman: Prof. Dr. Eyüp Başkale
# Tarih: 16.07.2025
#
# Açıklama: Bu uygulama, Patara sahilindeki Caretta caretta yuvalama
# verilerinin coğrafi olarak kaydedilmesi, yönetilmesi, analiz edilmesi
# ve raporlanması için geliştirilmiş bir masaüstü platformudur.
# ==============================================================================

# ------------------------------------------------------------------------------
# BÖLÜM 1: GEREKLİ KÜTÜPHANELER
# ------------------------------------------------------------------------------
import sys
import os
import io
import json
import sqlite3
import pandas as pd
import numpy as np
import folium
import matplotlib

matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import shutil
from datetime import datetime
import logging
import time
import geopandas as gpd
from shapely.geometry import Point, Polygon
import folium.plugins as plugins

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QDialog, QLineEdit, QFormLayout,
                             QDialogButtonBox, QMessageBox, QComboBox, QLabel,
                             QCheckBox, QGroupBox, QHBoxLayout, QListWidget, QListWidgetItem,
                             QScrollArea, QFileDialog, QDateEdit, QMenuBar, QMenu,
                             QSplashScreen, QStyle, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, QDate, QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QPixmap, QColor, QActionGroup

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.colors import navy, green, red

# ------------------------------------------------------------------------------
# BÖLÜM 2: GLOBAL AYARLAR VE YARDIMCI FONKSİYONLAR
# ------------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "caretta_final.db")


def load_config():
    """
    Uygulama ayarlarını 'config.json' dosyasından yükler.
    Dosya yoksa, varsayılan ayarlarla oluşturur.
    """
    config_yolu = os.path.join(SCRIPT_DIR, "config.json")
    try:
        if not os.path.exists(config_yolu):
            varsayilan_config = {
                "sabit_lejantlar": {
                    "dağ": [36.2486, 29.3157], "işletme": [36.2524, 29.3127], "info": [36.2534, 29.3121],
                    "çalılıklar": [36.2546, 29.3109], "fener": [36.2578, 29.3078], "kum tepesi": [36.2654, 29.2997],
                    "bayrak": [36.2750, 29.2887], "kamp alanı": [36.2762, 29.2858], "çay sonu": [36.2791, 29.2806],
                    "çay ortası": [36.2819, 29.2764], "çay başı": [36.2906, 29.2651], "bitiş": [36.2933, 29.2631]
                }
            }
            with open(config_yolu, 'w', encoding='utf-8') as f:
                json.dump(varsayilan_config, f, indent=2, ensure_ascii=False)
            return varsayilan_config
        else:
            with open(config_yolu, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"HATA: config.json okunamadı veya oluşturulamadı: {e}")
        return {"sabit_lejantlar": {}}


def setup_logging():
    """
    Uygulama aktivitelerini ve hatalarını 'activity_log.txt' dosyasına kaydetmek
    için loglama sistemini kurar.
    """
    log_dosyasi = os.path.join(SCRIPT_DIR, "activity_log.txt")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_dosyasi, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def create_pdf_report(dosya_yolu, baslik, icerik_listesi, grafik_yolu=None):
    """
    Verilen bilgilerle standart bir PDF raporu oluşturur.
    """
    try:
        c = canvas.Canvas(dosya_yolu, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 1 * inch, baslik)
        c.setFont("Helvetica", 9)
        rapor_tarihi = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        c.drawString(inch, height - 1.25 * inch, f"Rapor Tarihi: {rapor_tarihi}")

        styles = getSampleStyleSheet()
        style_normal = styles['Normal']
        style_bold = styles['h5']

        y_pozisyonu = height - 2 * inch
        for etiket, deger, renk in icerik_listesi:
            if y_pozisyonu < 1.5 * inch:
                c.showPage()
                y_pozisyonu = height - 1 * inch

            p_etiket = Paragraph(etiket, style_normal)
            p_etiket.wrapOn(c, 2.5 * inch, 1 * inch)
            p_etiket.drawOn(c, 1 * inch, y_pozisyonu)

            p_deger = Paragraph(f'<font color="{renk}">{deger}</font>', style_bold)
            p_deger.wrapOn(c, 4 * inch, 1 * inch)
            p_deger.drawOn(c, 3.5 * inch, y_pozisyonu)

            y_pozisyonu -= 0.3 * inch

        if grafik_yolu and os.path.exists(grafik_yolu):
            if y_pozisyonu < 5 * inch:
                c.showPage()
                y_pozisyonu = height - 1 * inch
            c.drawImage(grafik_yolu, 1 * inch, y_pozisyonu - 4.5 * inch, width=6.5 * inch, height=4 * inch,
                        preserveAspectRatio=True)

        c.save()
        return True, "PDF raporu başarıyla oluşturuldu."
    except Exception as e:
        return False, f"PDF oluşturulurken bir hata oluştu: {e}"


# --- Veritabanı Fonksiyonları ---

def get_connection():
    """Veritabanı bağlantısı oluşturur."""
    return sqlite3.connect(DB_PATH)


def setup_database():
    """Veritabanını ve 'yuvalar' tablosunu Yıllık ID şemasıyla kurar."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS yuvalar (
        id INTEGER NOT NULL, yil INTEGER NOT NULL, lat REAL, lon REAL, yuva_tarihi TEXT, 
        ilk_yavru_cikis_tarihi TEXT, ikinci_predasyon_tarihi TEXT, kuru_kum_uzakligi REAL, 
        yari_islak_kum_uzakligi REAL, islak_kum_uzakligi REAL, toplam_denize_uzaklik REAL, 
        tasinma_durumu TEXT, sicaklik_aleti_var_mi TEXT, kulucka_suresi_gun INTEGER, 
        yuva_basarisi_yuzde REAL, predasyon_durumu TEXT, predator_canli_listesi TEXT, marka TEXT, 
        yuva_derinligi REAL, yuva_capi REAL, yuva_ici_canli_yavru INTEGER, yuva_ici_olu_yavru INTEGER, 
        erken_donem_embriyo INTEGER, orta_donem_embriyo INTEGER, gec_donem_embriyo INTEGER, 
        toplam_olu_embriyo INTEGER, bos_kabuk_sayisi INTEGER, predasyonlu_yumurta_sayisi INTEGER,
        dollenmemis_yumurta_sayisi INTEGER, toplam_yumurta_sayisi INTEGER,
        yavru_cikis_gun_1 INTEGER, yavru_cikis_gun_2 INTEGER, yavru_cikis_gun_3 INTEGER,
        PRIMARY KEY (id, yil)
    )""")
    conn.commit()
    conn.close()
    logging.info("Veritabanı şeması (yıl bilgisiyle) kuruldu/kontrol edildi.")


def excelden_toplu_ekle(excel_dosya_yolu):
    """Excel dosyasından toplu veri aktarımı yapar, Yıllık ID sistemini dikkate alır."""
    try:
        df = pd.read_excel(excel_dosya_yolu, engine='openpyxl')
        df = df.where(pd.notna(df), None)
        df.columns = [
            str(col).strip().lower().replace(' ', '_').replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace(
                'ş', 's').replace('ö', 'o').replace('ç', 'c').replace('(', '').replace(')', '').replace('.', '') for col
            in df.columns]

        if 'yuva_tarihi' not in df.columns: return 0, "Excel'de 'yuva_tarihi' sütunu bulunamadı."

        df['yuva_tarihi'] = pd.to_datetime(df['yuva_tarihi'], errors='coerce')
        df.dropna(subset=['yuva_tarihi'], inplace=True)
        df['yil'] = df['yuva_tarihi'].dt.year.astype(int)

        id_key = next((k for k in ['id', 'yuva_sira_no', 'yuva_no'] if k in df.columns), None)
        if id_key is None: return 0, "Excel'de 'id' sütunu bulunamadı."
        if id_key != 'id': df['id'] = df[id_key]
        df.dropna(subset=['id'], inplace=True)
        df['id'] = df['id'].astype(int)

        conn = get_connection()
        mevcut_df = pd.read_sql_query("SELECT id, yil FROM yuvalar", conn)
        mevcut_kombinasyonlar = set(tuple(x) for x in mevcut_df.to_numpy())

        yeni_kayitlar = [row.to_dict() for index, row in df.iterrows() if
                         (row['id'], row['yil']) not in mevcut_kombinasyonlar]
        if not yeni_kayitlar:
            conn.close()
            return 0, "Excel'de yeni bir (ID, Yıl) kombinasyonu bulunamadı."

        yeni_df = pd.DataFrame(yeni_kayitlar)
        if 'yuva_ici_canli_yavru' in yeni_df.columns and 'toplam_yumurta_sayisi' in yeni_df.columns:
            canli = pd.to_numeric(yeni_df['yuva_ici_canli_yavru'], errors='coerce').fillna(0)
            toplam = pd.to_numeric(yeni_df['toplam_yumurta_sayisi'], errors='coerce').fillna(0)
            yeni_df['yuva_basarisi_yuzde'] = np.divide(canli * 100, toplam, out=np.zeros_like(canli, dtype=float),
                                                       where=toplam != 0).round(2)

        yeni_df['yuva_tarihi'] = yeni_df['yuva_tarihi'].dt.strftime('%Y-%m-%d')

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(yuvalar)")
        db_sutunlar = {row[1] for row in cursor.fetchall()}

        eklenecek_df = yeni_df[[col for col in yeni_df.columns if col in db_sutunlar]]

        eklenecek_df.to_sql('yuvalar', conn, if_exists='append', index=False)
        conn.close()
        return len(eklenecek_df), f"{len(eklenecek_df)} yeni kayıt başarıyla eklendi."
    except Exception as e:
        logging.error(f"Excel aktarım hatası: {e}", exc_info=True)
        return 0, f"Excel aktarım hatası: {e}"


def yuva_var_mi(id, yil):
    """Belirtilen ID ve YIL kombinasyonunun veritabanında olup olmadığını kontrol eder."""
    conn = get_connection();
    cursor = conn.cursor();
    cursor.execute("SELECT 1 FROM yuvalar WHERE id = ? AND yil = ?", (id, yil));
    result = cursor.fetchone();
    conn.close();
    return result is not None


def yuva_ekle(yuva_verisi):
    """Verilen yuva verisini, 'yil' sütununu otomatik ekleyerek kaydeder."""
    conn = get_connection();
    cursor = conn.cursor()
    if 'yuva_tarihi' in yuva_verisi and yuva_verisi['yuva_tarihi']:
        try:
            yuva_verisi['yil'] = datetime.strptime(yuva_verisi['yuva_tarihi'], '%Y-%m-%d').year
        except (ValueError, TypeError):
            logging.error(f"Geçersiz tarih: {yuva_verisi['yuva_tarihi']}."); conn.close(); return

    sutunlar_list = [k for k, v in yuva_verisi.items() if v is not None]
    degerler = [v for k, v in yuva_verisi.items() if v is not None]
    if 'yil' not in sutunlar_list: logging.error("Yuva verisinde 'yil' bilgisi eksik."); conn.close(); return

    sutunlar = ', '.join(sutunlar_list);
    yer_tutucular = ', '.join(['?'] * len(sutunlar_list))
    try:
        cursor.execute(f"INSERT INTO yuvalar ({sutunlar}) VALUES ({yer_tutucular})", degerler); conn.commit()
    except sqlite3.IntegrityError:
        logging.error(f"Bileşik anahtar hatası: ID {yuva_verisi.get('id')} YIL {yuva_verisi.get('yil')} zaten mevcut.")
    finally:
        conn.close()


def yuva_predasyon_guncelle(id, yil, durum, turler):
    """Belirtilen ID ve YIL'a ait yuvanın predasyon durumunu günceller."""
    conn = get_connection();
    cursor = conn.cursor();
    turler_json = json.dumps(turler)
    cursor.execute("UPDATE yuvalar SET predasyon_durumu = ?, predator_canli_listesi = ? WHERE id = ? AND yil = ?",
                   (durum, turler_json, id, yil));
    conn.commit();
    conn.close()


def toplu_yuva_sil(yuva_kombinasyonlari):
    """Verilen (id, yil) listesindeki tüm yuvaları tek bir sorguyla siler."""
    if not yuva_kombinasyonlari: return
    conn = get_connection();
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE TEMP TABLE silinecek_yuvalar (id INTEGER, yil INTEGER)")
        cursor.executemany("INSERT INTO silinecek_yuvalar (id, yil) VALUES (?, ?)", yuva_kombinasyonlari)
        cursor.execute("DELETE FROM yuvalar WHERE (id, yil) IN (SELECT id, yil FROM silinecek_yuvalar)")
        cursor.execute("DROP TABLE silinecek_yuvalar")
        conn.commit()
    except Exception as e:
        conn.rollback(); logging.error(f"Toplu silme hatası: {e}", exc_info=True)
    finally:
        conn.close()


def tum_yuvalari_getir():
    """Tüm yuva kayıtlarını veritabanından çeker."""
    conn = get_connection();
    conn.row_factory = sqlite3.Row;
    cursor = conn.cursor();
    cursor.execute("SELECT * FROM yuvalar");
    yuvalar = [dict(row) for row in cursor.fetchall()]
    for yuva in yuvalar:
        if 'predator_canli_listesi' in yuva and yuva['predator_canli_listesi']:
            try:
                yuva['predator_canli_listesi'] = json.loads(yuva['predator_canli_listesi'])
            except (json.JSONDecodeError, TypeError):
                yuva['predator_canli_listesi'] = []
        else:
            yuva['predator_canli_listesi'] = []
    conn.close();
    return yuvalar


def yuvalari_dataframe_yap():
    """Tüm yuva kayıtlarını bir Pandas DataFrame'ine dönüştürür."""
    conn = get_connection();
    df = pd.read_sql_query("SELECT * FROM yuvalar", conn);
    conn.close()
    if not df.empty and 'predator_canli_listesi' in df.columns:
        df['predator_canli_listesi'] = df['predator_canli_listesi'].apply(
            lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else [])
    return df
# ------------------------------------------------------------------------------
# 3. BÖLÜM: ARAYÜZ SINIFLARI (TÜM DIALOG PENCERELERİ)
# ------------------------------------------------------------------------------

class YuvaEkleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Yuva Kaydı Ekle")
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        form_widget = QWidget()
        self.form_layout = QFormLayout(form_widget)

        self.inputs = {
            "id": QLineEdit(), "lat": QLineEdit(), "lon": QLineEdit(), "yuva_tarihi": QDateEdit(QDate.currentDate()),
            "ilk_yavru_cikis_tarihi": QDateEdit(QDate.currentDate()),
            "ikinci_predasyon_tarihi": QDateEdit(QDate.currentDate()),
            "kuru_kum_uzakligi": QLineEdit(), "yari_islak_kum_uzakligi": QLineEdit(), "islak_kum_uzakligi": QLineEdit(),
            "toplam_denize_uzaklik": QLineEdit(), "tasinma_durumu": QCheckBox("Evet"),
            "sicaklik_aleti_var_mi": QCheckBox("Var"),
            "kulucka_suresi_gun": QLineEdit(), "marka": QLineEdit(), "yuva_derinligi": QLineEdit(),
            "yuva_capi": QLineEdit(),
            "yuva_ici_canli_yavru": QLineEdit(), "yuva_ici_olu_yavru": QLineEdit(), "erken_donem_embriyo": QLineEdit(),
            "orta_donem_embriyo": QLineEdit(), "gec_donem_embriyo": QLineEdit(), "toplam_olu_embriyo": QLineEdit(),
            "bos_kabuk_sayisi": QLineEdit(), "predasyonlu_yumurta_sayisi": QLineEdit(),
            "dollenmemis_yumurta_sayisi": QLineEdit(),
            "toplam_yumurta_sayisi": QLineEdit(),

            "yavru_cikis_gun_1": QLineEdit(), "yavru_cikis_gun_2": QLineEdit(), "yavru_cikis_gun_3": QLineEdit()
        }

        # Temel Bilgiler Grubu
        self.form_layout.addRow(QLabel("<b>--- Temel Bilgiler (Zorunlu) ---</b>"))
        self.form_layout.addRow("Yuva ID:", self.inputs["id"])
        self.form_layout.addRow("Enlem (Lat):", self.inputs["lat"])
        self.form_layout.addRow("Boylam (Lon):", self.inputs["lon"])
        self.inputs["yuva_tarihi"].setCalendarPopup(True)
        self.inputs["yuva_tarihi"].setDisplayFormat("dd.MM.yyyy")
        self.form_layout.addRow("Yuva Tarihi:", self.inputs["yuva_tarihi"])

        # Saha Ölçümleri Grubu
        self.form_layout.addRow(QLabel("<b>--- Saha Ölçümleri (İsteğe Bağlı) ---</b>"))
        saha_bilgileri = ["kuru_kum_uzakligi", "yari_islak_kum_uzakligi", "islak_kum_uzakligi", "toplam_denize_uzaklik",
                          "marka", "yuva_derinligi", "yuva_capi", "kulucka_suresi_gun"]
        for name in saha_bilgileri:
            self.form_layout.addRow(name.replace("_", " ").title(), self.inputs[name])

        # Checkbox'ları etiketleriyle birlikte ekle
        self.form_layout.addRow("Taşınma Durumu:", self.inputs["tasinma_durumu"])
        self.form_layout.addRow("Sıcaklık Aleti Var Mı:", self.inputs["sicaklik_aleti_var_mi"])

        # Yuva Kontrol Sonuçları Grubu
        self.form_layout.addRow(QLabel("<b>--- Yuva Kontrol Sonuçları (İsteğe Bağlı) ---</b>"))
        kontrol_bilgileri = [
            "toplam_yumurta_sayisi", "dollenmemis_yumurta_sayisi", "predasyonlu_yumurta_sayisi", "bos_kabuk_sayisi",
            "erken_donem_embriyo", "orta_donem_embriyo", "gec_donem_embriyo", "toplam_olu_embriyo",
            "yuva_ici_canli_yavru", "yuva_ici_olu_yavru",
            "yavru_cikis_gun_1", "yavru_cikis_gun_2", "yavru_cikis_gun_3"
        ]
        for name in kontrol_bilgileri:
            if "yavru_cikis_gun_" in name:
                gun_numarasi = name.split('_')[-1]
                guzel_isim = f"{gun_numarasi}. Gün Yavru Çıkışı"
            else:
                guzel_isim = name.replace("_", " ").title()
            self.form_layout.addRow(guzel_isim + ":", self.inputs[name])

        # Özel Tarihler Grubu
        self.form_layout.addRow(QLabel("<b>--- Özel Tarihler (İsteğe Bağlı) ---</b>"))
        self.ilk_yavru_cikis_check = QCheckBox("İlk Yavru Çıkış Tarihi Gir")
        self.inputs["ilk_yavru_cikis_tarihi"].setEnabled(False)
        self.inputs["ilk_yavru_cikis_tarihi"].setCalendarPopup(True)
        self.inputs["ilk_yavru_cikis_tarihi"].setDisplayFormat("dd.MM.yyyy")
        self.ilk_yavru_cikis_check.toggled.connect(self.inputs["ilk_yavru_cikis_tarihi"].setEnabled)
        self.form_layout.addRow(self.ilk_yavru_cikis_check, self.inputs["ilk_yavru_cikis_tarihi"])

        self.ikinci_predasyon_check = QCheckBox("2. Predasyon Tarihi Gir")
        self.inputs["ikinci_predasyon_tarihi"].setEnabled(False)
        self.inputs["ikinci_predasyon_tarihi"].setCalendarPopup(True)
        self.inputs["ikinci_predasyon_tarihi"].setDisplayFormat("dd.MM.yyyy")
        self.ikinci_predasyon_check.toggled.connect(self.inputs["ikinci_predasyon_tarihi"].setEnabled)
        self.form_layout.addRow(self.ikinci_predasyon_check, self.inputs["ikinci_predasyon_tarihi"])

        # Kapanış
        scroll_area.setWidget(form_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
    def get_data(self):
        data = {}; numeric_fields_int = ['id', 'kulucka_suresi_gun', 'yuva_ici_canli_yavru', 'yuva_ici_olu_yavru', 'erken_donem_embriyo', 'orta_donem_embriyo', 'gec_donem_embriyo', 'toplam_olu_embriyo', 'bos_kabuk_sayisi', 'predasyonlu_yumurta_sayisi', 'dollenmemis_yumurta_sayisi', 'toplam_yumurta_sayisi', 'yavru_cikis_gun_1', 'yavru_cikis_gun_2', 'yavru_cikis_gun_3']; numeric_fields_float = ['lat', 'lon', 'kuru_kum_uzakligi', 'yari_islak_kum_uzakligi', 'islak_kum_uzakligi', 'toplam_denize_uzaklik', 'yuva_derinligi', 'yuva_capi']
        try:
            for name, widget in self.inputs.items():
                if isinstance(widget, QLineEdit):
                    text = widget.text().strip(); data[name] = None if not text else int(text) if name in numeric_fields_int else float(text.replace(',', '.')) if name in numeric_fields_float else text
                elif isinstance(widget, QCheckBox): data[name] = "Evet" if widget.isChecked() else None
                elif isinstance(widget, QDateEdit):
                    if (name == "ilk_yavru_cikis_tarihi" and self.ilk_yavru_cikis_check.isChecked()) or (name == "ikinci_predasyon_tarihi" and self.ikinci_predasyon_check.isChecked()) or (name == "yuva_tarihi"): data[name] = widget.date().toString("yyyy-MM-dd")
                    else: data[name] = None
            if data.get('id') is None or data.get('lat') is None or data.get('lon') is None or data.get('yuva_tarihi') is None: raise ValueError("ID, Enlem, Boylam ve Yuva Tarihi alanları zorunludur.")
            canli = data.get('yuva_ici_canli_yavru'); toplam = data.get('toplam_yumurta_sayisi')
            if canli is not None and toplam is not None and toplam > 0: data['yuva_basarisi_yuzde'] = round((canli / toplam) * 100, 2)
            else: data['yuva_basarisi_yuzde'] = None
            return data
        except ValueError as e: QMessageBox.warning(self, "Veri Hatası", f"Lütfen sayısal alanları doğru girin.\n{e}"); return None

class GelismisGrafikDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Gelişmiş Grafik Aracı"); self.resize(850, 700)
        self.df = None; self.fig = None; self.canvas = None; self.readable_columns = {}; self.setup_ui(); self.load_data()
    def setup_ui(self):
        layout = QVBoxLayout(self); filter_group = QGroupBox("Veri Filtrele (İsteğe Bağlı)"); filter_layout = QFormLayout(filter_group); self.baslangic_id_input = QLineEdit(); self.baslangic_id_input.setPlaceholderText("Örn: 10"); self.bitis_id_input = QLineEdit(); self.bitis_id_input.setPlaceholderText("Örn: 50"); self.belirli_idler_input = QLineEdit(); self.belirli_idler_input.setPlaceholderText("Örn: 1, 3, 5 (virgülle ayırın)"); filter_layout.addRow("ID Aralığı (Başlangıç):", self.baslangic_id_input); filter_layout.addRow("ID Aralığı (Bitiş):", self.bitis_id_input); filter_layout.addRow(QLabel("<b>--- VEYA ---</b>")); filter_layout.addRow("Belirli Yuva ID'leri:", self.belirli_idler_input); layout.addWidget(filter_group); form_layout = QFormLayout(); self.x_ekseni_combo = QComboBox(); self.y_ekseni_combo = QComboBox(); self.grafik_turu_combo = QComboBox(); form_layout.addRow("X Ekseni:", self.x_ekseni_combo); form_layout.addRow("Y Ekseni:", self.y_ekseni_combo); form_layout.addRow("Grafik Türü:", self.grafik_turu_combo); layout.addLayout(form_layout); self.plot_container = QWidget(); self.plot_layout = QVBoxLayout(self.plot_container); layout.addWidget(self.plot_container); button_layout = QHBoxLayout(); self.btn_ciz = QPushButton("Grafiği Çiz"); self.btn_kaydet = QPushButton("Grafiği PNG Olarak Kaydet"); self.btn_pdf_kaydet_grafik = QPushButton("Grafiği PDF Olarak Kaydet"); self.btn_kaydet.setEnabled(False); self.btn_pdf_kaydet_grafik.setEnabled(False); button_layout.addWidget(self.btn_ciz); button_layout.addWidget(self.btn_kaydet); button_layout.addWidget(self.btn_pdf_kaydet_grafik); layout.addLayout(button_layout); self.btn_ciz.clicked.connect(self.grafik_ciz_ve_goster); self.btn_kaydet.clicked.connect(self.grafik_kaydet); self.btn_pdf_kaydet_grafik.clicked.connect(self.grafik_pdf_kaydet); self.x_ekseni_combo.currentIndexChanged.connect(self.update_grafik_turu_options); self.y_ekseni_combo.currentIndexChanged.connect(self.update_grafik_turu_options)
    def clear_canvas(self):
        if self.canvas: self.plot_layout.removeWidget(self.canvas); self.canvas.deleteLater(); self.canvas = None
        if self.fig: plt.close(self.fig); self.fig = None
        self.btn_kaydet.setEnabled(False); self.btn_pdf_kaydet_grafik.setEnabled(False)
    def load_data(self):
        self.df = yuvalari_dataframe_yap(); self.btn_ciz.setEnabled(not self.df.empty)
        if self.df.empty: return
        for col in ['yuva_tarihi', 'ilk_yavru_cikis_tarihi', 'ikinci_predasyon_tarihi']:
            if col in self.df.columns: self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
        self.readable_columns = {col: col.replace('_', ' ').title() for col in self.df.columns}
        self.x_ekseni_combo.clear(); self.y_ekseni_combo.clear(); self.y_ekseni_combo.addItem("Yok (Tek Sütun Analizi)", None)
        all_columns = [col for col in self.df.columns if col not in ['lat', 'lon']]
        for col in all_columns: self.x_ekseni_combo.addItem(self.readable_columns[col], col); self.y_ekseni_combo.addItem(self.readable_columns[col], col)
        self.update_grafik_turu_options()
    def update_grafik_turu_options(self, _=None):
        x_col_name = self.x_ekseni_combo.currentData(); y_col_name = self.y_ekseni_combo.currentData(); self.grafik_turu_combo.clear()
        if self.df is None or self.df.empty or x_col_name is None: return
        available_plot_types = []; x_is_numeric = pd.api.types.is_numeric_dtype(self.df[x_col_name]); x_is_datetime = pd.api.types.is_datetime64_any_dtype(self.df[x_col_name])
        if y_col_name is None:
            available_plot_types.extend(["Çubuk (bar)", "Pasta (pie)"])
            if x_is_numeric: available_plot_types.append("Histogram (hist)")
        else:
            if y_col_name not in self.df.columns: return
            y_is_numeric = pd.api.types.is_numeric_dtype(self.df[y_col_name])
            if (x_is_numeric or x_is_datetime) and y_is_numeric: available_plot_types.extend(["Dağılım (scatter)", "Çizgi (line)"])
            else: available_plot_types.append("Çubuk (bar)")
        self.grafik_turu_combo.addItems(available_plot_types)
    def get_filtered_data(self):
        try:
            belirli_idler_str = self.belirli_idler_input.text().strip()
            if belirli_idler_str:
                idler_listesi = [int(p.strip()) for p in belirli_idler_str.split(',') if p.strip().isdigit()]
                if not idler_listesi: QMessageBox.warning(self, "Geçersiz Giriş", "Geçerli, virgülle ayrılmış sayılar girmelisiniz."); return None
                return self.df[self.df['id'].isin(idler_listesi)].copy()
            else:
                df_temp = self.df.copy(); start_id_str = self.baslangic_id_input.text().strip(); end_id_str = self.bitis_id_input.text().strip()
                if start_id_str.isdigit(): df_temp = df_temp[df_temp['id'] >= int(start_id_str)]
                if end_id_str.isdigit(): df_temp = df_temp[df_temp['id'] <= int(end_id_str)]
                return df_temp
        except Exception as e: QMessageBox.critical(self, "Filtreleme Hatası", f"Veri filtrelenirken hata oluştu:\n{e}"); return None
    def grafik_ciz_ve_goster(self):
        self.clear_canvas(); filtered_df = self.get_filtered_data()
        if filtered_df is None or filtered_df.empty: QMessageBox.information(self, "Veri Bulunamadı", "Kriterlere uygun veri bulunamadı."); return
        x_sutun = self.x_ekseni_combo.currentData(); y_sutun = self.y_ekseni_combo.currentData(); grafik_turu_text = self.grafik_turu_combo.currentText()
        if not grafik_turu_text: QMessageBox.warning(self, "Hata", "Uygun bir grafik türü yok."); return
        grafik_turu = grafik_turu_text.split('(')[0].strip().lower()
        try:
            self.fig, ax = plt.subplots(); x_label = self.readable_columns.get(x_sutun, str(x_sutun))
            if y_sutun is None:
                plot_data = filtered_df[x_sutun].dropna()
                if grafik_turu == "pasta": plot_data.value_counts().head(15).plot.pie(ax=ax, autopct='%1.1f%%', startangle=90)
                elif grafik_turu == "çubuk": plot_data.value_counts().plot.bar(ax=ax, color='cornflowerblue')
                elif grafik_turu == "histogram": plot_data.plot.hist(ax=ax, bins=15, alpha=0.75, color='salmon')
                ax.set_title(f"'{x_label}' Dağılımı", fontsize=14)
            else:
                y_label = self.readable_columns.get(y_sutun, str(y_sutun)); plot_df = filtered_df[[x_sutun, y_sutun]].dropna()
                if grafik_turu == "dağılım": plot_df.plot.scatter(x=x_sutun, y=y_sutun, ax=ax, alpha=0.6)
                elif grafik_turu == "çizgi": plot_df.sort_values(by=x_sutun).plot(x=x_sutun, y=y_sutun, ax=ax, marker='o')
                elif grafik_turu == "çubuk":
                    if pd.api.types.is_numeric_dtype(plot_df[y_sutun]): plot_df.groupby(x_sutun)[y_sutun].mean().plot.bar(ax=ax, color='cornflowerblue')
                    else: plot_df.groupby([x_sutun, y_sutun]).size().unstack().plot.bar(ax=ax, stacked=True)
                ax.set_title(f"'{x_label}' ve '{y_label}' İlişkisi", fontsize=14); ax.set_ylabel(y_label, fontsize=10)
            ax.set_xlabel(x_label, fontsize=10); ax.grid(True, linestyle='--', alpha=0.6); self.fig.tight_layout()
            self.canvas = FigureCanvas(self.fig); self.plot_layout.addWidget(self.canvas); self.btn_kaydet.setEnabled(True); self.btn_pdf_kaydet_grafik.setEnabled(True)
        except Exception as e: QMessageBox.critical(self, "Grafik Hatası", f"Grafik çizilirken hata: {e}"); self.clear_canvas()
    def grafik_kaydet(self):
        if not self.fig: QMessageBox.warning(self, "Hata", "Kaydedilecek grafik yok."); return
        file_path, _ = QFileDialog.getSaveFileName(self, "Grafiği Kaydet", "grafik.png", "PNG Dosyaları (*.png)");
        if file_path:
            try: self.fig.savefig(file_path, dpi=300, bbox_inches='tight'); QMessageBox.information(self, "Başarılı", f"Grafik kaydedildi: {file_path}")
            except Exception as e: QMessageBox.critical(self, "Hata", f"Grafik kaydedilemedi: {e}")
    def grafik_pdf_kaydet(self):
        if not self.fig: QMessageBox.warning(self, "Hata", "Kaydedilecek grafik yok."); return
        dosya_yolu, _ = QFileDialog.getSaveFileName(self, "Grafik Raporunu Kaydet", "grafik_raporu.pdf", "PDF Dosyaları (*.pdf)")
        if not dosya_yolu: return
        gecici_grafik_yolu = os.path.join(SCRIPT_DIR, "temp_grafik.png")
        try: self.fig.savefig(gecici_grafik_yolu, dpi=300, bbox_inches='tight')
        except Exception as e: QMessageBox.critical(self, "Hata", f"Grafik geçici olarak kaydedilemedi: {e}"); return
        baslik = "Patara Yuva Verileri Grafik Raporu"; x_ekseni = self.x_ekseni_combo.currentText(); y_ekseni = self.y_ekseni_combo.currentText(); grafik_turu = self.grafik_turu_combo.currentText()
        icerik = [("Analiz Edilen X Ekseni:", x_ekseni, "navy"), ("Analiz Edilen Y Ekseni:", y_ekseni, "navy"), ("Kullanılan Grafik Türü:", grafik_turu, "navy")]
        basarili, mesaj = create_pdf_report(dosya_yolu, baslik, icerik, grafik_yolu=gecici_grafik_yolu)
        if os.path.exists(gecici_grafik_yolu): os.remove(gecici_grafik_yolu)
        if basarili: QMessageBox.information(self, "Başarılı", mesaj)
        else: QMessageBox.critical(self, "Hata", mesaj)
    def closeEvent(self, event): self.clear_canvas(); super().closeEvent(event)




class IstatistikDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İstatistiksel Özet Raporu")
        self.setMinimumSize(500, 450)  # Boyutu biraz büyütelim

        # Sadece arayüzü kur, HİÇBİR hesaplama yapma!
        self.setup_ui()

    def setup_ui(self):
        """Sadece arayüzü oluşturur, hesaplama yapmaz."""
        layout = QVBoxLayout(self)

        # Butonlar
        button_layout = QHBoxLayout()
        self.btn_hesapla = QPushButton("📊 İstatistikleri Hesapla ve Göster")
        self.btn_hesapla.setStyleSheet("padding: 8px;")
        self.btn_pdf_kaydet = QPushButton("PDF Olarak Kaydet")
        self.btn_pdf_kaydet.setEnabled(False)  # Başta pasif
        button_layout.addWidget(self.btn_hesapla)
        button_layout.addWidget(self.btn_pdf_kaydet)
        layout.addLayout(button_layout)

        # Sonuçların gösterileceği alan
        self.sonuc_container = QWidget()
        self.form_layout = QFormLayout(self.sonuc_container)
        layout.addWidget(self.sonuc_container)

        # Sinyal bağlantıları
        self.btn_hesapla.clicked.connect(self.hesapla_ve_goster)
        self.btn_pdf_kaydet.clicked.connect(self.pdf_kaydet)

        # Hesaplanan istatistikleri tutmak için bir değişken
        self.hesaplanan_istatistikler = None


    def hesapla_ve_goster(self):
        """Butona basıldığında veriyi yükler, hesaplar ve gösterir."""
        try:
            df = yuvalari_dataframe_yap()
            if df.empty:
                QMessageBox.warning(self, "Veri Yok", "Rapor oluşturulacak veri bulunamadı.")
                return

            # Önceki sonuçları temizle
            if hasattr(self, 'sonuc_container') and self.sonuc_container:
                self.sonuc_container.deleteLater()

            self.sonuc_container = QWidget()
            self.form_layout = QFormLayout(self.sonuc_container)
            self.layout().addWidget(self.sonuc_container)

            # İstatistikleri hesapla
            self.hesaplanan_istatistikler = []

            toplam_yuva = len(df)
            self.form_layout.addRow("Toplam Kayıtlı Yuva Sayısı:", QLabel(f"<b>{toplam_yuva}</b>"))
            self.hesaplanan_istatistikler.append(("Toplam Kayıtlı Yuva Sayısı:", f"{toplam_yuva}", "navy"))

            ortalama_basari = pd.to_numeric(df['yuva_basarisi_yuzde'], errors='coerce').dropna().mean()
            basari_str = f"<b>% {ortalama_basari:.2f}</b>" if pd.notna(ortalama_basari) else "N/A"
            self.form_layout.addRow("Ortalama Yuva Başarısı:", QLabel(basari_str))
            self.hesaplanan_istatistikler.append(
                ("Ortalama Yuva Başarısı:", basari_str.replace("<b>", "").replace("</b>", ""), "green"))

            ortalama_kulucka = pd.to_numeric(df['kulucka_suresi_gun'], errors='coerce').dropna().mean()
            kulucka_str = f"<b>{ortalama_kulucka:.1f}</b>" if pd.notna(ortalama_kulucka) else "N/A"
            self.form_layout.addRow("Ortalama Kuluçka Süresi (Gün):", QLabel(kulucka_str))
            self.hesaplanan_istatistikler.append(
                ("Ortalama Kuluçka Süresi (Gün):", kulucka_str.replace("<b>", "").replace("</b>", ""), "navy"))

            predasyonlu_sayisi = len(df[df['predasyon_durumu'].isin(['tam', 'yari', 'kismi'])])
            predasyon_orani = (predasyonlu_sayisi / toplam_yuva) * 100 if toplam_yuva > 0 else 0
            pred_str = f"<b>{predasyonlu_sayisi} yuva (% {predasyon_orani:.2f})</b>"
            self.form_layout.addRow("Predasyona Uğrayan Yuva Sayısı/Oranı:", QLabel(pred_str))
            self.hesaplanan_istatistikler.append(
                ("Predasyona Uğrayan Yuva Sayısı/Oranı:", pred_str.replace("<b>", "").replace("</b>", ""), "red"))


            self.btn_pdf_kaydet.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "Hesaplama Hatası", f"İstatistikler hesaplanırken bir hata oluştu:\n{e}")
            logging.error(f"İstatistik hesaplama hatası: {e}", exc_info=True)

    def pdf_kaydet(self):
        if not self.hesaplanan_istatistikler:
            QMessageBox.warning(self, "Hata", "Önce istatistikleri hesaplamalısınız.")
            return

        dosya_yolu, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", "istatistik_raporu.pdf",
                                                    "PDF Dosyaları (*.pdf)")
        if dosya_yolu:
            baslik = "Patara Yuva Verileri İstatistiksel Özet Raporu"
            basarili, mesaj = create_pdf_report(dosya_yolu, baslik, self.hesaplanan_istatistikler)
            if basarili:
                QMessageBox.information(self, "Başarılı", mesaj)
            else:
                QMessageBox.critical(self, "Hata", mesaj)


class PredasyonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Predasyon Durumu Güncelle")
        self.form_layout = QFormLayout(self)

        self.id_input = QLineEdit(self)
        self.yil_input = QLineEdit(self)  # Yıl için yeni giriş alanı
        self.durum_combo = QComboBox(self)
        self.durum_combo.addItems(["Yok", "Yarı Predasyon", "Tam Predasyon"])

        self.form_layout.addRow("Güncellenecek Yuvanın Yılı:", self.yil_input)
        self.form_layout.addRow("Güncellenecek Yuva ID'si:", self.id_input)
        self.form_layout.addRow("Yeni Predasyon Durumu:", self.durum_combo)

        self.predator_group_box = QGroupBox("Predatör Türleri")
        group_layout = QVBoxLayout()
        self.hayvan_turleri = {"domuz": QCheckBox("Domuz"), "marti": QCheckBox("Martı"), "tilki": QCheckBox("Tilki"),
                               "yengec": QCheckBox("Yengeç")}
        for checkbox in self.hayvan_turleri.values():
            group_layout.addWidget(checkbox)
        self.predator_group_box.setLayout(group_layout)
        self.form_layout.addRow(self.predator_group_box)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.form_layout.addWidget(self.button_box)

    def get_data(self):
        try:
            yuva_id = int(self.id_input.text())
            yuva_yil = int(self.yil_input.text())
            durum_text = self.durum_combo.currentText()
            predasyon_durumu = {"Tam Predasyon": "tam", "Yarı Predasyon": "yari"}.get(durum_text, "yok")
            secili_turler = [tur for tur, checkbox in self.hayvan_turleri.items() if checkbox.isChecked()]
            return {"id": yuva_id, "yil": yuva_yil, "durum": predasyon_durumu, "turler": secili_turler}
        except (ValueError, TypeError):
            return None



class KarsilastirmaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Yıllık Veri Karşılaştırma Aracı"); self.setMinimumSize(700, 500)
        self.df = None; layout = QVBoxLayout(self)
        try:
            df_orjinal = yuvalari_dataframe_yap()
            if df_orjinal.empty or 'yuva_tarihi' not in df_orjinal.columns: layout.addWidget(QLabel("Karşılaştırma yapılacak yeterli veri bulunamadı.")); return
            self.df = df_orjinal.copy()
            self.df['yuva_tarihi_dt'] = pd.to_datetime(self.df['yuva_tarihi'], errors='coerce')
            self.df.dropna(subset=['yuva_tarihi_dt'], inplace=True)
            self.df['yil'] = self.df['yuva_tarihi_dt'].dt.year.astype(int)
            self.setup_ui(layout); self.karsilastirmayi_yap()
        except Exception as e: layout.addWidget(QLabel(f"Veri hazırlanırken hata: {e}"))
    def setup_ui(self, layout):
        secim_grup = QGroupBox("Karşılaştırılacak Yılları Seçin"); secim_layout = QHBoxLayout(secim_grup)
        mevcut_yillar = sorted(self.df['yil'].unique(), reverse=True); yillar_str = [str(yil) for yil in mevcut_yillar]
        self.combo_grup1 = QComboBox(); self.combo_grup1.addItems(yillar_str)
        self.combo_grup2 = QComboBox(); self.combo_grup2.addItems(yillar_str)
        if len(yillar_str) > 1: self.combo_grup2.setCurrentIndex(1)
        self.btn_karsilastir = QPushButton("Karşılaştır")
        secim_layout.addWidget(QLabel("Grup 1:")); secim_layout.addWidget(self.combo_grup1); secim_layout.addWidget(QLabel("Grup 2:")); secim_layout.addWidget(self.combo_grup2)
        secim_layout.addStretch(); secim_layout.addWidget(self.btn_karsilastir); layout.addWidget(secim_grup)
        self.sonuc_tablosu = QTableWidget(); self.sonuc_tablosu.setColumnCount(3); self.sonuc_tablosu.setHorizontalHeaderLabels(["Ölçüm Kriteri", "Grup 1", "Grup 2"])
        self.sonuc_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sonuc_tablosu.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); layout.addWidget(self.sonuc_tablosu)
        self.btn_karsilastir.clicked.connect(self.karsilastirmayi_yap)
    def karsilastirmayi_yap(self):
        yil1_str = self.combo_grup1.currentText(); yil2_str = self.combo_grup2.currentText()
        if not yil1_str or not yil2_str: return
        yil1 = int(yil1_str); yil2 = int(yil2_str)
        self.sonuc_tablosu.setHorizontalHeaderItem(1, QTableWidgetItem(f"Grup 1 ({yil1})")); self.sonuc_tablosu.setHorizontalHeaderItem(2, QTableWidgetItem(f"Grup 2 ({yil2})"))
        df1 = self.df[self.df['yil'] == yil1]; df2 = self.df[self.df['yil'] == yil2]
        stats1 = self.hesapla_istatistik(df1); stats2 = self.hesapla_istatistik(df2); self.tabloyu_doldur(stats1, stats2)
    def hesapla_istatistik(self, df_grup):
        if df_grup.empty: return {k: "N/A" for k in ["Toplam Yuva Sayısı", "Ortalama Yuva Başarısı (%)", "Predasyonlu Yuva Sayısı", "Predasyon Oranı (%)"]}
        stats = {}; toplam_yuva = len(df_grup); stats["Toplam Yuva Sayısı"] = str(toplam_yuva)
        basari = pd.to_numeric(df_grup['yuva_basarisi_yuzde'], errors='coerce').dropna().mean()
        stats["Ortalama Yuva Başarısı (%)"] = f"{basari:.2f}" if pd.notna(basari) else "N/A"
        predasyonlu_sayisi = len(df_grup[df_grup['predasyon_durumu'].isin(['tam', 'yari', 'kismi'])]); stats["Predasyonlu Yuva Sayısı"] = str(predasyonlu_sayisi)
        predasyon_orani = (predasyonlu_sayisi / toplam_yuva) * 100 if toplam_yuva > 0 else 0; stats["Predasyon Oranı (%)"] = f"{predasyon_orani:.2f}"
        return stats
    def tabloyu_doldur(self, stats1, stats2):
        kriterler = list(stats1.keys()); self.sonuc_tablosu.setRowCount(len(kriterler))
        for satir, kriter in enumerate(kriterler):
            deger_orjinal_str = stats1.get(kriter, "N/A"); deger_simule_str = stats2.get(kriter, "N/A")
            self.sonuc_tablosu.setItem(satir, 0, QTableWidgetItem(kriter)); self.sonuc_tablosu.setItem(satir, 1, QTableWidgetItem(deger_orjinal_str))
            item_simule = QTableWidgetItem(deger_simule_str)
            try:
                val_orj = float(str(deger_orjinal_str).replace('%','').strip()); val_sim = float(str(deger_simule_str).replace('%','').strip())
                if val_sim > val_orj: item_simule.setForeground(QColor('#28A745'))
                elif val_sim < val_orj: item_simule.setForeground(QColor('#DC3545'))
            except (ValueError, TypeError): pass
            self.sonuc_tablosu.setItem(satir, 2, item_simule)

class SimulasyonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Ekolojik Senaryo ve Simülasyon Aracı"); self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self); self.df_orjinal = None
        try:
            self.df_orjinal = yuvalari_dataframe_yap()
            if self.df_orjinal.empty: main_layout.addWidget(QLabel("Simülasyon yapılacak veri bulunamadı.")); return
            self.setup_ui(main_layout); self.senaryo_degisti()
        except Exception as e: logging.error(f"Simülasyon diyaloğu başlatılırken hata: {e}", exc_info=True); main_layout.addWidget(QLabel(f"Pencere yüklenirken bir hata oluştu:\n{e}"))
    def setup_ui(self, main_layout):
        senaryo_grup = QGroupBox("1. Simülasyon Senaryosunu Seçin"); senaryo_form = QFormLayout(senaryo_grup)
        self.combo_senaryo = QComboBox(); self.combo_senaryo.addItems(["Konum Bazlı Tehdit/İyileştirme", "Durum Değişikliği (Filtreli)"]); senaryo_form.addRow("Senaryo Türü:", self.combo_senaryo); main_layout.addWidget(senaryo_grup)
        self.parametre_container = QWidget(); parametre_container_layout = QVBoxLayout(self.parametre_container); parametre_container_layout.setContentsMargins(0,0,0,0); main_layout.addWidget(self.parametre_container)
        self.setup_konum_bazli_widgets(); self.setup_durum_degisikligi_widgets()
        self.btn_simule_et = QPushButton("Simülasyonu Çalıştır ve Sonuçları Göster"); self.btn_simule_et.setStyleSheet("font-size: 14px; padding: 10px; background-color: #2E8B57; color: white;"); main_layout.addWidget(self.btn_simule_et)
        sonuc_grup = QGroupBox("Simülasyon Sonuçları"); sonuc_layout = QVBoxLayout(sonuc_grup); self.sonuc_tablosu = QTableWidget(); self.sonuc_tablosu.setColumnCount(3); self.sonuc_tablosu.setHorizontalHeaderLabels(["Ölçüm Kriteri", "Mevcut Durum", "Simülasyon Sonucu"])
        self.sonuc_tablosu.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.sonuc_tablosu.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); sonuc_layout.addWidget(self.sonuc_tablosu); main_layout.addWidget(sonuc_grup)
        self.combo_senaryo.currentIndexChanged.connect(self.senaryo_degisti); self.btn_simule_et.clicked.connect(self.simulasyonu_calistir)
    def setup_konum_bazli_widgets(self):
        self.konum_grup = QGroupBox("Konum Parametreleri"); layout = QFormLayout(self.konum_grup); config = load_config(); sabit_lejantlar = config.get("sabit_lejantlar", {})
        self.konum_referans_combo = QComboBox(); self.konum_referans_combo.addItems(list(sabit_lejantlar.keys())); self.konum_mesafe_input = QLineEdit("300")
        self.konum_yeni_durum_combo = QComboBox(); self.konum_yeni_durum_combo.addItems(["tam", "yari", "yok"])
        layout.addRow("Referans Noktası:", self.konum_referans_combo); layout.addRow("Mesafe (metre):", self.konum_mesafe_input); layout.addRow("Yeni Predasyon Durumu:", self.konum_yeni_durum_combo)
        self.parametre_container.layout().addWidget(self.konum_grup)
    def setup_durum_degisikligi_widgets(self):
        self.durum_grup = QGroupBox("Durum Değişikliği Parametreleri"); layout = QFormLayout(self.durum_grup)
        self.durum_eski_combo = QComboBox(); self.durum_eski_combo.addItems(["yari", "tam", "yok"]); self.durum_yeni_combo = QComboBox(); self.durum_yeni_combo.addItems(["yok", "yari", "tam"])
        layout.addRow("Mevcut Durumu:", self.durum_eski_combo); layout.addRow("Yeni Durumu:", self.durum_yeni_combo)
        self.parametre_container.layout().addWidget(self.durum_grup)
    def senaryo_degisti(self):
        secilen_senaryo = self.combo_senaryo.currentText()
        if "Konum Bazlı" in secilen_senaryo: self.konum_grup.show(); self.durum_grup.hide()
        elif "Durum Değişikliği" in secilen_senaryo: self.konum_grup.hide(); self.durum_grup.show()
    def simulasyonu_calistir(self):
        if self.df_orjinal is None or self.df_orjinal.empty: return
        df_simule = self.df_orjinal.copy(); secilen_senaryo = self.combo_senaryo.currentText(); etkilenen_yuva_sayisi = 0
        try:
            if "Konum Bazlı" in secilen_senaryo:
                referans_adi = self.konum_referans_combo.currentText().lower(); mesafe_metre = int(self.konum_mesafe_input.text()); yeni_durum = self.konum_yeni_durum_combo.currentText()
                config = load_config(); sabit_lejantlar = config.get("sabit_lejantlar", {}); referans_koordinat = sabit_lejantlar[referans_adi]
                df_geo = df_simule[df_simule['lat'].notna() & df_simule['lon'].notna()].copy()
                if not df_geo.empty:
                    gdf = gpd.GeoDataFrame(df_geo, geometry=gpd.points_from_xy(df_geo.lon, df_geo.lat), crs="EPSG:4326"); gdf_utm = gdf.to_crs("EPSG:32635")
                    referans_noktasi_utm = gpd.GeoSeries([Point(referans_koordinat[1], referans_koordinat[0])], crs="EPSG:4326").to_crs("EPSG:32635")[0]
                    tampon_bolge = referans_noktasi_utm.buffer(mesafe_metre); etkilenen_indexler = gdf_utm[gdf_utm.within(tampon_bolge)].index; etkilenen_yuva_sayisi = len(etkilenen_indexler)
                    df_simule.loc[etkilenen_indexler, 'predasyon_durumu'] = yeni_durum
            elif "Durum Değişikliği" in secilen_senaryo:
                eski_durum = self.durum_eski_combo.currentText(); yeni_durum = self.durum_yeni_combo.currentText()
                etkilenen_indexler = df_simule[df_simule['predasyon_durumu'] == eski_durum].index; etkilenen_yuva_sayisi = len(etkilenen_indexler)
                df_simule.loc[etkilenen_indexler, 'predasyon_durumu'] = yeni_durum
        except Exception as e: QMessageBox.critical(self, "Simülasyon Hatası", f"Senaryo uygulanırken bir hata oluştu:\n{e}"); logging.error(f"Simülasyon hatası: {e}", exc_info=True); return
        canli = pd.to_numeric(df_simule['yuva_ici_canli_yavru'], errors='coerce').fillna(0); toplam = pd.to_numeric(df_simule['toplam_yumurta_sayisi'], errors='coerce').fillna(0)
        df_simule['yuva_basarisi_yuzde'] = np.divide(canli * 100, toplam, out=np.zeros_like(canli, dtype=float), where=toplam!=0).round(2)
        stats_orjinal = self.hesapla_istatistik(self.df_orjinal); stats_simule = self.hesapla_istatistik(df_simule); self.tabloyu_doldur(stats_orjinal, stats_simule)
        QMessageBox.information(self, "Simülasyon Tamamlandı", f"Simülasyon başarıyla çalıştırıldı.\nToplam {etkilenen_yuva_sayisi} yuva bu senaryodan etkilendi.")
    def hesapla_istatistik(self, df_grup):
        if df_grup.empty: return {k: "N/A" for k in ["Toplam Yuva Sayısı", "Ortalama Yuva Başarısı (%)", "Predasyonlu Yuva Sayısı", "Predasyon Oranı (%)"]}
        stats = {}; toplam_yuva = len(df_grup); stats["Toplam Yuva Sayısı"] = str(toplam_yuva)
        basari = pd.to_numeric(df_grup['yuva_basarisi_yuzde'], errors='coerce').dropna().mean(); stats["Ortalama Yuva Başarısı (%)"] = f"{basari:.2f}" if pd.notna(basari) else "N/A"
        predasyonlu_sayisi = len(df_grup[df_grup['predasyon_durumu'].isin(['tam', 'yari', 'kismi'])]); stats["Predasyonlu Yuva Sayısı"] = str(predasyonlu_sayisi)
        predasyon_orani = (predasyonlu_sayisi / toplam_yuva) * 100 if toplam_yuva > 0 else 0; stats["Predasyon Oranı (%)"] = f"{predasyon_orani:.2f}"
        return stats
    def tabloyu_doldur(self, stats_orjinal, stats_simule):
        kriterler = list(stats_orjinal.keys()); self.sonuc_tablosu.setRowCount(len(kriterler))
        for satir, kriter in enumerate(kriterler):
            deger_orjinal_str = stats_orjinal.get(kriter, "N/A"); deger_simule_str = stats_simule.get(kriter, "N/A")
            self.sonuc_tablosu.setItem(satir, 0, QTableWidgetItem(kriter)); self.sonuc_tablosu.setItem(satir, 1, QTableWidgetItem(deger_orjinal_str))
            item_simule = QTableWidgetItem(deger_simule_str)
            try:
                val_orj = float(str(deger_orjinal_str).replace('%','').strip()); val_sim = float(str(deger_simule_str).replace('%','').strip())
                if val_sim > val_orj: item_simule.setForeground(QColor('#28A745'))
                elif val_sim < val_orj: item_simule.setForeground(QColor('#DC3545'))
            except (ValueError, TypeError): pass
            self.sonuc_tablosu.setItem(satir, 2, item_simule)

class HakkindaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowTitle("Hakkında"); self.setFixedSize(450, 320)
        layout = QVBoxLayout(self); layout.setContentsMargins(20, 20, 20, 20); layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        try:
            logo_path = os.path.join(SCRIPT_DIR, "logo.png")
            if os.path.exists(logo_path):
                logo_label = QLabel(); pixmap = QPixmap(logo_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(pixmap); logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(logo_label)
        except Exception as e: logging.error(f"Logo yüklenirken hata oluştu: {e}")
        baslik = QLabel("Patara Bilimsel Veri Platformu"); baslik.setStyleSheet("font-size: 20px; font-weight: bold; color: #0055A4;"); baslik.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(baslik)
        versiyon = QLabel("Versiyon 1.3 (Final)"); versiyon.setStyleSheet("font-size: 11px; color: #555;"); versiyon.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(versiyon)
        layout.addSpacing(25)
        github_url = "https://github.com/Eggkan"; info_text = (f"<p><b>Geliştirici:</b> Ege Kaan Yükün</p>" f"<p><b>Akademik Danışman:</b> Prof. Dr. Eyüp Başkale</p>" f"<p>Bu uygulama, bilimsel veri toplama ve analiz süreçlerini kolaylaştırmak amacıyla geliştirilmiştir.</p>" f"<p><b>GitHub:</b> <a href='{github_url}'>{github_url}</a></p>")
        info_label = QLabel(info_text); info_label.setOpenExternalLinks(True); info_label.setWordWrap(True); layout.addWidget(info_label)
        layout.addStretch(); kapat_button = QPushButton("Kapat"); kapat_button.clicked.connect(self.accept); layout.addWidget(kapat_button, 0, Qt.AlignmentFlag.AlignCenter)

class MapCommunicator(QObject):
    drawing_finished_signal = pyqtSignal(list)
    def __init__(self, parent=None):
        super().__init__(parent); self.drawn_polygon_coords = None; logging.info("MapCommunicator başlatıldı.")
    @pyqtSlot(str)
    def receive_drawing_data(self, geojson_str):
        try:
            data = json.loads(geojson_str)
            if data['geometry']['type'] in ['Polygon', 'LineString']:
                coords = [[point[1], point[0]] for point in data['geometry']['coordinates'][0]] if data['geometry']['type'] == 'Polygon' else [[point[1], point[0]] for point in data['geometry']['coordinates']]
                self.drawn_polygon_coords = coords; logging.info(f"Haritadan {data['geometry']['type']} verisi alındı."); self.drawing_finished_signal.emit(coords)
            else: logging.warning(f"Desteklenmeyen çizim tipi: {data['geometry']['type']}")
        except Exception as e: logging.error(f"GeoJSON verisi işlenirken hata: {e}", exc_info=True)




# ==============================================================================
# BÖLÜM 4: ANA PENCERE SINIFI (YILLIK ID SİSTEMİ İLE GÜNCELLENMİŞ)
# ==============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logging.info("Ana pencere oluşturuluyor...")
        self.config = load_config()
        self.sabit_lejantlar = self.config.get("sabit_lejantlar", {})
        self.renkler = ["red", "blue", "green", "purple", "orange", "darkred", "lightred", "beige", "darkblue", "darkgreen", "cadetblue", "pink"]
        self.map_object = None
        self.map_communicator = MapCommunicator(self)
        self.gelismis_grafik_penceresi = None
        self.setWindowTitle("Patara Bilimsel Veri Platformu")
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(1600, 900)
        self.setup_ui()
        self.setup_connections()
        self.setAcceptDrops(True)
        logging.info("Ana pencere __init__ süreci tamamlandı.")

    def setup_ui(self):
        self.setup_menu_bar()
        main_layout = QHBoxLayout()
        container = QWidget(); container.setLayout(main_layout); self.setCentralWidget(container)
        def _create_icon_safely(icon_name, fallback_pixmap_enum=None):
            full_path = os.path.join(SCRIPT_DIR, 'icons', icon_name)
            if os.path.exists(full_path):
                try: return QIcon(full_path)
                except Exception as e: logging.error(f"Özel ikon '{icon_name}' yüklenirken hata: {e}", exc_info=True)
            if fallback_pixmap_enum: return self.style().standardIcon(fallback_pixmap_enum)
            return QIcon()
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel); left_panel.setMaximumWidth(400)
        left_layout.addWidget(QLabel("<b>Kayıtlı Yuvalar</b>")); arama_layout = QHBoxLayout()
        self.arama_kriteri_combo = QComboBox(); self.arama_kriteri_combo.addItems(["Tüm Bilgiler", "ID", "Yıl", "Durum", "Predatör"])
        self.arama_kutusu = QLineEdit(); self.arama_kutusu.setPlaceholderText("Aramak için yazın...")
        arama_layout.addWidget(self.arama_kriteri_combo); arama_layout.addWidget(self.arama_kutusu); left_layout.addLayout(arama_layout)
        self.yuva_list_widget = QListWidget(); left_layout.addWidget(self.yuva_list_widget)
        self.yuva_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_layout.addWidget(self.yuva_list_widget)
        self.detay_paneli = QGroupBox("Seçili Yuva Detayları"); detay_layout = QFormLayout(self.detay_paneli); self.detay_paneli.setFixedHeight(220)
        self.detay_id = QLabel("-"); self.detay_tarih = QLabel("-"); self.detay_basari = QLabel("-"); self.detay_predasyon = QLabel("-"); self.detay_yumurta_sayisi = QLabel("-"); self.detay_canli_yavru = QLabel("-")
        self.detay_id.setStyleSheet("font-weight: bold; color: #0055A4;"); self.detay_basari.setStyleSheet("font-weight: bold; color: #2E8B57;"); self.detay_predasyon.setStyleSheet("font-weight: bold; color: #B22222;")
        detay_layout.addRow("Yuva ID (Yıl):", self.detay_id); detay_layout.addRow("Yuva Tarihi:", self.detay_tarih); detay_layout.addRow("Toplam Yumurta:", self.detay_yumurta_sayisi); detay_layout.addRow("Canlı Yavru:", self.detay_canli_yavru); detay_layout.addRow("Yuva Başarısı:", self.detay_basari); detay_layout.addRow("Predasyon Durumu:", self.detay_predasyon)
        left_layout.addWidget(self.detay_paneli); main_layout.addWidget(left_panel)
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel); self.web_view = QWebEngineView(); right_layout.addWidget(self.web_view)
        kontrol_paneli_grup = QGroupBox("Harita Analiz Araçları"); kontrol_paneli = QHBoxLayout(kontrol_paneli_grup)
        self.heatmap_check = QCheckBox("Isı Haritasını Göster"); kontrol_paneli.addWidget(self.heatmap_check); kontrol_paneli.addWidget(QLabel(" | "))
        kontrol_paneli.addWidget(QLabel("Referans Noktası:")); self.combo_referans = QComboBox(); sabit_lejantlar_isimleri = [isim.title() for isim in self.sabit_lejantlar.keys()]; self.combo_referans.addItems(["Yok"] + sabit_lejantlar_isimleri)
        kontrol_paneli.addWidget(self.combo_referans); kontrol_paneli.addWidget(QLabel("Mesafe (m):")); self.mesafe_input = QLineEdit("500"); self.mesafe_input.setFixedWidth(50); kontrol_paneli.addWidget(self.mesafe_input)
        self.btn_filtrele = QPushButton(" Filtrele"); self.btn_filtrele.setIcon(_create_icon_safely('filter.png', QStyle.StandardPixmap.SP_DialogApplyButton)); kontrol_paneli.addWidget(self.btn_filtrele); kontrol_paneli.addWidget(QLabel(" | "))
        self.btn_cizim_modu = QPushButton(" Çizim Modu"); self.btn_cizim_modu.setIcon(_create_icon_safely('pencil.png', QStyle.StandardPixmap.SP_DialogHelpButton))
        self.btn_cizim_temizle = QPushButton(" Çizimi Temizle"); self.btn_cizim_temizle.setIcon(_create_icon_safely('eraser.png', QStyle.StandardPixmap.SP_DialogCancelButton)); self.btn_cizim_temizle.setEnabled(False)
        kontrol_paneli.addWidget(self.btn_cizim_modu); kontrol_paneli.addWidget(self.btn_cizim_temizle); kontrol_paneli.addStretch(); right_layout.addWidget(kontrol_paneli_grup)
        button_panel = QWidget(); self.button_layout = QHBoxLayout(button_panel); self.button_layout.setContentsMargins(0, 5, 0, 0)
        self.btn_yenile = QPushButton(" Yenile"); self.btn_yenile.setIcon(_create_icon_safely('reload.png', QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_yuva_ekle = QPushButton(" Yuva Ekle"); self.btn_yuva_ekle.setIcon(_create_icon_safely('turtle.png', QStyle.StandardPixmap.SP_FileIcon))
        self.btn_predasyon = QPushButton(" Predasyon"); self.btn_predasyon.setIcon(_create_icon_safely('fangs.png', QStyle.StandardPixmap.SP_DialogApplyButton))
        self.btn_sil = QPushButton(" Sil"); self.btn_sil.setIcon(_create_icon_safely('remove.png', QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_karsilastir = QPushButton(" Karşılaştır"); self.btn_karsilastir.setIcon(_create_icon_safely('benchmarking.png', QStyle.StandardPixmap.SP_ComputerIcon))
        self.btn_istatistik = QPushButton(" Özet Rapor"); self.btn_istatistik.setIcon(_create_icon_safely('report.png', QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_gelismis_grafik = QPushButton(" Grafik"); self.btn_gelismis_grafik.setIcon(_create_icon_safely('chart.png', QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_excel_import = QPushButton(" İçe Aktar"); self.btn_excel_import.setIcon(_create_icon_safely('file-import.png', QStyle.StandardPixmap.SP_ArrowUp))
        self.btn_excel_export = QPushButton(" Dışa Aktar"); self.btn_excel_export.setIcon(_create_icon_safely('import-export.png', QStyle.StandardPixmap.SP_ArrowDown))
        self.btn_simulasyon = QPushButton(" Simülasyon"); self.btn_simulasyon.setIcon(_create_icon_safely('magic_wand.png', QStyle.StandardPixmap.SP_DialogHelpButton))
        self.button_layout.addWidget(self.btn_yenile); self.button_layout.addWidget(self.btn_yuva_ekle); self.button_layout.addWidget(self.btn_predasyon); self.button_layout.addWidget(self.btn_sil); self.button_layout.addStretch(1)
        self.button_layout.addWidget(self.btn_karsilastir); self.button_layout.addWidget(self.btn_istatistik); self.button_layout.addWidget(self.btn_gelismis_grafik); self.button_layout.addWidget(self.btn_excel_import); self.button_layout.addWidget(self.btn_excel_export); self.button_layout.addWidget(self.btn_simulasyon)
        right_layout.addWidget(button_panel); main_layout.addWidget(right_panel, 3)

    def setup_menu_bar(self):
        menu_bar = self.menuBar(); dosya_menu = menu_bar.addMenu("&Dosya"); geri_yukle_action = QAction(self.get_icon(QStyle.StandardPixmap.SP_DialogResetButton), "Yedekten Geri Yükle...", self); geri_yukle_action.triggered.connect(self.yedekten_geri_yukle); dosya_menu.addAction(geri_yukle_action)
        dosya_menu.addSeparator(); cikis_action = QAction(self.get_icon(QStyle.StandardPixmap.SP_DialogCloseButton), "Çıkış", self); cikis_action.triggered.connect(self.close); dosya_menu.addAction(cikis_action)
        gorunum_menu = menu_bar.addMenu("&Görünüm"); tema_menu = gorunum_menu.addMenu("Tema Seç")
        acik_tema_action = QAction("Açık Tema", self, checkable=True); koyu_tema_action = QAction("Koyu Tema", self, checkable=True)
        self.tema_aksiyon_grubu = QActionGroup(self); self.tema_aksiyon_grubu.addAction(acik_tema_action); self.tema_aksiyon_grubu.addAction(koyu_tema_action); acik_tema_action.setChecked(True)
        tema_menu.addAction(acik_tema_action); tema_menu.addAction(koyu_tema_action)
        yardim_menu = menu_bar.addMenu("&Yardım"); hakkinda_action = QAction(self.get_icon(QStyle.StandardPixmap.SP_DialogHelpButton), "Hakkında", self); hakkinda_action.triggered.connect(self.hakkinda_penceresi_ac); yardim_menu.addAction(hakkinda_action)
        self.tema_aksiyon_grubu.triggered.connect(self.tema_degistir)

    def setup_connections(self):
        self.arama_kutusu.textChanged.connect(self.akilli_filtrele); self.arama_kriteri_combo.currentIndexChanged.connect(self.akilli_filtrele)
        self.yuva_list_widget.currentItemChanged.connect(self.yuva_secildiginde_odaklan)
        self.btn_yenile.clicked.connect(self.harita_ve_liste_yenile); self.btn_yuva_ekle.clicked.connect(self.yuva_ekle_dialog_ac)
        self.btn_predasyon.clicked.connect(self.predasyon_dialog_ac); self.btn_sil.clicked.connect(self.yuva_sil_dialog_ac)
        self.btn_gelismis_grafik.clicked.connect(self.gelismis_grafik_penceresi_ac); self.btn_excel_import.clicked.connect(self.excel_import_dialog_ac); self.btn_excel_export.clicked.connect(self.excel_export_dialog_ac)
        self.btn_istatistik.clicked.connect(self.istatistik_penceresi_ac); self.btn_karsilastir.clicked.connect(self.karsilastirma_penceresi_ac); self.btn_simulasyon.clicked.connect(self.simulasyon_penceresi_ac)
        self.heatmap_check.stateChanged.connect(self.harita_ve_liste_yenile); self.btn_filtrele.clicked.connect(self.harita_ve_liste_yenile); self.combo_referans.currentIndexChanged.connect(self.harita_ve_liste_yenile)
        self.btn_cizim_modu.clicked.connect(self.cizim_modu_toggle); self.btn_cizim_temizle.clicked.connect(self.cizim_temizle); self.map_communicator.drawing_finished_signal.connect(self.cizim_sonucunu_islem)
        self.web_view.page().loadFinished.connect(self.on_web_page_load_finished)

    def tema_degistir(self, action):
        app = QApplication.instance(); tema_adi = "light_theme.qss"
        if action.text() == "Koyu Tema": tema_adi = "dark_theme.qss"
        try:
            style_path = os.path.join(SCRIPT_DIR, "styles", tema_adi)
            if os.path.exists(style_path):
                with open(style_path, "r") as f: app.setStyleSheet(f.read())
                logging.info(f"Tema değiştirildi: {action.text()}")
            else: app.setStyleSheet(""); logging.warning(f"Tema dosyası bulunamadı: {tema_adi}")
        except Exception as e: app.setStyleSheet(""); logging.error(f"Tema dosyası yüklenemedi: {e}", exc_info=True)

    def cizim_modu_toggle(self):
        if self.web_view.page().url().isEmpty(): QMessageBox.warning(self, "Hata", "Harita yüklenmeden çizim modu aktifleştirilemez."); return
        js_enable = self.btn_cizim_modu.text() == " Çizim Modu"
        self.web_view.page().runJavaScript(f"window.toggleDrawModeJS({str(js_enable).lower()});")
        if js_enable: self.statusBar().showMessage("Çizim modu aktif...", 5000); self.btn_cizim_modu.setText("Çizim Modunu Kapat"); self.btn_cizim_temizle.setEnabled(True)
        else: self.statusBar().showMessage("Çizim modu kapalı.", 3000); self.btn_cizim_modu.setText(" Çizim Modu"); self.btn_cizim_temizle.setEnabled(False); self.harita_ve_liste_yenile(clear_drawn_filter=True)

    def cizim_temizle(self):
        if self.map_object:
            self.web_view.page().runJavaScript("window.clearDrawingsJS();")
            self.map_communicator.drawn_polygon_coords = None; self.harita_ve_liste_yenile(clear_drawn_filter=True); self.statusBar().showMessage("Çizimler temizlendi ve filtre kaldırıldı.", 3000)

    @pyqtSlot(list)
    def cizim_sonucunu_islem(self, coords):
        self.map_communicator.drawn_polygon_coords = coords; self.statusBar().showMessage("Alan çizildi. Veriler filtreleniyor...", 3000); self.harita_ve_liste_yenile(); self.btn_cizim_temizle.setEnabled(True)

    @pyqtSlot(bool)
    def on_web_page_load_finished(self, ok):
        if ok:
            logging.info("QWebEngineView sayfası yüklendi. WebChannel kuruluyor.")
            channel = QWebChannel(self.web_view.page()); self.web_view.page().setWebChannel(channel); channel.registerObject("MapCommunicator", self.map_communicator)
            js_setup_script = """if (typeof window.setupWebChannelAndDrawPlugin === 'function') { window.setupWebChannelAndDrawPlugin(); } else { console.error("JS tarafında fonksiyon bulunamadı."); }"""; self.web_view.page().runJavaScript(js_setup_script)
        else: logging.error("QWebEngineView sayfası yüklenirken hata."); QMessageBox.critical(self, "Harita Yükleme Hatası", "Harita görüntülenemedi.")

    def get_icon(self, pixmap_enum):
        return self.style().standardIcon(pixmap_enum)

    def get_filtrelenmis_yuvalar(self):
        if self.map_communicator.drawn_polygon_coords:
            try:
                drawn_polygon = Polygon(self.map_communicator.drawn_polygon_coords); yuvalar = tum_yuvalari_getir()
                if not yuvalar: return []
                gecerli_yuvalar = [y for y in yuvalar if y.get('lat') is not None and y.get('lon') is not None]
                if not gecerli_yuvalar: return []
                gdf_yuvalar = gpd.GeoDataFrame(gecerli_yuvalar, geometry=gpd.points_from_xy([y['lon'] for y in gecerli_yuvalar], [y['lat'] for y in gecerli_yuvalar]), crs="EPSG:4326")
                gdf_polygon = gpd.GeoSeries([drawn_polygon], crs="EPSG:4326")
                filtered_gdf = gdf_yuvalar[gdf_yuvalar.within(gdf_polygon.iloc[0])]
                filtrelenmis_idler = set(filtered_gdf['id']); sonuc = [yuva for yuva in gecerli_yuvalar if yuva['id'] in filtrelenmis_idler]
                logging.info(f"Çizilen alanda {len(sonuc)} yuva bulundu."); return sonuc
            except Exception as e: logging.error(f"Çizim filtresi hatası: {e}", exc_info=True); QMessageBox.critical(self, "Çizim Filtresi Hatası", f"Filtreleme yapılamadı:\n{e}"); self.map_communicator.drawn_polygon_coords = None; return tum_yuvalari_getir()
        referans_adi = self.combo_referans.currentText().lower(); mesafe_str = self.mesafe_input.text()
        if referans_adi == "yok" or not mesafe_str.isdigit(): return tum_yuvalari_getir()
        try:
            mesafe_metre = int(mesafe_str); yuvalar = tum_yuvalari_getir()
            if not yuvalar: return []
            gecerli_yuvalar = [y for y in yuvalar if y.get('lat') is not None and y.get('lon') is not None]
            if not gecerli_yuvalar: return []
            gdf_yuvalar = gpd.GeoDataFrame(gecerli_yuvalar, geometry=gpd.points_from_xy([y['lon'] for y in gecerli_yuvalar], [y['lat'] for y in gecerli_yuvalar]), crs="EPSG:4326")
            gdf_yuvalar_utm = gdf_yuvalar.to_crs("EPSG:32635")
            referans_koordinat = self.sabit_lejantlar[referans_adi]; referans_noktasi_utm = gpd.GeoSeries([Point(referans_koordinat[1], referans_koordinat[0])], crs="EPSG:4326").to_crs("EPSG:32635")[0]
            tampon_bolge = referans_noktasi_utm.buffer(mesafe_metre); icindeki_yuvalar_mask = gdf_yuvalar_utm.within(tampon_bolge)
            filtrelenmis_gdf = gdf_yuvalar_utm[icindeki_yuvalar_mask]; filtrelenmis_idler = set(filtrelenmis_gdf['id'])
            sonuc = [yuva for yuva in gecerli_yuvalar if yuva['id'] in filtrelenmis_idler]
            logging.info(f"'{referans_adi.title()}' noktasına {mesafe_metre}m mesafe içinde {len(sonuc)} yuva bulundu."); return sonuc
        except Exception as e: logging.error(f"Coğrafi analiz hatası: {e}", exc_info=True); QMessageBox.critical(self, "Coğrafi Analiz Hatası", f"Analiz hatası: {e}"); return tum_yuvalari_getir()

    def harita_ve_liste_yenile(self, *args, **kwargs):
        if kwargs.get('clear_drawn_filter', False): self.map_communicator.drawn_polygon_coords = None; self.btn_cizim_temizle.setEnabled(False)
        filtrelenmis_yuvalar = self.get_filtrelenmis_yuvalar(); self.map_object = self.harita_olustur(yuva_verisi=filtrelenmis_yuvalar)
        data = io.BytesIO(); self.map_object.save(data, close_file=False); self.web_view.setHtml(data.getvalue().decode())
        self.populate_yuva_listesi(yuva_verisi=filtrelenmis_yuvalar); self.statusBar().showMessage("Harita ve yuva listesi başarıyla yenilendi.", 4000)



    def harita_olustur(self, yuva_verisi=None):
        """
        Verilen yuva verisine göre, kümelenmiş ve katmanlı bir Folium haritası oluşturur.
        Isı haritası seçeneğini de bir katman olarak ekler.
        """
        yuva_noktalari = yuva_verisi if yuva_verisi is not None else tum_yuvalari_getir()
        start_location = [36.27, 29.29]  # Varsayılan başlangıç konumu

        if yuva_noktalari:
            # Geçerli koordinatı olan ilk yuvayı bul ve haritayı oraya odakla
            first_valid_coord = next(
                ((y['lat'], y['lon']) for y in yuva_noktalari if y.get('lat') is not None and y.get('lon') is not None),
                None)
            if first_valid_coord:
                start_location = first_valid_coord

        # Haritayı oluştur
        harita = folium.Map(location=start_location, zoom_start=13, tiles="CartoDB positron")

        # Sabit lejantları haritanın ana katmanına ekle
        for i, (isim, koordinat) in enumerate(self.sabit_lejantlar.items()):
            folium.Marker(
                location=koordinat,
                popup=isim,
                tooltip=isim,
                icon=folium.Icon(color=self.renkler[i % len(self.renkler)], icon='info-sign')
            ).add_to(harita)

        points = list(self.sabit_lejantlar.values())
        folium.PolyLine(points, color="gray", weight=2, opacity=0.8, dash_array='5, 5').add_to(harita)

        # --- KATEGORİK KÜMELEME VE KATMANLAMA MANTIĞI ---

        # 1. Her durum için ayrı bir FeatureGroup ve MarkerCluster oluştur
        # 'show' parametresi, katmanın başlangıçta görünür olup olmayacağını belirler.
        grup_saglam = folium.FeatureGroup(name="Sağlam Yuvalar", show=True).add_to(harita)
        cluster_saglam = plugins.MarkerCluster().add_to(grup_saglam)

        grup_yari = folium.FeatureGroup(name="Yarı Predasyon", show=True).add_to(harita)
        cluster_yari = plugins.MarkerCluster().add_to(grup_yari)

        grup_tam = folium.FeatureGroup(name="Tam Predasyon", show=True).add_to(harita)
        cluster_tam = plugins.MarkerCluster().add_to(grup_tam)

        # Isı haritası için ayrı bir katman, başlangıçta gizli
        grup_heatmap = folium.FeatureGroup(name="Yoğunluk Haritası (Heatmap)", show=False).add_to(harita)
        koordinatlar_heatmap = []

        # 2. Yuvaları tek tek işle ve doğru gruba/kümelere ekle
        for yuva in yuva_noktalari:
            lat, lon = yuva.get("lat"), yuva.get("lon")
            if lat is not None and lon is not None:
                koordinatlar_heatmap.append([lat, lon])  # Isı haritası için her zaman topla

                # Popup ve renk bilgilerini hazırla
                durum = str(yuva.get("predasyon_durumu", "")).lower()
                basari_str = f"{yuva.get('yuva_basarisi_yuzde')}%" if yuva.get(
                    'yuva_basarisi_yuzde') is not None else "N/A"
                popup_text = f"<b>{yuva.get('yil')} - ID: {yuva.get('id', 'N/A')}</b><br>Tarih: {yuva.get('yuva_tarihi', 'N/A')}<br><b>Başarı: {basari_str}</b>"
                predatorler = yuva.get("predator_canli_listesi", [])
                if predatorler:
                    popup_text += f"<br>Predatörler: {', '.join(p.title() for p in predatorler)}"

                marker = folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    popup=popup_text,
                    tooltip=f"ID: {yuva.get('id', 'N/A')} ({yuva.get('yil')})",
                    fill=True,
                    fill_opacity=0.8
                )

                # Duruma göre doğru kümeye ekle ve rengini ayarla
                if durum == "tam":
                    marker.options.update({'color': 'darkred', 'fillColor': 'red'})
                    marker.add_to(cluster_tam)
                elif durum in ["yari", "kismi"]:
                    marker.options.update({'color': 'darkblue', 'fillColor': 'blue'})
                    marker.add_to(cluster_yari)
                else:  # Sağlam
                    marker.options.update({'color': 'darkgreen', 'fillColor': 'green'})
                    marker.add_to(cluster_saglam)

        # 3. Isı haritası katmanını doldur (eğer veri varsa)
        if koordinatlar_heatmap:
            plugins.HeatMap(koordinatlar_heatmap, radius=15).add_to(grup_heatmap)

        # 4. Çizim eklentisini ekle
        self.draw_control = plugins.Draw(
            export=True, position="topleft",
            draw_options={"polyline": False, "marker": False, "circlemarker": False, "rectangle": True, "circle": True,
                          "polygon": True},
            edit_options={"edit": False, "remove": False}
        )
        self.draw_control.add_to(harita)


        script = """
            window.setupWebChannelAndDrawPlugin = function() {
                if (typeof qt === 'undefined' || !qt.webChannelTransport) { return; }
                try {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.MapCommunicator = channel.objects.MapCommunicator;
                        function setupDrawEvents() {
                            if (typeof map === 'undefined' || !map.on || !map.pm) { setTimeout(setupDrawEvents, 150); return; }
                            map.on('draw:created', function (e) {
                                var geojson = e.layer.toGeoJSON();
                                if (window.MapCommunicator) { window.MapCommunicator.receive_drawing_data(JSON.stringify(geojson)); }
                            });
                        }
                        setupDrawEvents();
                        window.toggleDrawModeJS = function(enable) { if (map && map.pm) { if (enable) map.pm.enableGlobalDrawMode(); else map.pm.disableGlobalDrawMode(); } };
                        window.clearDrawingsJS = function() { if (map && map.pm) map.pm.removeAllLayers(); };
                    });
                } catch (e) { console.error("QWebChannel başlatılırken hata: ", e); }
            };
        """
        harita.get_root().script.add_child(folium.Element(script))

        #tüm katmanları yönetecek olan kontrol paneli
        folium.LayerControl(collapsed=False).add_to(harita)

        return harita

    def populate_yuva_listesi(self, yuva_verisi=None):
        self.yuva_list_widget.blockSignals(True)
        self.yuva_list_widget.clear()

        yuvalar_ham = yuva_verisi if yuva_verisi is not None else tum_yuvalari_getir()

        # Listeyi ID'ye göre tersten sırala (en yeni en üstte)
        yuvalar = sorted(yuvalar_ham, key=lambda x: x.get('id', 0), reverse=True)

        for yuva in yuvalar:
            yuva_id = yuva.get('id', 'N/A')
            durum = str(yuva.get('predasyon_durumu', '')).lower()
            basari = yuva.get('yuva_basarisi_yuzde')

            durum_str = durum.capitalize() if durum else 'Belirsiz'
            item_text = f"ID: {yuva_id} - Durum: {durum_str}"

            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, yuva)

            # --- RENKLENDİRME MANTIĞI BURADA BAŞLIYOR ---


            if durum == "tam":
                list_item.setForeground(QColor('white'))
                list_item.setBackground(QColor('#DC3545'))  # Canlı Kırmızı


            elif durum in ["yari", "kismi"]:
                list_item.setForeground(QColor('white'))
                list_item.setBackground(QColor('#007BFF'))  # Canlı Mavi


            elif basari is not None:
                if basari >= 75:
                    # Yüksek başarılı yuvalar
                    list_item.setBackground(QColor('#D4EDDA'))  # Açık Yeşil
                    list_item.setForeground(QColor('#155724'))  # Koyu Yeşil Metin
                elif basari <= 25:
                    # Düşük başarılı yuvalar
                    list_item.setBackground(QColor('#FFF3CD'))  # Açık Sarı
                    list_item.setForeground(QColor('#856404'))  # Koyu Sarı/Kahve Metin



            self.yuva_list_widget.addItem(list_item)

        self.yuva_list_widget.blockSignals(False)
    def akilli_filtrele(self):
        arama_metni = self.arama_kutusu.text().lower().strip(); kriter = self.arama_kriteri_combo.currentText()
        for i in range(self.yuva_list_widget.count()):
            item = self.yuva_list_widget.item(i); yuva_data = item.data(Qt.ItemDataRole.UserRole); gorunur_yap = False
            if not arama_metni: gorunur_yap = True
            else:
                if kriter == "ID": hedef_metin = str(yuva_data.get('id', '')); gorunur_yap = arama_metni in hedef_metin
                elif kriter == "Yıl": hedef_metin = str(yuva_data.get('yil', '')); gorunur_yap = arama_metni in hedef_metin
                elif kriter == "Durum": hedef_metin = str(yuva_data.get('predasyon_durumu', '')).lower(); gorunur_yap = arama_metni in hedef_metin
                elif kriter == "Predatör": hedef_metin = ', '.join(yuva_data.get('predator_canli_listesi', [])).lower(); gorunur_yap = arama_metni in hedef_metin
                else: tum_bilgiler = ' '.join(str(v) for v in yuva_data.values()).lower(); gorunur_yap = arama_metni in tum_bilgiler
            item.setHidden(not gorunur_yap)

    def yuva_secildiginde_odaklan(self, current_item, previous_item):
        if not current_item: self.detay_id.setText("-"); self.detay_tarih.setText("-"); self.detay_yumurta_sayisi.setText("-"); self.detay_canli_yavru.setText("-"); self.detay_basari.setText("-"); self.detay_predasyon.setText("-"); self.statusBar().showMessage("Seçim kaldırıldı.", 3000); return
        try:
            yuva_data = current_item.data(Qt.ItemDataRole.UserRole); yuva_id = yuva_data.get('id'); yil = yuva_data.get('yil'); lat = yuva_data.get('lat'); lon = yuva_data.get('lon')
            self.statusBar().showMessage(f"[{yil}] ID: {yuva_id} olan yuva seçildi.", 3000)
            if self.map_object and lat is not None and lon is not None:
                js_script = f"var map = {self.map_object.get_name()}; map.setView([{lat}, {lon}], 18); setTimeout(function() {{ var targetLatLng = L.latLng({lat}, {lon}); var closestLayer = null; var minDistance = Infinity; map.eachLayer(function(layer) {{ if (layer instanceof L.Marker || layer instanceof L.CircleMarker) {{ var distance = targetLatLng.distanceTo(layer.getLatLng()); if (distance < minDistance) {{ minDistance = distance; closestLayer = layer; }} }} }}); if (closestLayer && minDistance < 1) {{ closestLayer.openPopup(); }} }}, 200);"; self.web_view.page().runJavaScript(js_script)
            self.detay_id.setText(f"{yuva_data.get('id', 'N/A')} ({yil})"); self.detay_tarih.setText(str(yuva_data.get('yuva_tarihi', 'N/A'))); self.detay_yumurta_sayisi.setText(str(yuva_data.get('toplam_yumurta_sayisi', 'N/A'))); self.detay_canli_yavru.setText(str(yuva_data.get('yuva_ici_canli_yavru', 'N/A')))
            basari_yuzde = yuva_data.get('yuva_basarisi_yuzde'); self.detay_basari.setText(f"{basari_yuzde}%" if basari_yuzde is not None else "N/A")
            predasyon_degeri = yuva_data.get('predasyon_durumu'); predasyon_str = str(predasyon_degeri).title() if predasyon_degeri else "Belirsiz"
            predatorler = yuva_data.get('predator_canli_listesi', []);
            if predatorler and isinstance(predatorler, list): guzel_predatorler = [p.title() for p in predatorler]; predasyon_str += f" ({', '.join(guzel_predatorler)})"
            self.detay_predasyon.setText(predasyon_str)
        except Exception as e: logging.error(f"Detay paneli güncellenirken hata: {e}", exc_info=True)

    def guvenli_dialog_ac(self, dialog_sinifi, *args, **kwargs):
        self.web_view.hide(); QApplication.processEvents(); time.sleep(0.05)
        dialog = None; result = QDialog.DialogCode.Rejected
        try: dialog = dialog_sinifi(parent=self, *args, **kwargs); result = dialog.exec()
        finally: self.web_view.show(); QApplication.processEvents()
        return dialog, result

    def yuva_ekle_dialog_ac(self):
        dialog, result = self.guvenli_dialog_ac(YuvaEkleDialog)
        if result == QDialog.DialogCode.Accepted:
            yeni_veri = dialog.get_data()
            if yeni_veri:
                try:
                    tarih_str = yeni_veri.get('yuva_tarihi'); yil = datetime.strptime(tarih_str, '%Y-%m-%d').year; yuva_id = yeni_veri.get('id')
                    if yuva_var_mi(yuva_id, yil): QMessageBox.critical(self, "Hata", f"{yil} yılı için ID: {yuva_id} zaten kullanılıyor!"); return
                    yuva_ekle(yeni_veri); self.harita_ve_liste_yenile(); QMessageBox.information(self, "Başarılı", f"ID: {yuva_id} ({yil}) eklendi!"); logging.info(f"ID {yuva_id} ({yil}) eklendi."); self.statusBar().showMessage(f"ID: {yuva_id} ({yil}) eklendi!", 4000)
                except (ValueError, TypeError) as e: QMessageBox.critical(self, "Veri Hatası", f"Geçersiz veri: {e}"); return

    def predasyon_dialog_ac(self):
        secili_item = self.yuva_list_widget.currentItem(); dialog, result = self.guvenli_dialog_ac(PredasyonDialog)
        if secili_item:
            yuva_data = secili_item.data(Qt.ItemDataRole.UserRole); dialog.id_input.setText(str(yuva_data.get('id', ''))); dialog.yil_input.setText(str(yuva_data.get('yil', '')))
        if result == QDialog.DialogCode.Accepted:
            veri = dialog.get_data()
            if not veri: QMessageBox.warning(self, "Hata", "Lütfen geçerli bir Yuva ID ve Yıl girin."); return
            if not yuva_var_mi(veri['id'], veri['yil']): QMessageBox.warning(self, "Hata", f"{veri['yil']} yılı için {veri['id']} ID'li bir yuva bulunamadı."); return
            yuva_predasyon_guncelle(veri['id'], veri['yil'], veri['durum'], veri['turler']); self.harita_ve_liste_yenile(); QMessageBox.information(self, "Başarılı", f"[{veri['yil']}] ID: {veri['id']} durumu güncellendi."); logging.info(f"KULLANICI EYLEMİ: [{veri['yil']}] ID: {veri['id']} durumu güncellendi."); self.statusBar().showMessage(f"[{veri['yil']}] ID: {veri['id']} durumu güncellendi!", 4000)

    def yuva_sil_dialog_ac(self):
        secili_itemler = self.yuva_list_widget.selectedItems()

        if not secili_itemler:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen silmek için listeden bir veya daha fazla yuva seçin.")
            return
        silinecek_yuvalar = []
        for item in secili_itemler:
            yuva_data = item.data(Qt.ItemDataRole.UserRole)
            yuva_id = yuva_data.get('id')
            yuva_yil = yuva_data.get('yil')
            if yuva_id and yuva_yil:
                silinecek_yuvalar.append((yuva_id, yuva_yil))

        if not silinecek_yuvalar:
            QMessageBox.critical(self, "Hata", "Seçili yuvaların ID veya Yıl bilgisi bulunamadı.")
            return

        cevap = QMessageBox.question(self, 'Onay',
                                     f"Seçili {len(silinecek_yuvalar)} adet yuvayı ve tüm verilerini silmek istediğinizden emin misiniz?\n"
                                     "Bu işlem geri alınamaz!",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if cevap == QMessageBox.StandardButton.Yes:
            # Veritabanından toplu silme işlemi yap
            toplu_yuva_sil(silinecek_yuvalar)

            self.harita_ve_liste_yenile()
            QMessageBox.information(self, "Başarılı", f"{len(silinecek_yuvalar)} adet yuva başarıyla silindi.")
            logging.warning(f"KULLANICI EYLEMİ: {len(silinecek_yuvalar)} adet yuva toplu olarak silindi.")
            self.statusBar().showMessage(f"{len(silinecek_yuvalar)} adet yuva silindi!", 4000)

    def gelismis_grafik_penceresi_ac(self):
        """Gelişmiş Grafik diyalog penceresini güvenli bir şekilde açar."""

        dialog, result = self.guvenli_dialog_ac(GelismisGrafikDialog)

    def istatistik_penceresi_ac(self):
        dialog, result = self.guvenli_dialog_ac(IstatistikDialog)
        self.statusBar().showMessage("İstatistik raporu penceresi kapatıldı.", 3000)
    def karsilastirma_penceresi_ac(self): dialog, result = self.guvenli_dialog_ac(KarsilastirmaDialog); self.statusBar().showMessage("Veri karşılaştırma aracı görüntülendi.", 3000)
    def hakkinda_penceresi_ac(self): dialog, result = self.guvenli_dialog_ac(HakkindaDialog); self.statusBar().showMessage("Hakkında penceresi görüntülendi.", 3000)
    def simulasyon_penceresi_ac(self): dialog, result = self.guvenli_dialog_ac(SimulasyonDialog); self.statusBar().showMessage("Simülasyon aracı görüntülendi.", 3000)

    def excel_import_dialog_ac(self):
        self.web_view.hide(); QApplication.processEvents(); time.sleep(0.05);
        try: dosya_yolu, _ = QFileDialog.getOpenFileName(self, "Excel'den Veri Al", "", "Excel Dosyaları (*.xlsx *.xls)")
        finally: self.web_view.show(); QApplication.processEvents()
        if dosya_yolu:
            eklenen_sayisi, mesaj = excelden_toplu_ekle(dosya_yolu); QMessageBox.information(self, "İşlem Tamamlandı", mesaj); logging.info(f"Excel aktarım: {mesaj}")
            if eklenen_sayisi > 0: self.harita_ve_liste_yenile()
            self.statusBar().showMessage(mesaj, 5000)

    def excel_export_dialog_ac(self):
        df = yuvalari_dataframe_yap()
        if df.empty: QMessageBox.warning(self, "Veri Yok", "Dışa aktarılacak veri bulunamadı."); return
        self.web_view.hide(); QApplication.processEvents(); time.sleep(0.05);
        try: dosya_yolu, _ = QFileDialog.getSaveFileName(self, "Verileri Excel'e Aktar", "patara_yuva_verileri.xlsx", "Excel Dosyaları (*.xlsx)")
        finally: self.web_view.show(); QApplication.processEvents()
        if dosya_yolu:
            try:
                if 'predator_canli_listesi' in df.columns: df['predator_canli_listesi'] = df['predator_canli_listesi'].apply(lambda d: ', '.join(d) if isinstance(d, list) else d)
                yeni_sutun_isimleri = {sutun: sutun.replace('_', ' ').title() for sutun in df.columns}; df.rename(columns=yeni_sutun_isimleri, inplace=True)
                df.to_excel(dosya_yolu, index=False, engine='openpyxl'); QMessageBox.information(self, "Başarılı", f"Veriler '{dosya_yolu}' dosyasına kaydedildi."); logging.info(f"Veriler Excel'e aktarıldı: {dosya_yolu}")
                self.statusBar().showMessage(f"Veriler Excel'e aktarıldı: {os.path.basename(dosya_yolu)}", 5000)
            except Exception as e: QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}"); logging.error(f"Excel'e aktarma hatası: {e}", exc_info=True)

    def yedekten_geri_yukle(self):
        yedekler_klasoru = os.path.join(SCRIPT_DIR, "backups")
        if not os.path.exists(yedekler_klasoru): QMessageBox.warning(self, "Yedek Bulunamadı", "Hiç yedek dosyası bulunamadı."); return
        self.web_view.hide(); QApplication.processEvents(); time.sleep(0.05);
        try: dosya_yolu, _ = QFileDialog.getOpenFileName(self, "Geri Yüklenecek Yedeği Seçin", yedekler_klasoru, "Veritabanı Yedekleri (*.db)")
        finally: self.web_view.show(); QApplication.processEvents()
        if dosya_yolu:
            cevap = QMessageBox.question(self, 'Onay', "Mevcut veritabanı seçilen yedek ile değiştirilecek.\nBu işlem geri alınamaz. Emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if cevap == QMessageBox.StandardButton.Yes:
                try:
                    shutil.copy2(dosya_yolu, DB_PATH); QMessageBox.information(self, "Başarılı", "Veritabanı geri yüklendi."); logging.warning(f"Veritabanı '{os.path.basename(dosya_yolu)}' yedeğinden geri yüklendi."); self.harita_ve_liste_yenile(); self.statusBar().showMessage("Veritabanı yedekten geri yüklendi.", 4000)
                except Exception as e: QMessageBox.critical(self, "Hata", f"Geri yükleme hatası: {e}"); logging.error(f"Yedekten geri yükleme hatası: {e}", exc_info=True)

    def otomatik_yedekle(self):
        try:
            yedekler_klasoru = os.path.join(SCRIPT_DIR, "backups");
            if not os.path.exists(yedekler_klasoru): os.makedirs(yedekler_klasoru)
            tarih_damgasi = datetime.now().strftime("%Y-%m-%d_%H-%M-%S"); yedek_dosya_yolu = os.path.join(yedekler_klasoru, f"caretta_final_{tarih_damgasi}.db")
            if os.path.exists(DB_PATH): shutil.copy2(DB_PATH, yedek_dosya_yolu); logging.info(f"Veritabanı yedeklendi: {yedek_dosya_yolu}")
        except Exception as e: logging.error(f"Yedekleme hatası: {e}", exc_info=True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            dosya_yolu = urls[0].toLocalFile()
            if dosya_yolu.lower().endswith(('.xlsx', '.xls')):
                logging.info(f"Kullanıcı Excel dosyası sürükledi: {dosya_yolu}")
                cevap = QMessageBox.question(self, 'Excel Dosyası Algılandı', f"'{os.path.basename(dosya_yolu)}' dosyasını aktarmak istiyor musunuz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if cevap == QMessageBox.StandardButton.Yes:
                    eklenen_sayisi, mesaj = excelden_toplu_ekle(dosya_yolu)
                    logging.info(f"Excel aktarım sonucu: {mesaj}"); QMessageBox.information(self, "İşlem Tamamlandı", mesaj)
                    if eklenen_sayisi > 0: self.harita_ve_liste_yenile()
                    self.statusBar().showMessage(mesaj, 5000)
            else: QMessageBox.warning(self, "Geçersiz Dosya Türü", "Lütfen sadece Excel (.xlsx, .xls) dosyası sürükleyin.")
        super().dropEvent(event)

    def closeEvent(self, event):
        logging.info("Uygulama kapatılıyor..."); self.otomatik_yedekle()
        if hasattr(self, 'gelismis_grafik_penceresi') and self.gelismis_grafik_penceresi: self.gelismis_grafik_penceresi.close()
        super().closeEvent(event)


# ==============================================================================
# BÖLÜM 5: UYGULAMAYI BAŞLATMA
# ==============================================================================

if __name__ == "__main__":
    # 1. Gerekli Kurulumlar
    setup_logging()
    os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = "1"
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)

    # 2. Uygulama Nesnesi
    app = QApplication(sys.argv)

    # 3. Açılış Ekranını Hazırla ve Göster
    splash_path = os.path.join(SCRIPT_DIR, "splash.png")
    splash = None
    if os.path.exists(splash_path):
        try:
            pixmap = QPixmap(splash_path)
            splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
            splash.show()
            app.processEvents()  # Ekranın hemen çizilmesini sağla
        except Exception as e:
            logging.error(f"Splash ekranı hatası: {e}");
            splash = None
    else:
        logging.warning("splash.png bulunamadı, açılış ekranı atlanıyor.")

    # 4. Uzun Süren İşlemleri Yap
    if splash: splash.showMessage("Veritabanı kontrol ediliyor...",
                                  Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    time.sleep(0.5);
    app.processEvents()
    setup_database()

    # 5. Ana Pencereyi Oluştur ve referansını GÜVENDE TUT
    if splash: splash.showMessage("Ana pencere yükleniyor...",
                                  Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    time.sleep(0.5);
    app.processEvents()

    main_window = MainWindow()
    main_window.show()

    # 6. Haritayı, pencere göründükten SONRA yükle
    main_window.harita_ve_liste_yenile()

    # 7. Splash Ekranını Kapat
    if splash:
        splash.finish(main_window)

    # 8. Uygulama Ana Döngüsünü Başlat
    logging.info("Uygulama ana döngüsü başlatıldı.")
    sys.exit(app.exec())