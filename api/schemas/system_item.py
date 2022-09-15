from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, validator, root_validator
from loguru import logger
from database.models import SystemItemType


def convert_datetime_to_iso_8601_with_z_suffix(dt: datetime) -> str:
    return dt.isoformat(timespec='milliseconds', ).replace('+00:00', 'Z')


class SystemItemBaseSchema(BaseModel):
    id: UUID
    url: Optional[str]
    date: Optional[datetime]
    parentId: Optional[UUID] = Field(alias='parentId')
    type: SystemItemType
    size: Optional[int]

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True
        orm_mode = True
        allow_population_by_field_name = True

        json_encoders = {
            datetime: convert_datetime_to_iso_8601_with_z_suffix
        }


class SystemItemImport(SystemItemBaseSchema):
    @root_validator
    def check_size_type(cls, values):
        size = values.get('size')
        type = values.get('type')
        url = values.get('url')
        assert ((SystemItemType(type) == SystemItemType.FOLDER and size is None and url is None) or (
                SystemItemType(type) == SystemItemType.FILE and size > 0 and len(url) <= 255))

        return values


class SystemItemImportRequest(BaseModel):
    items: List[SystemItemImport]
    update_date: datetime = Field(alias='updateDate')


class SystemItemSchema(SystemItemBaseSchema):
    children: List["SystemItemSchema"] = None

    @validator("children")
    def replace_empty_list(cls, v):
        return v or None

    def get_child(self, index):
        if len(self.children) > index:
            return self.children[index]
        return None


# class SystemItemSchema(SystemItemBaseSchema):
#     children: List["SystemItemBaseSchema"] = None
#
#     @validator("children")
#     def replace_empty_list(cls, v):
#         return v or None
#
#     def get_child(self, index):
#         if len(self.children) > index:
#             return self.children[index]
#         return None

class SystemItemResponseSchema(SystemItemBaseSchema):
    children: List["SystemItemResponseSchema"] = None

    @validator("date")
    def date_conversion(cls, v):
        return convert_datetime_to_iso_8601_with_z_suffix(v)

    @validator("children")
    def replace_empty_list(cls, v, values):
        type = values.get("type")
        if type == SystemItemType.FILE:
            return v or None
        else:
            return v or list()

    def get_child(self, index):
        try:
            if len(self.children) > index:
                return self.children[index]
        except:
            pass
        return None


# class HistoryBaseSchema(BaseModel):
#     id: UUID
#     url: Optional[str]
#     parentId: Optional[UUID] = Field(alias='parentId')
#     size: Optional[int]
#     type: SystemItemType
#     date: Optional[datetime]
#
#     class Config:
#         use_enum_values = True
#         arbitrary_types_allowed = True
#         orm_mode = True
#         allow_population_by_field_name = True
#
#     @validator("date")
#     def date_conversion(cls, v):
#         return convert_datetime_to_iso_8601_with_z_suffix(v)
#
#
# class HistoryResponseSchema(BaseModel):
#     items: List[HistoryBaseSchema]
#
#

class SystemItemStatisticResponse(BaseModel):
    items: List[SystemItemBaseSchema]

    class Config:
        orm_mode = True


SystemItemSchema.update_forward_refs()
