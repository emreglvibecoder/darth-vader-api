from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
import requests
from textblob import TextBlob
from passlib.context import CryptContext

# 1. GÜVENLİK VE ŞİFRELEME AYARLARI
SECRET_KEY = "darth-vader-gizli-anahtar" # Bu anahtar token üretmek için kullanılır
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 2. VERİTABANI AYARLARI
DATABASE_URL = "sqlite:///./yapilacaklar.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TodoDB(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    baslik = Column(String)
    tamamlandi = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# 3. API NESNESİ VE MODELLER
app = FastAPI()

class TodoSema(BaseModel):
    baslik: str
    tamamlandi: bool = False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. GÜVENLİK FONKSİYONLARI (KAPICI)
def kullanici_dogrula(token: str = Depends(oauth2_scheme)):
    # Şimdilik basit tutuyoruz: Eğer token 'admin' ise geçiş ver
    if token != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz anahtar (Token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# --- ENDPOİNTLER ---

# Giriş yapma ve Token alma noktası
@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Kullanıcı adı: admin, Şifre: 12345
    if form_data.username == "admin" and form_data.password == "12345":
        return {"access_token": "admin", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="Hatalı kullanıcı adı veya şifre")

@app.get("/")
def ana_sayfa():
    return {"mesaj": "Güvenli API'ye Hoş Geldin!"}

# BU KISIM ARTIK KORUMALI (Depends(kullanici_dogrula) eklendi)
@app.get("/listele/")
def gorevleri_getir(token: str = Depends(kullanici_dogrula), db: Session = Depends(get_db)):
    return db.query(TodoDB).all()

@app.post("/ekle/")
def gorev_ekle(item: TodoSema, db: Session = Depends(get_db)):
    yeni_gorev = TodoDB(baslik=item.baslik, tamamlandi=item.tamamlandi)
    db.add(yeni_gorev)
    db.commit()
    db.refresh(yeni_gorev)
    return {"mesaj": "Görev eklendi!", "id": yeni_gorev.id}

@app.get("/analiz/{cumle}")
def duygu_analizi(cumle: str):
    puan = TextBlob(cumle).sentiment.polarity
    durum = "Pozitif 😊" if puan > 0 else "Negatif 😔" if puan < 0 else "Nötr 😐"
    return {"metin": cumle, "duygu": durum}

@app.get("/doviz-hesapla/{miktar}")
def doviz_getir(miktar: float):
    url = "https://api.frankfurter.app/latest?from=EUR&to=TRY"
    try:
        kur = requests.get(url).json()["rates"]["TRY"]
        return {"miktar_eur": miktar, "toplam_tl": round(miktar * kur, 2)}
    except:
        return {"hata": "Kur verisi alınamadı."}
