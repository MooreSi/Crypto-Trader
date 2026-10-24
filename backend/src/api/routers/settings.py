from fastapi import APIRouter

from backend.src.api.schemas import AccountAddress, AdminConsole, AgentKey, Network
from backend.src.controllers import settings_controller

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get() -> dict:
    return settings_controller.get()


@router.post("/network")
def network(body: Network) -> dict:
    return settings_controller.set_network(body.network)


@router.post("/account")
def account(body: AccountAddress) -> dict:
    return settings_controller.set_account_address(body.address)


@router.post("/agent-key")
def agent_key(body: AgentKey) -> dict:
    return settings_controller.set_agent_key(body.network, body.key)


@router.delete("/agent-key/{network}")
def clear_agent_key(network: str) -> dict:
    return settings_controller.clear_agent_key(network)


@router.post("/admin-console")
def admin_console(body: AdminConsole) -> dict:
    return settings_controller.set_admin_console(body.enabled, body.nickname or "")
