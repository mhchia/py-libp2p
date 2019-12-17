from async_service import Service, ServiceCancelled, background_trio_service
import pytest
import trio

from libp2p.tools.async_service.utils import external_api

# Copied and modified from `ethereum/async-service` repo
# Ref: https://github.com/ethereum/async-service/blob/e067b16783e20983491a63fa98cdd4f5f11ec40e/tests-asyncio/test_asyncio_external_api.py  # noqa: E501


class ExternalAPIService(Service):
    async def run(self):
        await self.manager.wait_finished()

    @external_api
    async def get_7(self, wait_return=None, signal_event=None):
        if signal_event is not None:
            signal_event.set()
        if wait_return is not None:
            await wait_return.wait()
        return 7


@pytest.mark.trio
async def test_asyncio_service_external_api_fails_before_start():
    service = ExternalAPIService()

    # should raise if the service has not yet been started.
    with pytest.raises(ServiceCancelled):
        await service.get_7()


@pytest.mark.trio
async def test_asyncio_service_external_api_works_while_running():
    service = ExternalAPIService()

    async with background_trio_service(service):
        assert await service.get_7() == 7


@pytest.mark.trio
async def test_asyncio_service_external_api_race_condition_done_and_cancelled():
    service = ExternalAPIService()

    async with background_trio_service(service) as manager:
        event_func_finished = trio.Event()
        result = None

        async def run_service_get_7():
            nonlocal result
            result = await service.get_7()
            event_func_finished.set()

        async with trio.open_nursery() as nursery:
            nursery.start_soon(run_service_get_7)

            # First, wait until the event finishes. After this, we are sure `service.get_7`
            # has finished.
            await event_func_finished.wait()
            # Second, cancel the service.
            await manager.stop()
            # Just a double check that we have got the result
            assert result == 7

        # We should be able to reach here without any exception even though the service is
        # cancelled by `service.stop` because `service.get_7` has finished.


@pytest.mark.trio
async def test_asyncio_service_external_api_raises_when_cancelled():
    service = ExternalAPIService()

    async with background_trio_service(service) as manager:
        with pytest.raises(ServiceCancelled):
            async with trio.open_nursery() as nursery:
                # an event to ensure that we are indeed within the body of the
                is_within_fn = trio.Event()
                trigger_return = trio.Event()

                nursery.start_soon(service.get_7, trigger_return, is_within_fn)

                # ensure we're within the body of the task.
                await is_within_fn.wait()

                # now cancel the service and trigger the return of the function.
                manager.cancel()


@pytest.mark.trio
async def test_asyncio_service_external_api_raises_when_finished():
    service = ExternalAPIService()

    async with background_trio_service(service) as manager:
        pass

    assert manager.is_finished
    # A direct call should also fail.  This *should* be hitting the early
    # return mechanism.
    with pytest.raises(ServiceCancelled):
        assert await service.get_7()
