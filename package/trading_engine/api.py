import datetime
import logging
import time

from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from trading_engine import engine


class TradingEngineAPI:
    def __init__(
        self,
        engine: engine.TradingEngine,
        allowed_users_passwords: list[tuple[str, str]],
        jwt_secret_key: str,
        jwt_access_token_expires: int,
        host: str = "0.0.0.0",
        port: int = 5000,
        debug: bool = False,
    ):
        self.engine = engine
        self.host = host
        self.port = port
        self.debug = debug
        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = jwt_secret_key
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(
            minutes=jwt_access_token_expires
        )
        self.jwt = JWTManager(self.app)
        self.allowed_users_passwords = allowed_users_passwords
        self.logger = logging.getLogger(__name__)  # Retrieve the logger object

        # Set log level based on debug flag
        log_level = logging.DEBUG if self.debug else logging.INFO
        self.logger.setLevel(log_level)

        @self.app.route("/login", methods=["POST"])
        def login():
            # Parse username and password from request
            data = request.json
            username = data.get("username", None)  # type: ignore
            password = data.get("password", None)  # type: ignore
            if not username or not password:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Username and password are required",
                        }
                    ),
                    401,
                )
            # Check if user is allowed to login
            if (username, password) not in self.allowed_users_passwords:
                return (
                    jsonify({"status": "error", "message": "Invalid credentials"}),
                    401,
                )
            access_token = create_access_token(identity=username, fresh=True)
            refresh_token = create_refresh_token(identity=username)
            return (
                jsonify(
                    {
                        "status": "success",
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                    }
                ),
                200,
            )

        @self.app.route("/refresh", methods=["POST"])
        @jwt_required(refresh=True)
        def refresh():
            identity = get_jwt_identity()
            access_token = create_access_token(identity=identity)
            return jsonify({"status": "success", "access_token": access_token}), 200

        @self.app.route("/start", methods=["POST"])
        @jwt_required()
        def start_engine():
            self.engine.start()
            logging.info(f"Started {type(self.engine).__name__}")
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Started {type(self.engine).__name__}",
                    }
                ),
                200,
            )

        @self.app.route("/stop", methods=["POST"])
        @jwt_required()
        def stop_engine():
            self.engine.stop()
            logging.info(f"Stopped {type(self.engine).__name__}")
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Stopped {type(self.engine).__name__}",
                    }
                ),
                200,
            )

        @self.app.route("/stats", methods=["GET"])
        @jwt_required()
        def engine_stats():
            if not self.engine.running:
                return (
                    jsonify({"status": "error", "message": "Engine is not running"}),
                    404,
                )
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Stats for {type(self.engine).__name__}",
                        "stats": self.engine.web3_manager.position_history[-1],
                    }
                ),
                200,
            )

        @self.app.route("/update", methods=["POST"])
        @jwt_required()
        def update_engine():
            # Only update if engine is running
            if not self.engine.running:
                return (
                    jsonify({"status": "error", "message": "Engine is not running"}),
                    404,
                )

            # Update engine
            self.engine.update()
            logging.info(f"Updated {type(self.engine).__name__}")
            return (
                jsonify(
                    {
                        "status": "success",
                        "message": f"Updated {type(self.engine).__name__}",
                    }
                ),
                200,
            )

        @self.app.route("/healthcheck", methods=["GET"])
        def healthcheck():
            time.sleep(1)
            return jsonify({"status": "success", "message": "Healthy"}), 200

    def run(self):
        self.app.run(debug=self.debug, port=self.port, host=self.host)
