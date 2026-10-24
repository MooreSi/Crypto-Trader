"""The composition root: wires config, database, runtime and web server.

The only module allowed to import across every layer (enforced by the
import-contract gate). Importing it must have no side effects beyond
building the FastAPI object -- the boot smoke test imports it.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from backend.src import config, runtime
from backend.src.api.server import create_app
from backend.src.db import database
from backend.src.services.engines import registry

log = logging.getLogger(__name__)


def open_storage() -> None:
    network = config.pin_network()
    database.init(config.main_db_path())
    log.info("[App] data in %s, network %s", config.USER_DATA_DIR, network)


@asynccontextmanager
async def lifespan(_app):
    open_storage()
    rt = runtime.get()
    rt.start()
    try:
        yield
    finally:
        await rt.stop()
        registry.close()
        database.close()


app = create_app(lifespan=lifespan)
