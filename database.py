from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///bot_database.db"

Base = declarative_base()


class UserPayments(Base):
    __tablename__ = "user_payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True)  # ID пользователя Telegram
    status = Column(String, default="не оплачено")
    verified = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey("group_links.id"), nullable=False)  # ID группы
    group = relationship("Groups", back_populates="payments")  # Связь с группой


class Groups(Base):
    __tablename__ = "group_links"
    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String, unique=True, index=True, nullable=False)  # Название группы
    group_id = Column(BigInteger, unique=True, nullable=False)  # ID группы Telegram
    payments = relationship("UserPayments", back_populates="group")  # Связь с платежами


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)

