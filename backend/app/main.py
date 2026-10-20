from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.responses import problem_responses
from app.api.routes import auth, health, incidents
from app.core.config import Settings, get_settings, warn_if_insecure
from app.core.errors import register_error_handlers
from app.core.openapi import use_problem_json_in_openapi


def create_app(settings: Settings) -> FastAPI:
    warn_if_insecure(settings)
    app = FastAPI(title=settings.app_name, debug=settings.debug, responses=problem_responses(500))
    # Auth travels in the Authorization header (no cookies), so credentials are not
    # needed; origins are always explicit (Settings rejects "*").
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Location", "Retry-After"],
        max_age=600,
    )
    register_error_handlers(app)
    use_problem_json_in_openapi(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(incidents.router)
    return app


# Fails fast here (e.g. APP_ENV=production without a strong JWT_SECRET).
app = create_app(get_settings())
