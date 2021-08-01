from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

sql = create_engine('sqlite:///orders.db')
BaseModel = declarative_base()


class Order(BaseModel):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(100))
    user_id = Column(String(100))
    name = Column(String(100))
    state = Column(String(10))
    result_path = Column(String(100), nullable=True)
    positions = Column(String(300))
    date = Column(DateTime, default=datetime.utcnow)


BaseModel.metadata.create_all(sql)

DB = sessionmaker(bind=sql)
