from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from pydantic import BaseModel
from typing import List
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
import requests
from textblob import TextBlob

# 1. AYARLAR VE GÜVENLİK
DATABASE_URL = "sqlite:///./yapilacaklar.db"
SECRET_KEY = "vader-secret-key"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. VERİTABANI MODELLERİ
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    todos = relationship("TodoDB", back_populates="owner")

class TodoDB(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    baslik = Column(String)
    tamamlandi = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("UserDB", back_populates="todos")

Base.metadata.create_all(bind=engine)

# 3. API NESNESİ VE CORS
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# 4. YARDIMCI FONKSİYONLAR
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == token).first() # Basitleştirilmiş token
    if not user:
        raise HTTPException(status_code=401, detail="Geçersiz oturum")
    return user

# 5. ENDPOINTLER (KAYIT VE GİRİŞ)
@app.post("/register")
def register(username: str, sifre: str, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.username == username).first():
        raise HTTPException(status_code=400, detail="Bu kullanıcı adı alınmış")
    yeni_user = UserDB(username=username, hashed_password=pwd_context.hash(sifre))
    db.add(yeni_user)
    db.commit()
    return {"mesaj": "Kayıt başarılı, karanlık tarafa hoş geldin."}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Hatalı giriş")
    return {"access_token": user.username, "token_type": "bearer"}

# 6. GÖREV ENDPOINTLERİ (KULLANICIYA ÖZEL)
@app.get("/listele/")
def listele(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    return user.todos

@app.post("/ekle/")
def ekle(baslik: str, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    yeni = TodoDB(baslik=baslik, owner_id=user.id)
    db.add(yeni)
    db.commit()
    return {"durum": "başarılı"}

# ... (AI ve Döviz endpointleri aynı kalabilir) ...
@app.get("/analiz/{cumle}")
def analiz(cumle: str):
    puan = TextBlob(cumle).sentiment.polarity
    return {"duygu": "Pozitif 😊" if puan > 0 else "Negatif 😔" if puan < 0 else "Nötr 😐"}

@app.get("/doviz-hesapla/{miktar}")
def doviz(miktar: float):
    kur = requests.get("https://api.frankfurter.app/latest?from=EUR&to=TRY").json()["rates"]["TRY"]
    return {"toplam_tl": round(miktar * kur, 2)}


