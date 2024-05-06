import logging
import os

import boto3
from flask import Flask

app = Flask(__name__)


logger = logging.getLogger(__name__)


@app.route("/")
def hello_world():
    logger.info("----test----")
    return "<p>Hello, World!</p>"


def create_app():
    sm = boto3.client("secretsmanager").get_secret_value(
        SecretId=os.getenv("SQLALCHEMY_DATABASE_URI")
    )
    print(sm)
    return app


if __name__ == "__main__":
    app.run(port=8000, host="0.0.0.0", debug=True)
