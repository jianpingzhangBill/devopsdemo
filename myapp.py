from random import randint
from flask import Flask, request
import logging
from logging.config import dictConfig


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route("/")
def roll_dice():
    player = request.args.get('player', default = None, type = str)
    result = str(roll())
    if player:
        logger.warning("%s is rolling the dice: %s", player, result)
    else:
        logger.warning("Anonymous player is rolling the dice: %s", result)
    return result

def roll():
    return randint(1, 6)
@app.get("/health_check")
def health_check():
    return "alive!"

if __name__ == "__main__":
    import os
    print(os.getenv("OTEL_SERVICE_NAME")) 
    app.run(host="0.0.0.0",port=8000,debug=True)
