class APIError(Exception):
    status_code = 500
    default_message = "A backend error occurred."

    def __init__(self, message: str = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class BadRequest(APIError):
    status_code = 400
    default_message = "Bad request."


class Unauthorized(APIError):
    status_code = 401
    default_message = "Authentication required."


class Forbidden(APIError):
    status_code = 403
    default_message = "You do not have permission to perform this action."


class NotFound(APIError):
    status_code = 404
    default_message = "Resource not found."


class Conflict(APIError):
    status_code = 409
    default_message = "Conflict detected."


class UnprocessableEntity(APIError):
    status_code = 422
    default_message = "Unprocessable entity."


class TooManyRequests(APIError):
    status_code = 429
    default_message = "Too many requests."