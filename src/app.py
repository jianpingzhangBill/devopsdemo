from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

LoggingInstrumentor().instrument()
BotocoreInstrumentor().instrument()
ConfluentKafkaInstrumentor().instrument()
PyMySQLInstrumentor().instrument()
PymongoInstrumentor().instrument()
RedisInstrumentor().instrument()
RequestsInstrumentor().instrument()


from flask import Flask, request
import datetime
import logs
from settings import settings


def create_app():
    logs.configure_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config.from_mapping(settings.model_dump())

    @app.before_request
    def before_request():
        request.start_time = datetime.datetime.now()

    @app.after_request
    def after_request(response):
        end_time = datetime.datetime.now()
        duration = end_time - request.start_time
        duration_ms = str((end_time - request.start_time).total_seconds() * 1000)
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            client_ip = real_ip
        else:
            # 如果 X-Real-IP 标头不存在，则检查 X-Forwarded-For 标头
            # X-Forwarded-For 可能包含一个逗号分隔的IP列表，其中第一个IP是客户端的真实IP
            forwarded_for = request.headers.get('X-Forwarded-For')
            if forwarded_for:
                client_ip = forwarded_for.split(',')[0]
            else:
                # 如果都不存在，则使用 remote_addr 属性作为客户端IP
                client_ip = request.remote_addr
        if request.path != "/health_check":
            app.logger.debug(f"{client_ip} , visit {request.path}, duration: {duration_ms}")
        return response

    @app.get("/")
    def index():
            # 检查 X-Real-IP 标头

        return "hello world!"

    @app.get("/health_check")
    def health_check():
        return "alive!"
    FlaskInstrumentor().instrument_app(app)
    return app


if __name__ == "__main__":
    create_app().run()
