import pika
import threading
import time
from fastapi import FastAPI, Depends

from .database import Base, engine, get_db, SessionLocal
from . import crud
from . import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Notification Service - Ranim")

RABBITMQ_HOST = "rabbitmq"  # must match service name in docker-compose

# -------------------------------------------------------
# RABBITMQ LISTENER FUNC
# -------------------------------------------------------
def start_consumer():
    print("🔥 Consumer function loaded.", flush=True)

    while True:
        try:
            print(f"🔌 Trying to connect to RabbitMQ at host={RABBITMQ_HOST} ...", flush=True)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()

            # Make sure the queue exists and is durable
            channel.queue_declare(queue="booking_notifications", durable=True)

            def callback(ch, method, properties, body):
                message = body.decode()
                print("📩 Received message:", message, flush=True)

                db = SessionLocal()
                try:
                    crud.create_notification(db, message)
                finally:
                    db.close()

            channel.basic_consume(
                queue="booking_notifications",
                durable=True,
                on_message_callback=callback,
                auto_ack=True
            )

            print("📥 Notification service listening for RabbitMQ messages...", flush=True)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            print(f"❌ RabbitMQ connection failed: {e}. Retrying in 5 seconds...", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"💥 Unexpected error in consumer: {e}. Retrying in 5 seconds...", flush=True)
            time.sleep(5)

# -------------------------------------------------------
# STARTUP EVENT
# -------------------------------------------------------
@app.on_event("startup")
def startup_event():
    print("🚀 RabbitMQ listener thread starting...", flush=True)
    t = threading.Thread(target=start_consumer, daemon=True)
    t.start()

# -------------------------------------------------------
# API ENDPOINTS
# -------------------------------------------------------
@app.get("/notifications", response_model=list[schemas.NotificationOut])
def get_notifications(db=Depends(get_db)):
    return crud.get_notifications(db)

@app.get("/health")
def health():
    return {"status": "ok", "service": "notifications"}
