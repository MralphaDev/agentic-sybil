"""Investigation Copilot package with lazy compatibility exports."""


def __getattr__(name: str):
    # Keep the historical import working without eagerly importing service/database modules.
    if name == "router":
        from app.agent.copilot.routes import router
        return router
    if name == "CopilotRequest":
        from app.agent.copilot.models import CopilotRequest
        return CopilotRequest
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router", "CopilotRequest"]
