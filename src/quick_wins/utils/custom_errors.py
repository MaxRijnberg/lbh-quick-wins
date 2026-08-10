class RunningError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class UnknownError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class QueryWarning(Warning):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class OverlyGenericSchemaWarning(Warning):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class HasNaNWarning(Warning):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
