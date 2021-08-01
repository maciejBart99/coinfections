import uuid

from sqlalchemy.orm import Session

from order import Order
from pipeline import send_task


def get_all_orders(user_id: str, db: Session) -> Order:
    return db.query(Order).filter_by(user_id=user_id).all()


def get_by_id(order_id: int, db: Session) -> Order:
    return db.query(Order).filter_by(id=order_id).one()


def create_order(name, file_1, file_2, user_id, positions, db: Session) -> str:
    token = str(uuid.uuid4())
    order = Order(name=name, state='WAITING', user_id=user_id, token=token, positions=positions)
    db.add(order)
    db.commit()
    db.refresh(order)

    send_task(file_1, file_2, order.id, [int(x) for x in positions.split(',')])

    return token
