from flask import Flask
import pymysql
import logging
import sys
from pythonjsonlogger import jsonlogger

app = Flask(__name__)

db_config = {
    'host': 'db-master-default.test2.hireez.info',
    'port': 3306,
    'user': 'admin',
    'password': 'fdsafs',
    'database': 'mysql',
}



# logger = logging.getLogger(__name__)
# handler = logging.StreamHandler(stream=sys.stdout)
# formatter = jsonlogger.JsonFormatter(
#         fmt="%(asctime)s [%(name)s] %(funcName)s %(otelTraceID)s %(otelSpanID)s - %(lineno)d - %(levelname)s: %(message)s",
#         datefmt="%Y-%m-%dT%H:%M:%SZ",
#         json_ensure_ascii=False,
#         rename_fields={
#             "asctime": "log_time",
#             "levelname": "level",
#             "message": "content",
#             "funcName": "func",
#             "otelTraceID": "TraceId",
#             "otelSpanID": "SpanId",
#         },
#     )
# handler.setFormatter(formatter)

# logging.basicConfig(level=logging.INFO, handlers=[handler])


@app.route("/health_check")
@app.route("/")
def hello_world():
    logger.info('----test----')
    return "<p>Hello, World!</p>"

@app.route('/tr')
def hello():
    with pymysql.connect(**db_config) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT DISTINCT * FROM user WHERE host = "localhost"')
            rows = cursor.fetchall()
    logger.info("query db")
    unique_rows = list(set(rows))
    return str(unique_rows)

if __name__ == '__main__':
    app.run(port=8000, host="0.0.0.0", debug=True)
