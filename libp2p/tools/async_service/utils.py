import functools
import inspect
from typing import Any, Callable, Coroutine, TypeVar, cast

import async_service
import trio

# Reference: https://github.com/ethereum/async-service/blob/e067b16783e20983491a63fa98cdd4f5f11ec40e/async_service/asyncio.py#L309  # noqa: E501

# TSyncFunc = TypeVar("TSyncFunc", )

TFunc = TypeVar("TFunc", bound=Callable[..., Coroutine[Any, Any, Any]])


def _validate_service_running(func: TFunc, service: async_service.ServiceAPI) -> None:
    if not hasattr(service, "manager"):
        raise async_service.ServiceCancelled(
            f"Cannot access external API {func}.  Service has not been run."
        )
    manager = service.manager

    if not service.manager.is_running:
        raise async_service.ServiceCancelled(
            f"Cannot access external API {func}.  Service is not running: "
            f"started={manager.is_started}  running={manager.is_running} "
            f"stopping={manager.is_stopping}  finished={manager.is_finished}"
        )


def _wrap_async_func(func: TFunc) -> TFunc:
    @functools.wraps(func)
    async def inner(self: async_service.ServiceAPI, *args: Any, **kwargs: Any) -> Any:
        _validate_service_running(func, self)
        manager = self.manager

        res_func = None
        is_func_finished = False
        is_service_stopping = False

        async def func_with_event(nursery: trio.Nursery) -> None:
            nonlocal res_func, is_func_finished
            res_func = await func(self, *args, **kwargs)
            is_func_finished = True
            nursery.cancel_scope.cancel()

        async def service_stopping_with_event(nursery: trio.Nursery) -> None:
            nonlocal is_service_stopping
            await manager.wait_stopping()
            is_service_stopping = True
            nursery.cancel_scope.cancel()

        async with trio.open_nursery() as nursery:
            nursery.start_soon(func_with_event, nursery)
            nursery.start_soon(service_stopping_with_event, nursery)

        if is_func_finished:
            return res_func
        elif is_service_stopping:
            raise async_service.ServiceCancelled(
                f"Cannot access external API {func}.  Service is not running: "
                f"started={manager.is_started}  running={manager.is_running} "
                f"stopping={manager.is_stopping}  finished={manager.is_finished}"
            )
        else:
            raise Exception("Code path should be unreachable")

    return cast(TFunc, inner)


def _wrap_sync_func(func: TFunc) -> TFunc:
    @functools.wraps(func)
    def inner(self: async_service.ServiceAPI, *args: Any, **kwargs: Any) -> Any:
        _validate_service_running(func, self)
        return func(self, *args, **kwargs)

    return cast(TFunc, inner)


def external_api(func: TFunc) -> TFunc:
    """Trio's version of `async_service.external_api`, except that it supports sync function as well."""
    if inspect.iscoroutinefunction(func):
        return _wrap_async_func(func)
    else:
        return _wrap_sync_func(func)
