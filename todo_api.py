from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

# 1. Veritabanı Ayarları
DATABASE_URL = "sqlite:///./yapilacaklar.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Veritabanı Tablo Modeli
class TodoDB(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    baslik = Column(String)
    tamamlandi = Column(Boolean, default=False)

# Tabloyu oluştur
Base.metadata.create_all(bind=engine)

# 3. API Nesnesini Oluştur (BURASI ÖNEMLİ: Her şeyden önce tanımlanmalı)
app = FastAPI()

# 4. Veri Yapısı (Pydantic)
class TodoSema(BaseModel):
    baslik: str
    tamamlandi: bool = False

# Veritabanı bağlantı yardımcısı
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ENDPOİNTLER (Rotalar) ---

@app.get("/")
def ana_sayfa():
    return {"mesaj": "API Çalışıyor! Test için /docs adresine git."}

@app.post("/ekle/")
def gorev_ekle(item: TodoSema, db: Session = Depends(get_db)):
    yeni_gorev = TodoDB(baslik=item.baslik, tamamlandi=item.tamamlandi)
    db.add(yeni_gorev)
    db.commit()
    db.refresh(yeni_gorev)
    return {"mesaj": "Görev kaydedildi!", "id": yeni_gorev.id}

@app.get("/listele/")
def gorevleri_getir(db: Session = Depends(get_db)):
    liste = db.query(TodoDB).all()
    return liste
from textblob import TextBlob

# --- YAPAY ZEKA ENDPOİNTİ ---

@app.get("/analiz/{cumle}")
def duygu_analizi(cumle: str):
    # TextBlob ile metni analiz ediyoruz
    analiz = TextBlob(cumle)
    
    # polarity (kutupsallık) -1 ile 1 arasındadır. 
    # 0'dan büyükse pozitif, küçükse negatiftir.
    puan = analiz.sentiment.polarity
    
    if puan > 0:
        durum = "Pozitif / Mutlu 😊"
    elif puan < 0:
        durum = "Negatif / Üzgün 😔"
    else:
        durum = "Nötr / Belirsiz 😐"
    
    return {
        "metin": cumle,
        "analiz_puani": puan,
        "duygu_durumu": durum
    }

import requests

# --- DIŞ DÜNYA (EXTERNAL API) ENDPOİNTİ ---

@app.get("/doviz-hesapla/{miktar}")
def doviz_getir(miktar: float):
    # Ücretsiz bir döviz kuru API'sine (Frankfurter) istek atıyoruz
    # Bu API Euro bazlı kurları verir
    url = "https://api.frankfurter.app/latest?from=EUR&to=TRY"
    
    try:
        yanit = requests.get(url)
        veri = yanit.json() # Gelen veriyi Python sözlüğüne çeviriyoruz
        
        kur = veri["rates"]["TRY"]
        toplam_tl = miktar * kur
        
        return {
            "birim": "Euro",
            "miktar": miktar,
            "guncel_kur": kur,
            "toplam_tl_karsiligi": round(toplam_tl, 2),
            "kaynak": "Frankfurter API"
        }
    except Exception as e:
        return {"hata": "Veri çekilemedi, internet bağlantınızı kontrol edin."}

