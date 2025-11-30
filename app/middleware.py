import os
import jwt
from flask import jsonify
from flask import request

SECRET_KEY = os.getenv("SECRET_KEY")


def authenticate_user():
    """
    This function is used for authentication and returns its own custom response

    Responses sent are usually tuples, while the decoded message is a ``<class 'dict'>``
    """

    bearer = request.headers.get("Authorization")

    if not bearer:
        return jsonify({"error": "Authorization header was not provided"}), 400

    if not bearer.startswith("Bearer"):
        return (
            jsonify({"error": "No bearer token was found, failed to authenticate"}),
            400,
        )

    token = bearer.split()[1]

    if not token:
        return (
            jsonify({"error": "No token provided, failed to autheticate request"}),
            400,
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if not payload:
            return (
                jsonify(
                    {
                        "error": "Invalid token provided recieved empty payload during processing"
                    }
                ),
                400,
            )
        return payload
    except (
        jwt.InvalidTokenError,
        jwt.ExpiredSignatureError,
        jwt.InvalidSignatureError,
    ):
        return (
            jsonify({"error": "An error occured when processing the token provided"}),
            500,
        )
