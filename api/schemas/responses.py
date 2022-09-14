from api.schemas.error import ErrorResult

HTTP_400_RESPONSE = {
            'description': 'Невалидная схема документа или входные данные не верны',
            'model': ErrorResult,
            'content': {
                'application/json': {
                    'example': {
                        'code': 400,
                        'message': 'Validation Failed',
                    }
                }
            }
        }

HTTP_404_RESPONSE = {
            'description': 'Элемент не найден',
            'model': ErrorResult,
            'content': {
                'application/json': {
                    'example': {
                        'code': 404,
                        'message': 'Item not found',
                    }
                }
            }
        }