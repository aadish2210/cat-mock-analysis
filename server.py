from __future__ import annotations

import html
import os
import re
from pathlib import Path
from typing import Any, Callable

import requests
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS

from app_config import AppConfig
from auth import AuthError, SupabaseAuthVerifier, UserIdentity, bearer_token
from importer import import_mock
from reporting import (
    build_coach_report,
    build_divergence,
    build_mock_audit,
    build_section_report,
    build_simulation,
    build_summary,
    flatten_questions,
    ordered_mocks,
)
from storage import MockStore, ReviewStore
from supabase_storage import (
    SupabaseMockStore,
    SupabaseProfileStore,
    SupabaseRestClient,
    SupabaseReviewStore,
    SupabaseStorageError,
)


ROOT = Path(__file__).resolve().parent
DIST = ROOT / "frontend" / "dist"


def create_app(
    store: MockStore | None = None,
    importer: Callable[..., dict[str, Any]] = import_mock,
    review_store: ReviewStore | None = None,
    config: AppConfig | None = None,
    auth_verifier: SupabaseAuthVerifier | None = None,
) -> Flask:
    settings = config or AppConfig.from_env()
    app = Flask(__name__, static_folder=None)
    CORS(
        app,
        resources={r"/api/*": {"origins": list(settings.allowed_origins)}},
    )
    local_mock_store = store or MockStore()
    local_review_store = review_store or ReviewStore()
    verifier = auth_verifier
    if settings.cloud_enabled and verifier is None:
        verifier = SupabaseAuthVerifier(settings.supabase_url or "", settings.supabase_key or "")

    @app.before_request
    def establish_request_context():
        if not request.path.startswith("/api/") or request.method == "OPTIONS":
            return None
        if request.path in {"/api/config", "/api/health"}:
            return None
        if settings.cloud_enabled:
            token = bearer_token(request.headers.get("Authorization"))
            identity = verifier.verify(token) if verifier else None
            if identity is None:
                raise AuthError("Unable to verify this session.")
            client = SupabaseRestClient(
                settings.supabase_url or "",
                settings.supabase_key or "",
                token,
            )
            g.current_user = identity
            g.mock_store = SupabaseMockStore(client, identity.id)
            g.review_store = SupabaseReviewStore(client, identity.id)
            g.profile_store = SupabaseProfileStore(client, identity.id)
        else:
            g.current_user = UserIdentity(
                id="local-user",
                email="local@device",
                metadata={"full_name": "Local candidate"},
            )
            g.mock_store = local_mock_store
            g.review_store = local_review_store
            g.profile_store = None
        return None

    @app.errorhandler(AuthError)
    def handle_auth_error(error: AuthError):
        return jsonify({"error": str(error), "code": "AUTH_REQUIRED"}), error.status_code

    @app.errorhandler(SupabaseStorageError)
    def handle_storage_error(error: SupabaseStorageError):
        return jsonify({"error": str(error), "code": "CLOUD_STORAGE_ERROR"}), error.status_code

    @app.after_request
    def add_security_headers(response):
        connect_sources = "'self'"
        if settings.supabase_url:
            connect_sources += f" {settings.supabase_url}"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            f"connect-src {connect_sources}; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/config")
    def public_config():
        response = jsonify(settings.public_payload())
        response.headers["Cache-Control"] = "no-store"
        return response

    def find_question(slug: str, question_id: str) -> dict[str, Any] | None:
        mock = g.mock_store.get(slug)
        if not mock:
            return None
        return next(
            (
                item
                for item in flatten_questions(mock)
                if str(item.get("id")) == question_id
            ),
            None,
        )

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "storage": settings.storage_mode})

    @app.get("/api/auth/me")
    def current_user():
        identity: UserIdentity = g.current_user
        profile = g.profile_store.get() if g.profile_store else None
        return jsonify(
            {
                **identity.public_payload(),
                "display_name": (profile or {}).get("display_name") or identity.display_name,
                "profile": profile,
                "storage": settings.storage_mode,
            }
        )

    @app.patch("/api/profile")
    def update_profile():
        if not g.profile_store:
            return jsonify({"error": "Profiles are available in Supabase mode."}), 400
        payload = request.get_json(silent=True) or {}
        try:
            profile = g.profile_store.update(
                str(payload.get("display_name") or ""),
                str(payload.get("timezone") or "Asia/Kolkata"),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(profile)

    @app.get("/api/summary")
    def summary():
        return jsonify(build_summary(g.mock_store.all()))

    @app.get("/api/coach")
    def coach():
        return jsonify(build_coach_report(g.mock_store.all()))

    @app.get("/api/mocks")
    def mocks():
        return jsonify(
            [
                {
                    "slug": mock.get("slug"),
                    "title": mock.get("title"),
                    "attempted_at": mock.get("attempted_at"),
                    "imported_at": mock.get("imported_at"),
                }
                for mock in ordered_mocks(g.mock_store.all())
            ]
        )

    @app.get("/api/mocks/<slug>")
    def mock_audit(slug: str):
        mock = g.mock_store.get(slug)
        if not mock:
            return jsonify({"error": "Mock not found."}), 404
        return jsonify(build_mock_audit(mock))

    @app.get("/api/mocks/<slug>/questions/<question_id>")
    def mock_question(slug: str, question_id: str):
        question = find_question(slug, question_id)
        if not question:
            return jsonify({"error": "Question not found."}), 404
        return jsonify(question)

    @app.get("/api/reviews")
    def reviews():
        review_items = g.review_store.all()
        due_keys = {item["key"] for item in g.review_store.due()}
        enriched = []
        for review in review_items:
            question = find_question(review["mock_slug"], review["question_id"])
            enriched.append(
                {
                    **review,
                    "is_due": review["key"] in due_keys,
                    "question": {
                        key: question.get(key)
                        for key in (
                            "number",
                            "mock_title",
                            "section_slug",
                            "section_title",
                            "topic",
                            "difficulty",
                        )
                    }
                    if question
                    else None,
                }
            )
        counts = {
            status: sum(1 for item in review_items if item.get("status") == status)
            for status in g.review_store.INTERVALS
        }
        return jsonify(
            {
                "count": len(enriched),
                "due_count": len(due_keys),
                "counts": counts,
                "reviews": sorted(
                    enriched,
                    key=lambda item: (not item["is_due"], item["next_review_at"]),
                ),
            }
        )

    @app.get("/api/reviews/<slug>/<question_id>")
    def question_review(slug: str, question_id: str):
        return jsonify(g.review_store.get(slug, question_id) or {})

    @app.put("/api/reviews/<slug>/<question_id>")
    def update_question_review(slug: str, question_id: str):
        if not find_question(slug, question_id):
            return jsonify({"error": "Question not found."}), 404
        payload = request.get_json(silent=True) or {}
        try:
            review = g.review_store.update(
                slug,
                question_id,
                status=str(payload.get("status") or ""),
                note=str(payload.get("note") or ""),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(review)

    @app.post("/api/mocks/import")
    def import_endpoint():
        payload = request.get_json(silent=True) or {}
        url = str(payload.get("url") or "").strip()
        if not url:
            return jsonify({"error": "An IMS View Solutions URL is required."}), 400
        try:
            mock = importer(url, store=g.mock_store)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except requests.RequestException as error:
            status = error.response.status_code if error.response is not None else None
            if status in {401, 403}:
                message = "IMS rejected this link. Open View Solutions again and copy a fresh URL."
            else:
                message = "IMS could not be reached. Check your network and try again."
            return jsonify({"error": message}), 502
        question_count = sum(len(section.get("questions", [])) for section in mock.get("sections", []))
        return jsonify(
            {"slug": mock.get("slug"), "title": mock.get("title"), "question_count": question_count}
        ), 201

    @app.get("/api/toppers/divergence")
    def divergence():
        return jsonify(build_divergence(g.mock_store.all()))

    @app.post("/api/simulator/run")
    def simulator():
        payload = request.get_json(silent=True) or {}
        try:
            result = build_simulation(
                g.mock_store.all(),
                mock_slug=payload.get("mock_slug"),
                time_cap_seconds=int(payload.get("time_cap_seconds", 180)),
                topic_blacklists=[str(topic) for topic in payload.get("topic_blacklists", [])],
                type_c_immunity=bool(payload.get("type_c_immunity", True)),
                type_a_conversion_rate=float(payload.get("type_a_conversion_rate", 0.5)),
            )
        except (TypeError, ValueError) as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(result)

    @app.get("/api/sections/<section_slug>")
    def section_report(section_slug: str):
        if section_slug not in {"varc", "dilr", "qa"}:
            return jsonify({"error": "Section must be varc, dilr, or qa."}), 404
        return jsonify(build_section_report(g.mock_store.all(), section_slug))

    @app.get("/api/questions")
    def question_bank():
        section_slug = request.args.get("section")
        difficulty = request.args.get("difficulty")
        include_content = request.args.get("include_content") == "1"
        questions = [
            question for mock in g.mock_store.all() for question in flatten_questions(mock)
        ]
        if section_slug:
            questions = [
                question for question in questions if question.get("section_slug") == section_slug
            ]
        if difficulty:
            questions = [
                question for question in questions if question.get("difficulty") == difficulty.upper()
            ]
        if not include_content:
            questions = [
                {
                    key: question.get(key)
                    for key in (
                        "id",
                        "number",
                        "mock_slug",
                        "mock_title",
                        "section_slug",
                        "section_title",
                        "topic",
                        "sub_topic",
                        "difficulty",
                        "question_type",
                        "is_attempted",
                        "is_correct",
                        "score",
                        "time_taken",
                        "p_value",
                        "topper_p_value",
                    )
                }
                | {
                    "preview": html.unescape(
                        re.sub(r"<[^>]+>", " ", str(question.get("question_html") or ""))
                    ).strip()[:220]
                }
                for question in questions
            ]
        return jsonify(questions)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend(path: str):
        requested = DIST / path
        if path and requested.is_file():
            return send_from_directory(DIST, path)
        if (DIST / "index.html").is_file():
            return send_from_directory(DIST, "index.html")
        return jsonify({"error": "Frontend is not built. Run npm run build in frontend."}), 503

    return app


app = create_app()


if __name__ == "__main__":
    runtime_config = AppConfig.from_env()
    host = os.getenv("HOST") or ("0.0.0.0" if runtime_config.cloud_enabled else "127.0.0.1")
    app.run(host=host, port=int(os.getenv("PORT", "5000")), debug=False)