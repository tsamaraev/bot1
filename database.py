from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///bot_database.db"

Base = declarative_base()

class UserPayments(Base):
    __tablename__ = "user_payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    payment_time = Column(DateTime, default=datetime.now)
    invoice_payload = Column(String, nullable=False)
    status = Column(String, default="не оплачено")
    verified = Column(Boolean, default=False)

class GroupLinks(Base):
    __tablename__ = "group_links"
    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String, unique=True, index=True)
    link = Column(String)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(engine)
