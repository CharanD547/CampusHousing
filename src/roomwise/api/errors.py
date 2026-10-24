from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, code, message, status=422, retryable=False):
        self.code, self.message, self.status, self.retryable = code, message, status, retryable


def error_response(code, message, status, request_id, retryable=False):
    return JSONResponse(status_code=status, content={
        'status': 'error', 'request_id': request_id,
        'error': {'code': code, 'message': message, 'retryable': retryable}})
