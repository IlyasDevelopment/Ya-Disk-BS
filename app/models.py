import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ItType(enum.Enum):
    FOLDER = "FOLDER"
    FILE = "FILE"


class Item(Base):
    __tablename__ = "items"
    item_id = Column(Integer, primary_key=True, index=True)
    id = Column(Text, unique=True)
    type = Column(Enum(ItType))
    parentId = Column(Text, nullable=True)
    url = Column(String(255), nullable=True)
    size = Column(Integer, nullable=True)
    date = Column(DateTime)
    filename = Column(Text, nullable=True)

    __table_args__ = (
        Index("file_id_index", "id"),
        Index("parent_id_index", "parentId"),
        )


def to_dict(model_instance, query_instance=None):
    if hasattr(model_instance, '__table__'):
        return {c.name: getattr(model_instance, c.name) for c in model_instance.__table__.columns}
    else:
        cols = query_instance.column_descriptions
        return {cols[i]['name']: model_instance[i] for i in range(len(cols))}

# def from_dict(dict, model_instance):
#     for c in model_instance.__table__.columns:
#         setattr(model_instance, c.name, dict[c.name])
