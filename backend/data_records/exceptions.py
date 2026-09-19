class RecordError(Exception):
    pass


class RecordValidationError(RecordError):
    pass


class RecordNotFoundError(RecordError):
    pass


class RecordConflictError(RecordError):
    pass


class UnsupportedRecordOperation(RecordError):
    pass
