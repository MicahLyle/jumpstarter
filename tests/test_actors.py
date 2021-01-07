import anyio
import pytest
from mock import AsyncMock

from jumpstarter.actors import Actor
from jumpstarter.resources import NotAResourceError, resource
from jumpstarter.states import ActorState


@pytest.mark.anyio
async def test_acquire_resource(subtests):
    resource_mock = AsyncMock()

    class FakeActor(Actor):
        @resource
        def resource(self):
            return resource_mock

    fake_actor = FakeActor()

    assert fake_actor.state == ActorState.initializing

    async with anyio.create_task_group() as tg:
        await fake_actor.start(tg)

    assert fake_actor.state == ActorState.started

    with subtests.test("__aenter__ is called"):
        resource_mock.__aenter__.assert_called_once_with(resource_mock)
        resource_mock.__aexit__.assert_not_called()

    assert fake_actor.state != ActorState.stopped
    await fake_actor.stop()

    with subtests.test("__aexit__ is called"):
        resource_mock.__aexit__.assert_called_once_with(resource_mock, None, None, None)


@pytest.mark.anyio
async def test_acquire_resource_within_specified_timeout(subtests):
    resource_mock = AsyncMock()

    class FakeActor(Actor):
        @resource(timeout=1)
        def resource(self):
            return resource_mock

    fake_actor = FakeActor()

    assert fake_actor.state == ActorState.initializing

    async with anyio.create_task_group() as tg:
        await fake_actor.start(tg)

    assert fake_actor.state == ActorState.started

    with subtests.test("__aenter__ is called"):
        resource_mock.__aenter__.assert_called_once_with(resource_mock)
        resource_mock.__aexit__.assert_not_called()

    assert fake_actor.state != ActorState.stopped
    await fake_actor.stop()

    with subtests.test("__aexit__ is called"):
        resource_mock.__aexit__.assert_called_once_with(resource_mock, None, None, None)


@pytest.mark.anyio
async def test_acquire_resource_timed_out(subtests):
    async def cause_timeout(*_, **__):
        await anyio.sleep(5)

    resource_mock = AsyncMock()
    resource_mock.__aenter__.side_effect = cause_timeout

    class FakeActor(Actor):
        @resource(timeout=0.01)
        def resource(self):
            return resource_mock

    fake_actor = FakeActor()

    with pytest.raises(TimeoutError):
        async with anyio.create_task_group() as tg:
            await fake_actor.start(tg)


@pytest.mark.anyio
async def test_acquire_resource_not_a_resource(subtests):
    class FakeActorWithAFaultyResource(Actor):
        @resource
        def not_a_resource(self):
            return object()

    a = FakeActorWithAFaultyResource()

    with pytest.raises(
        NotAResourceError,
        match=r"The return value of not_a_resource is not a context manager\.\n"
        r"Instead we got <object object at 0x[0-9a-f]+>\.",
    ):
        await a.start()