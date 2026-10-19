"""Account routes: /account/... (the real portfolio)"""
from fastapi import APIRouter

from app.controllers.account import AccountController
from app.core.dependencies import RequiredAccountServiceDep
from app.schemas.account import PositioningRequest
from app.schemas.workspace import ViewResponse

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/holdings", response_model=ViewResponse)
async def holdings(account_service: RequiredAccountServiceDep, use_cache: bool = True) -> ViewResponse:
    """Value and weight of each held asset"""
    return await AccountController(account_service).holdings(use_cache)


@router.post("/positioning", response_model=ViewResponse)
async def positioning(request: PositioningRequest, account_service: RequiredAccountServiceDep,
                      use_cache: bool = True) -> ViewResponse:
    """Current holdings vs the model allocation"""
    return await AccountController(account_service).positioning(request, use_cache)


@router.get("/pnl", response_model=ViewResponse)
async def pnl(account_service: RequiredAccountServiceDep, use_cache: bool = True) -> ViewResponse:
    """Average cost, book cost, realized / unrealized P&L per held asset and the trade history"""
    return await AccountController(account_service).pnl(use_cache)


@router.post("/upload", response_model=ViewResponse)
async def upload(account_service: RequiredAccountServiceDep) -> ViewResponse:
    """Push Positions, Quantities and the trade history to the GitHub repository"""
    return await AccountController(account_service).upload()
