from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.responses import problem_responses
from app.api.routes import auth, chaos, config, demo, health, incidents
from app.core.chaos import ChaosController, ChaosMiddleware
from app.core.config import Settings, get_settings, warn_if_insecure
from app.core.errors import register_error_handlers
from app.core.observability import RequestContextMiddleware, configure_logging
from app.core.openapi import use_problem_json_in_openapi


def create_app(settings: Settings) -> FastAPI:
    configure_logging()
    warn_if_insecure(settings)
    app = FastAPI(title=settings.app_name, debug=settings.debug, responses=problem_responses(500))
    if settings.chaos_enabled:
        # Innermost of the three, so simulated 503s still get CORS and X-Request-ID.
        app.state.chaos = ChaosController()
        app.add_middleware(ChaosMiddleware, controller=app.state.chaos)
    # Auth travels in the Authorization header (no cookies), so credentials are not
    # needed; origins are always explicit (Settings rejects "*").
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Location", "Retry-After", "X-Request-ID"],
        max_age=600,
    )
    # Added last, so it wraps everything: every response (even 500) gets X-Request-ID.
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    use_problem_json_in_openapi(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(config.router)
    app.include_router(incidents.router)
    if settings.chaos_enabled:
        app.include_router(chaos.router)
    if settings.demo_mode:
        app.include_router(demo.router)
    return app


# Fails fast here (e.g. APP_ENV=production without a strong JWT_SECRET).
app = create_app(get_settings())
