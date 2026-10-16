import asyncio
from types import SimpleNamespace

import pytest

from src.config.config import Profile
from src.modules.service import AnswerService, AnswerSignals


class FakeStream:
    def __init__(self, pieces):
        self.pieces = iter(pieces)
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            delay, content = next(self.pieces)
        except StopIteration:
            raise StopAsyncIteration from None
        await asyncio.sleep(delay)
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])

    async def close(self):
        self.closed = True


def service_for(stream):
    signals = AnswerSignals()
    results = {"deltas": [], "errors": [], "done": []}
    signals.delta.connect(results["deltas"].append)
    signals.error.connect(results["errors"].append)
    signals.done.connect(results["done"].append)

    async def create(**_kwargs):
        return stream

    service = AnswerService(signals)
    service._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    service.FIRST_TOKEN_TIMEOUT = 0.03
    service.STREAM_IDLE_TIMEOUT = 0.03
    service.TOTAL_TIMEOUT = 1
    return service, results


@pytest.mark.asyncio
async def test_no_first_token_exits_generating_state():
    stream = FakeStream([(0.2, "太迟了")])
    service, results = service_for(stream)
    service.answer("问题", Profile())
    await service._task

    assert results["errors"] and "等待首字" in results["errors"][0]
    assert not results["done"]
    assert stream.closed


@pytest.mark.asyncio
async def test_stream_pause_preserves_partial_answer():
    stream = FakeStream([(0, "已有回答"), (0.2, "太迟了")])
    service, results = service_for(stream)
    service.answer("问题", Profile())
    await service._task

    assert results["deltas"] == ["已有回答"]
    assert results["errors"] and "输出中断" in results["errors"][0]
    assert stream.closed


@pytest.mark.asyncio
async def test_canceled_request_cannot_update_new_answer():
    first = FakeStream([(0.2, "旧回答")])
    service, results = service_for(first)
    service.answer("旧问题", Profile())
    old_task = service._task
    await asyncio.sleep(0)

    second = FakeStream([(0, "新回答")])

    async def create(**_kwargs):
        return second

    service._client.chat.completions.create = create
    service.answer("新问题", Profile())
    await service._task
    with pytest.raises(asyncio.CancelledError):
        await old_task

    assert results["done"] == ["新回答"]
    assert results["deltas"] == ["新回答"]
    assert not results["errors"]
