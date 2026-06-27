from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from e2b import Sandbox
from langchain_e2b import E2BSandbox

from src.config import Settings


@contextmanager
def managed_sandbox(settings: Settings) -> Iterator[E2BSandbox]:
    e2b_sandbox = Sandbox.create(timeout=settings.sandbox_timeout)
    backend = E2BSandbox(sandbox=e2b_sandbox)
    try:
        yield backend
    finally:
        e2b_sandbox.kill()
