"""Flask web server for Truth Mirror."""

from __future__ import annotations

import concurrent.futures
from dataclasses import asdict
from http import HTTPStatus
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse
import uuid

from dotenv import load_dotenv
from flask import Flask, Response, g, jsonify, request, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from truth_mirror.auth_service import (
    authenticate_user,
    generate_code,
    login_user,
    register_user,
    seed_test_user,
    verify_email_code,
)
from truth_mirror.db import (
    get_db,
    get_user_by_email,
    store_verification_code,
)
from truth_mirror.geo_orchestrator import GeopoliticalPipeline
from truth_mirror.models import GeopoliticalResult
from truth_mirror.pipeline_status import clear_status, get_status, set_result, set_stage

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

AUTH_DB_PATH = os.environ.get("AUTH_DB_PATH", "truth_mirror.db")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "")
MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5MB
SESSION_TTL = 24 * 3600  # 24 hours

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

_active_sessions: Dict[str, tuple[str, float]] = {}
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"
LANDING_FILE = STATIC_DIR / "landing.html"


def send_verification_email(email: str, code: str) -> bool:
    """Send verification email with 6-digit code via Resend."""
    if not RESEND_API_KEY:
        logger.info(f"RESEND_API_KEY not configured. Verification code for {email}: {code}")
        return True
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        params = {
            "from": RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "Your Truth Mirror Verification Code",
            "html": (
                f"<div style='font-family: sans-serif; padding: 20px;'>"
                f"<h2>Truth Mirror Verification</h2>"
                f"<p>Your verification code is: <b style='font-size: 24px; letter-spacing: 2px;'>{code}</b></p>"
                f"<p>This code will expire in 15 minutes.</p>"
                f"</div>"
            ),
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


def _create_session(user_id_or_email: str) -> str:
    token = str(uuid.uuid4())
    _active_sessions[token] = (user_id_or_email, time.time())
    return token


def _get_authenticated_user_from_token(auth_header: Optional[str]) -> Optional[str]:
    now = time.time()
    expired = [t for t, v in _active_sessions.items() if now - v[1] > SESSION_TTL]
    for t in expired:
        del _active_sessions[t]

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token in _active_sessions:
            user_id_or_email, _ = _active_sessions[token]
            _active_sessions[token] = (user_id_or_email, now)
            return user_id_or_email
    return None


def _check_session(handler=None) -> bool:
    """Session check helper supporting both Flask requests and legacy HTTP handler mocks."""
    if handler is not None:
        auth_header = handler.headers.get("Authorization") if hasattr(handler, "headers") and handler.headers else None
        user = _get_authenticated_user_from_token(auth_header)
        if user:
            return True
        if hasattr(handler, "send_response"):
            handler.send_response(401)
            if hasattr(handler, "send_header") and hasattr(handler, "end_headers") and hasattr(handler, "wfile"):
                body = json.dumps({"error": "Unauthorized"}).encode("utf-8")
                handler.send_header("Content-Type", "application/json")
                handler.send_header("Content-Length", str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
        return False

    auth_header = request.headers.get("Authorization")
    return _get_authenticated_user_from_token(auth_header) is not None


def _handle_pipeline_result(fut, request_id: str, pipeline_inst: Any) -> None:
    try:
        result = fut.result()
        if isinstance(result, GeopoliticalResult):
            res_dict = asdict(result)
            res_dict["final_verdict"] = res_dict.get("verdict")
            res_dict["request_id"] = request_id
        else:
            if result is None:
                res_dict = {}
            else:
                res_dict = pipeline_inst.to_json(result) if hasattr(pipeline_inst, "to_json") else result
            res_dict["request_id"] = request_id
        set_result(request_id, res_dict)
    except Exception as e:
        set_result(
            request_id,
            {
                "error": "Internal server error during analysis",
                "details": str(e),
                "verdict": "ERROR",
                "verdict_data": {
                    "verdict": "ERROR",
                    "confidence": 0.0,
                    "confidence_label": "N/A",
                    "one_line_verdict": "An internal error occurred during claim processing.",
                    "full_reasoning": f"Unhandled exception during claim analysis: {e}",
                    "what_is_true": "N/A — system error.",
                    "what_is_false": "N/A — system error.",
                    "what_is_unclear": "N/A — system error.",
                },
                "is_geopolitical": False,
            },
        )


def _start_verification(claim: str, request_id: str, pipeline_inst: Any) -> tuple[dict, int]:
    if not claim:
        return {"error": "Claim is required"}, 400
    set_stage("classifying", request_id=request_id)
    try:
        future = _executor.submit(pipeline_inst.verify, claim, request_id=request_id)
        future.add_done_callback(lambda fut: _handle_pipeline_result(fut, request_id, pipeline_inst))
        return {"status": "Started", "request_id": request_id}, 202
    except Exception as e:
        clear_status(request_id)
        return {"error": "Failed to start analysis", "details": str(e)}, 500


def create_app(db_path: Optional[str] = None, test_config: Optional[dict] = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["AUTH_DB_PATH"] = db_path or AUTH_DB_PATH
    app.config["CACHE_DB_PATH"] = os.environ.get("CACHE_DB_PATH", ".tm_cache.db")
    app.config["MAX_CONTENT_LENGTH"] = MAX_PAYLOAD_SIZE

    if test_config:
        app.config.update(test_config)

    # Initialize DB schema & optionally seed test users for automated testing
    has_seed_flag = os.environ.get("SEED_TEST_USERS", "").strip().lower() in ("1", "true", "yes")
    if has_seed_flag:
        should_seed = True
    elif test_config and test_config.get("TESTING") is False:
        should_seed = False
    else:
        should_seed = bool(
            app.config.get("TESTING", False)
            or ("pytest" in sys.modules)
        )
    init_conn = get_db(app.config["AUTH_DB_PATH"])
    try:
        if should_seed:
            seed_test_user(init_conn)
    finally:
        init_conn.close()

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[],
        storage_uri="memory://",
    )
    app.limiter = limiter

    pipeline = GeopoliticalPipeline()

    def get_req_db():
        if "db" not in g:
            g.db = get_db(app.config["AUTH_DB_PATH"])
        return g.db

    @app.teardown_appcontext
    def teardown_db(exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/", methods=["GET"])
    def root():
        if LANDING_FILE.exists():
            html = LANDING_FILE.read_text(encoding="utf-8")
        elif INDEX_FILE.exists():
            html = INDEX_FILE.read_text(encoding="utf-8")
        else:
            html = "<!DOCTYPE html><html><head><title>Truth Mirror</title></head><body><h1>Truth Mirror</h1><a href='/app'>Go to App</a></body></html>"
        if WHATSAPP_NUMBER:
            html = html.replace("{{WHATSAPP_NUMBER}}", WHATSAPP_NUMBER)
        return Response(html, mimetype="text/html")

    @app.route("/app", methods=["GET"])
    def app_page():
        if INDEX_FILE.exists():
            html = INDEX_FILE.read_text(encoding="utf-8")
        else:
            html = "<!DOCTYPE html><html><head><title>Truth Mirror App</title></head><body><h1>Truth Mirror App</h1></body></html>"
        if WHATSAPP_NUMBER:
            html = html.replace("{{WHATSAPP_NUMBER}}", WHATSAPP_NUMBER)
        return Response(html, mimetype="text/html")

    @app.route("/static/<path:filename>", methods=["GET"])
    def static_files(filename: str):
        return send_from_directory(STATIC_DIR, filename)

    @app.route("/api/register", methods=["POST"])
    @limiter.limit("10 per day")
    def register():
        if request.content_length and request.content_length > MAX_PAYLOAD_SIZE:
            return jsonify({"error": "Payload too large"}), 413
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip()
        password = str(data.get("password", ""))

        if not email or not password:
            return jsonify({"error": "Missing required fields", "code": "missing_fields"}), 400

        conn = get_req_db()
        res = register_user(conn, email, password)
        if not res.get("success"):
            err = res.get("error", "Registration failed")
            err_lower = err.lower()
            if "email is already registered" in err_lower:
                return jsonify({"error": err, "code": "email_taken"}), 409
            elif "invalid email" in err_lower:
                return jsonify({"error": err, "code": "invalid_email"}), 400
            elif "password" in err_lower:
                return jsonify({"error": err, "code": "invalid_password"}), 400
            else:
                return jsonify({"error": err, "code": "invalid_registration"}), 400

        code = res.get("verification_code") or res.get("code")
        send_verification_email(email, code)
        return jsonify({
            "status": "verification_sent",
            "message": "Verification code sent to your email.",
            "email": email,
        }), 201

    @app.route("/api/verify-email", methods=["POST"])
    def verify_email():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip()
        code = str(data.get("code", "")).strip()

        if not email or not code:
            return jsonify({"error": "Email and verification code are required", "code": "missing_fields"}), 400

        conn = get_req_db()
        res = verify_email_code(conn, email, code)
        if not res.get("success"):
            return jsonify({"error": res.get("error", "Invalid code"), "code": "invalid"}), 400

        user = get_user_by_email(conn, email)
        user_email = user["email"] if user else email
        token = _create_session(user_email)
        return jsonify({
            "status": "verified",
            "message": "Email verified successfully.",
            "token": token,
            "email": user_email,
        }), 200

    @app.route("/api/resend-code", methods=["POST"])
    @limiter.limit("3 per hour")
    def resend_code():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip()
        if not email:
            return jsonify({"error": "Email is required", "code": "missing_fields"}), 400

        conn = get_req_db()
        user = get_user_by_email(conn, email)
        if not user:
            return jsonify({"error": "User not found", "code": "not_found"}), 404
        if user["is_verified"]:
            return jsonify({"error": "User already verified", "code": "already_verified"}), 400

        code = generate_code()
        expires_at = time.time() + 900.0  # 15 mins
        store_verification_code(conn, email, code, expires_at)
        send_verification_email(email, code)
        return jsonify({"status": "resent", "message": "Verification code resent."}), 200

    @app.route("/api/login", methods=["POST"])
    def login():
        if request.content_length and request.content_length > MAX_PAYLOAD_SIZE:
            return jsonify({"error": "Payload too large"}), 413

        data = request.get_json(silent=True) or {}
        identifier = str(data.get("email") or data.get("username") or data.get("identifier") or "").strip()
        password = str(data.get("password") or "")

        if not identifier or not password:
            return jsonify({"error": "Invalid email or password"}), 401

        # Check DB users (including seeded test user)
        conn = get_req_db()
        res = authenticate_user(conn, identifier, password)
        if res.get("success"):
            user = res["user"]
            token = _create_session(user["email"])
            return jsonify({"token": token, "email": user["email"]}), 200

        return jsonify({"error": res.get("error", "Invalid email or password")}), 401

    @app.route("/api/validate", methods=["GET"])
    def validate_session():
        auth_header = request.headers.get("Authorization")
        user = _get_authenticated_user_from_token(auth_header)
        if user:
            return jsonify({"valid": True, "email": user}), 200
        return jsonify({"error": "Unauthorized"}), 401

    @app.route("/api/cached-claims", methods=["GET"])
    def cached_claims():
        try:
            import sqlite3, json
            conn = sqlite3.connect(app.config.get("CACHE_DB_PATH", ".tm_cache.db"), timeout=5.0)
            rows = conn.execute("SELECT data FROM result_cache ORDER BY timestamp DESC LIMIT 15").fetchall()
            claims = []
            for row in rows:
                try:
                    data = json.loads(row[0])
                    if data.get("original_claim"):
                        claims.append({"claim": data["original_claim"]})
                except Exception:
                    pass
            conn.close()
            # Deduplicate preserving order, limit to 5
            seen = set()
            unique_claims = []
            for c in claims:
                claim_lower = c["claim"].lower()
                if claim_lower not in seen:
                    seen.add(claim_lower)
                    unique_claims.append(c)
                    if len(unique_claims) >= 5:
                        break
            return jsonify({"claims": unique_claims}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/status", methods=["GET"])
    def status():
        is_guest = request.args.get("guest") in ("1", "true", "True")
        auth_header = request.headers.get("Authorization")
        user = _get_authenticated_user_from_token(auth_header)
        if not is_guest and not user:
            return jsonify({"error": "Unauthorized"}), 401

        req_id = request.args.get("request_id", "__global__")
        return jsonify(get_status(req_id)), 200

    @app.route("/api/verify", methods=["POST"])
    def verify():
        if request.content_length and request.content_length > MAX_PAYLOAD_SIZE:
            return jsonify({"error": "Payload too large"}), 413

        auth_header = request.headers.get("Authorization")
        user = _get_authenticated_user_from_token(auth_header)
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Missing body"}), 400
        claim = str(data.get("claim", "")).strip()
        request_id = data.get("request_id") or str(uuid.uuid4())

        cached_res = pipeline._check_cache(claim)
        if cached_res:
            from dataclasses import asdict
            res_dict = asdict(cached_res)
            res_dict["final_verdict"] = res_dict.get("verdict")
            return jsonify({"stage": "completed", "result": res_dict}), 200

        resp_data, status_code = _start_verification(claim, request_id, pipeline)
        return jsonify(resp_data), status_code

    @app.route("/api/guest-verify", methods=["POST"])
    def guest_verify():
        if request.content_length and request.content_length > MAX_PAYLOAD_SIZE:
            return jsonify({"error": "Payload too large"}), 413

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Missing body"}), 400
        claim = str(data.get("claim", "")).strip()
        request_id = data.get("request_id") or str(uuid.uuid4())

        cached_res = pipeline._check_cache(claim)
        if cached_res:
            from dataclasses import asdict
            res_dict = asdict(cached_res)
            res_dict["final_verdict"] = res_dict.get("verdict")
            return jsonify({"stage": "completed", "result": res_dict}), 200

        resp_data, status_code = _start_verification(claim, request_id, pipeline)
        return jsonify(resp_data), status_code

    return app


class TruthMirrorHandler:
    """Compatibility shim for tests expecting the legacy HTTP handler."""
    pipeline = GeopoliticalPipeline()

    def send_response(self, code: int, message: Optional[str] = None) -> None:
        pass

    def send_header(self, keyword: str, value: str) -> None:
        pass

    def end_headers(self) -> None:
        pass

    def _write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        if hasattr(self, "send_response"):
            self.send_response(status)
        if hasattr(self, "send_header"):
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
        if hasattr(self, "end_headers"):
            self.end_headers()
        if hasattr(self, "wfile") and hasattr(self.wfile, "write"):
            self.wfile.write(body)

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        if parsed_path.path in {"/", "/index.html"}:
            html = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""
            if WHATSAPP_NUMBER:
                html = html.replace("{{WHATSAPP_NUMBER}}", WHATSAPP_NUMBER)
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed_path.path == "/api/status":
            if not _check_session(self):
                return
            query = parse_qs(parsed_path.query)
            req_id = query.get("request_id", ["__global__"])[0]
            self._write_json(get_status(req_id), status=200)
            return

        self._write_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        length = int(getattr(self, "headers", {}).get("Content-Length", 0)) if hasattr(self, "headers") else 0
        if length > MAX_PAYLOAD_SIZE:
            self._write_json({"error": "Payload too large"}, status=413)
            return

        if self.path == "/api/login":
            raw = self.rfile.read(length) if hasattr(self, "rfile") else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._write_json({"error": "Invalid JSON"}, status=400)
                return
            identifier = str(payload.get("email") or payload.get("username") or payload.get("identifier") or "").strip()
            password = str(payload.get("password", ""))
            if not identifier or not password:
                self._write_json({"error": "Invalid email or password"}, status=401)
                return
            conn = get_db(AUTH_DB_PATH)
            try:
                res = authenticate_user(conn, identifier, password)
                if res.get("success"):
                    token = _create_session(res["user"]["email"])
                    self._write_json({"token": token, "email": res["user"]["email"]})
                    return
            finally:
                conn.close()
            self._write_json({"error": res.get("error", "Invalid email or password")}, status=401)
            return

        if self.path == "/api/verify":
            if not _check_session(self):
                return
            raw = self.rfile.read(length) if hasattr(self, "rfile") else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._write_json({"error": "Invalid JSON"}, status=400)
                return
            claim = str(payload.get("claim", "")).strip()
            request_id = payload.get("request_id", str(uuid.uuid4()))
            res_dict, status_code = _start_verification(claim, request_id, getattr(self, "pipeline", TruthMirrorHandler.pipeline))
            self._write_json(res_dict, status=status_code)
            return

        self._write_json({"error": "Not found"}, status=404)


app = create_app()


def run_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    logger.info(f"Truth Mirror running on http://127.0.0.1:{port} (bound to {host})")
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    run_server()
