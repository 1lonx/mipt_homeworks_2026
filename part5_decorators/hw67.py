import functools
import json
from datetime import UTC, datetime, timedelta
from typing import Any, ParamSpec, Protocol, TypeVar, cast
from urllib.request import urlopen

INVALID_CRITICAL_COUNT = "Breaker count must be positive integer!"
INVALID_RECOVERY_TIME = "Breaker recovery time must be positive integer!"
VALIDATIONS_FAILED = "Invalid decorator args."
TOO_MUCH = "Too much requests, just wait."

P = ParamSpec("P")
R_co = TypeVar("R_co", covariant=True)


class CallableWithMeta(Protocol[P, R_co]):
    __name__: str
    __module__: str

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...


class BreakerError(Exception):
    def __init__(self, func_name: str, block_time: datetime):
        self.func_name = func_name
        self.block_time = block_time
        super().__init__(TOO_MUCH)


class _State:
    __slots__ = ("block_start", "block_until", "fails")

    def __init__(self) -> None:
        self.fails = 0
        self.block_start: datetime | None = None
        self.block_until: datetime | None = None


class CircuitBreaker:
    def __init__(
        self,
        critical_count: int = 5,
        time_to_recover: int = 30,
        triggers_on: type[Exception] = Exception,
    ):
        errors = []
        if not isinstance(critical_count, int) or isinstance(critical_count, bool) or critical_count <= 0:
            errors.append(ValueError(INVALID_CRITICAL_COUNT))
        if not isinstance(time_to_recover, int) or isinstance(time_to_recover, bool) or time_to_recover <= 0:
            errors.append(ValueError(INVALID_RECOVERY_TIME))
        if errors:
            raise ExceptionGroup(VALIDATIONS_FAILED, errors)
        self.cnt = critical_count
        self.rec = time_to_recover
        self.trig = triggers_on

    def __call__(self, func: CallableWithMeta[P, R_co]) -> CallableWithMeta[P, R_co]:
        func_name = f"{func.__module__}.{func.__name__}"
        state = _State()

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R_co:
            self._check_blocked(state, func_name)
            try:
                res = func(*args, **kwargs)
            except self.trig as e:
                self._handle_error(state, func_name, e)
            else:
                self._reset(state)
                return res
            unreachable_msg = "unreachable"
            raise RuntimeError(unreachable_msg)

        return wrapper

    def _check_blocked(self, state: _State, func_name: str) -> None:
        if state.block_until is not None and datetime.now(UTC) < state.block_until:
            raise BreakerError(func_name, cast("datetime", state.block_start))

    def _handle_error(self, state: _State, func_name: str, e: Exception) -> None:
        state.fails += 1
        if state.fails < self.cnt:
            raise e
        state.block_start = datetime.now(UTC)
        state.block_until = state.block_start + timedelta(seconds=self.rec)
        raise BreakerError(func_name, state.block_start) from e

    def _reset(self, state: _State) -> None:
        state.fails = 0
        state.block_start = None
        state.block_until = None


circuit_breaker = CircuitBreaker(5, 30, Exception)


# @circuit_breaker
def get_comments(post_id: int) -> Any:
    """
    Получает комментарии к посту

    Args:
        post_id (int): Идентификатор поста

    Returns:
        list[dict[int | str]]: Список комментариев
    """
    response = urlopen(f"https://jsonplaceholder.typicode.com/comments?postId={post_id}")
    return json.loads(response.read())


if __name__ == "__main__":
    comments = get_comments(1)
