from sqlalchemy import String, DateTime, func, ARRAY, Date, BigInteger, Integer, Float
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()



class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    telegram_login: Mapped[str] = mapped_column(String(400), nullable=False)
    name: Mapped[str] = mapped_column(String(400), nullable=False)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    email: Mapped[str] = mapped_column(String(500), nullable=True)
    distance_1: Mapped[int] = mapped_column(Float, nullable=True)
    photo_1: Mapped[str] = mapped_column(String(150), nullable=True)
    story_1: Mapped[str] = mapped_column(String(150), nullable=True)
    date_1: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    distance_2: Mapped[int] = mapped_column(Float, nullable=True)
    photo_2: Mapped[str] = mapped_column(String(150), nullable=True)
    story_2: Mapped[str] = mapped_column(String(150), nullable=True)
    date_2: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    distance_3: Mapped[int] = mapped_column(Float, nullable=True)
    photo_3: Mapped[str] = mapped_column(String(150), nullable=True)
    story_3: Mapped[str] = mapped_column(String(150), nullable=True)
    date_3: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    index: Mapped[str] = mapped_column(String(10), nullable=True)
    city: Mapped[str] = mapped_column(String(150), nullable=True)
    address: Mapped[str] = mapped_column(String(400), nullable=True)
    result: Mapped[int] = mapped_column(Float, nullable=True)


class Telegram_ID(Base):
    __tablename__ = 'telegram_id'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)

