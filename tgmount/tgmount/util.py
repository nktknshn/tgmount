import json
from datetime import datetime


def document_to_dict(document):
    return {
        'id': str(document['id']),  # jq
        'message_id': int(document['message_id']),
        'message_date': document['message_date'],
        'document_date': document['document_date'],
        'mime_type': document['mime_type'],
        'size': document['size'],
        'attributes': document['attributes'],
    }


def none_or_int(value):
    if value is None:
        return None

    return int(value)


def int_or_string(value):

    try:
        return int(value)
    except ValueError:
        return str(value)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):  # pylint: disable=E0202
        if isinstance(o, datetime):
            return o.isoformat()

        return super().default(o)
