import pytest
from embedder.base import EmbedderBase


def test_embedder_base_is_abstract():
    with pytest.raises(TypeError):
        EmbedderBase()


def test_concrete_embedder_must_implement_embed():
    class Incomplete(EmbedderBase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_concrete_embedder_works_when_embed_implemented():
    class Stub(EmbedderBase):
        def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
            return [[0.1] * 3 for _ in texts]

    stub = Stub()
    result = stub.embed(["hello"])
    assert len(result) == 1
    assert len(result[0]) == 3
