from datetime import datetime
from bson import ObjectId
import json
import typing
from fastapi.responses import JSONResponse

def custom_json_encoder(obj: typing.Any) -> typing.Any:
    """
    Custom JSON encoder function for handling special types like ObjectId and datetime.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class CustomJSONResponse(JSONResponse):
    """
    JSONResponse subclass that uses the custom encoder to handle ObjectId and datetime.
    """
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=custom_json_encoder,
        ).encode("utf-8")
