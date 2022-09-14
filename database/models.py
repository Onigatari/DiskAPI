import datetime
import enum
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, event, select, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.engine import Connection
from sqlalchemy.orm import relationship, backref
from sqlalchemy_utils import ChoiceType

from database.engine import Session
from database.base import Base, HistoryBase


class SystemItemType(str, enum.Enum):
    FILE = 'FILE'
    FOLDER = 'FOLDER'


class SystemItem(Base):
    __tablename__ = "system_item"
    url = Column(String, nullable=True)
    date = Column(DateTime(timezone=datetime.timezone.utc), nullable=False, default=datetime.datetime.utcnow)
    type = Column(ChoiceType(SystemItemType, impl=String()), nullable=False)
    parentId = Column(UUID(as_uuid=True), ForeignKey('system_item.id'),
                      index=True, default=None,
                      nullable=True)
    size = Column(Integer, nullable=True)

    children: List["SystemItem"] = relationship(
        "SystemItem",
        backref=backref('parent', remote_side='SystemItem.id'),
        uselist=True, cascade="all, delete"
    )

    def get_child(self, index: int = 0) -> Optional["SystemItemType"]:
        if len(self.children) > index:
            return self.children[index]
        return None

    def __str__(self):
        return f'{self.url} {self.type}'

    def __repr__(self):
        return f'<SystemItem {self.name}>'


class HistoryItem(HistoryBase):
    __tablename__ = "history_item"
    id = Column(String, ForeignKey('system_item.id', ondelete='CASCADE'), nullable=False)
    url = Column(String, nullable=True)
    date = Column(DateTime(timezone=datetime.timezone.utc), primary_key=True, nullable=False)
    type = Column(ChoiceType(SystemItemType, impl=String()), nullable=False)
    parentId = Column(UUID(as_uuid=True), default=None, nullable=True)
    size = Column(Integer, nullable=True)

    def __str__(self):
        return f'{self.url} {self.type}'

    def __repr__(self):
        return f'<HistorySystemItem {self.name}>'


@event.listens_for(SystemItem, 'after_insert')
def do_something(mapper, connection: Connection, target):
    if target.parentId is not None:
        session = Session()
        parent = session.query(SystemItem).filter_by(id=target.parentId).one()
        parent.date = target.date
        session.add(parent)
        session.commit()


@event.listens_for(SystemItem, 'after_update')
def do_something(mapper, connection: Connection, target: SystemItem):
    if target.parentId is not None:
        session = Session()
        parent = session.query(SystemItem).filter_by(id=target.parentId).one()
        parent.date = target.date
        session.add(parent)
        session.commit()
