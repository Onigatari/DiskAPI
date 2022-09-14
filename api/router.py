import datetime
from loguru import logger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import Response
from typing import Dict, Union
from uuid import UUID
from api.schemas.system_item import SystemItemImportRequest, SystemItemSchema, SystemItemStatisticResponse, \
    SystemItemResponseSchema, HistoryResponseSchema

from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from api.schemas.responses import HTTP_400_RESPONSE, HTTP_404_RESPONSE

from database.engine import get_session
from database.models import SystemItem, SystemItemType, HistoryItem

router = APIRouter()


@router.get('/test', tags=['Тестовый запрос'])
def test_reqest():
    return {'Status': 'OK'}


@router.post('/imports', status_code=200, tags=['Базовые задачи'])
def import_reqest(files: SystemItemImportRequest, session: Session = Depends(get_session)) -> Response:
    """
    Импортирует элементы файловой системы.
    """

    id_set = set()
    parent_set = set()
    file_set = set()
    
    for file_item in files.items:
        if str(file_item.id) in id_set:
            raise HTTPException(status_code=400, detail='Item with this ID already exists')

        id_set.add(str(file_item.id))

        file_parent = session.query(SystemItem).filter(SystemItem.id == file_item.parentId).one_or_none()

        if file_item.parentId is not None:
            if file_parent is not None:
                if file_parent.type == SystemItemType.FILE:
                    raise HTTPException(status_code=400, detail='File can\'t be a parent')
            else:
                parent_set.add(str(file_item.parentId))

        if str(file_item.type) == 'FILE':
            file_set.add(str(file_item.type))

        file_item.date = files.update_date
        system_item_model = session.query(SystemItem).filter(SystemItem.id == file_item.id).one_or_none()
        if system_item_model is not None:
            if system_item_model.type != file_item.type:
                raise HTTPException(status_code=400, detail='Can\'t change type items')

            for var, value in vars(file_item).items():
                setattr(system_item_model, var, value)
            session.add(system_item_model)
        else:
            session.add(SystemItem(**file_item.dict()))

        if not (id_set >= parent_set):
            raise HTTPException(status_code=400, detail='Impossible parent link')
        if file_set.intersection(parent_set) != set():
            raise HTTPException(status_code=400, detail='Can\'t be a parent')

        session.commit()
        
    date = files.update_date
    updated_items = session.query(SystemItem).filter(SystemItem.date == date).all()

    if updated_items:
        for item in updated_items:
            temp = {
                "id": str(item.id),
                "type": str(item.type).split('.')[1],
                "url": item.url
            }

            if str(item.parentId) is not None:
                temp["parentId"] = str(item.parentId)

            session.add(HistoryItem(**temp))
            temp["size"] = item_get_size(item)
            temp["date"] = str(item.date.astimezone(datetime.timezone.utc))

        session.commit()

    return Response(status_code=200)


@router.get('/nodes/{id}/',
            response_model=SystemItemSchema, response_model_by_alias=True,
            tags=['Базовые задачи'])
def get_reqest(id: Union[UUID, str], session: Session = Depends(get_session)):
    """
    Получить информацию об элементе по идентификатору.
    """
    item = session.query(SystemItem).filter_by(id=id).one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail='Item not found')

    element: SystemItemResponseSchema = SystemItemResponseSchema.from_orm(item)
    if element.type == SystemItemType.FOLDER:
        temp = [[element, 0, 0]]
        while len(temp):
            last, index = temp[-1][0], temp[-1][1]
            child = last.get_child(index)
            if child is not None:
                temp[-1][1] += 1
                if child.type == SystemItemType.FILE:
                    temp[-1][2] += child.size
                else:
                    temp.append([child, 0, 0])
            else:
                last.size = temp[-1][2]
                if len(temp) > 1:
                    temp[-2][2] += temp[-1][2]
                temp.pop()
    return element


@router.delete('/delete/{id}',
               status_code=200,
               responses={
                   200: {
                       'description': 'Удаление прошло успешно',
                       'model': None,
                   },
                   HTTP_400_BAD_REQUEST: HTTP_400_RESPONSE,
                   HTTP_404_NOT_FOUND: HTTP_404_RESPONSE,
               },
               tags=['Базовые задачи'])
def delete_reqest(id: UUID,
                  session: Session = Depends(get_session)) -> Response:
    """
    Удалить элемент по идентификатору.
    """
    system_item = session.query(SystemItem).filter_by(id=id).one_or_none()
    if system_item is None:
        raise HTTPException(status_code=404, detail='Item not found')
    try:
        session.delete(system_item)
        session.commit()
        return Response(status_code=HTTP_200_OK)
    except Exception as e:
        raise HTTPException(status_code=400, detail='Validation Failed')


@router.get('/updates', status_code=200, tags=['Дополнительные задачи'],
            response_model=SystemItemStatisticResponse)
def updates_reqest(date: datetime.datetime, session: Session = Depends(get_session)) -> SystemItemStatisticResponse:
    """
    Получение списка файлов, которые были обновлены за последние 24 часа включительно от времени переданном в запросе.
    """
    items = session.query(SystemItem).filter(
        SystemItem.type == SystemItemType.FILE,
        SystemItem.date <= date,
        SystemItem.date >= date - datetime.timedelta(days=1),
    ).all()
    return SystemItemStatisticResponse(items=items)


@router.get('/node/{id}/history',
            response_model=HistoryResponseSchema, response_model_by_alias=True,
            tags=['Дополнительные задачи'])
def history_reqest(id: str, dateStart: datetime.datetime = None, dateEnd: datetime.datetime = None,
                   session: Session = Depends(get_session)):
    """
    Получить информацию об элементе по идентификатору.
    """
    if dateStart is None:
        dateStart = datetime.datetime.min
    if dateEnd is None:
        dateEnd = datetime.datetime.max

    items = session.query(HistoryItem).filter(
        HistoryItem.id == id,
        HistoryItem.date >= dateStart,
        HistoryItem.date < dateEnd).all()

    return {"items": items}


def item_get_size(item: SystemItem):
    size = 0
    if item.type == SystemItemType.FOLDER:
        for child in item.children:
            size += item_get_size(child)
        return size
    elif item.type == SystemItemType.FILE:
        return item.size
