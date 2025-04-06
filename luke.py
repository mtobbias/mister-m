import logging
import uuid
import pika
import tempfile
from PIL import ImageGrab
import os

from consts import (
    RABBITMQ_URI,
    QUEUE_FALCON_DESCRIBE,
    QUEUE_FALCON_SCREEN, PRINT_SCREEN
)

APP_NAME = "luke.py"
__version__ = "1.0"

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

BANNER = r"""

,--.           ,--.           
|  |   ,--.,--.|  |,-. ,---.  
|  |   |  ||  ||     /| .-. : 
|  '--.'  ''  '|  \  \\   --. 
`-----' `----' `--'`--'`----' 

🌌 Está certo, eu vou tentar
"""

def send_message_with_path(file_path):
    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_DESCRIBE, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_FALCON_DESCRIBE,
            body=file_path
        )
        logging.info(f"{APP_NAME}: Screenshot path sent to queue: {file_path}")
        connection.close()
    except Exception as e:
        logging.error(f"{APP_NAME}: Error sending message to queue: {e}")

def capture_screenshot():
    try:
        image = ImageGrab.grab()
        filename = f"{uuid.uuid4()}.png"
        file_path = os.path.join(tempfile.gettempdir(), filename)
        image.save(file_path)
        logging.info(f"{APP_NAME}: Screenshot captured and saved to: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"{APP_NAME}: Error capturing screenshot: {e}")
        return None

def on_message(ch, method, properties, body):
    message = body.decode()
    logging.info(f"{APP_NAME}: Received message: {message}")
    if message == PRINT_SCREEN:
        screenshot_path = capture_screenshot()
        if screenshot_path:
            send_message_with_path(screenshot_path)

def listen_for_commands():
    print(BANNER)
    if not RABBITMQ_URI:
        logging.error(f"{APP_NAME}: RABBITMQ_URI is not set. Please check your configuration.")
        return
    logging.info(f"{APP_NAME}: SpideySnap agent is online.")
    logging.info(f"{APP_NAME}: Listening for screenshot events...")
    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_SCREEN, durable=True)
        channel.basic_consume(
            queue=QUEUE_FALCON_SCREEN,
            on_message_callback=on_message,
            auto_ack=True
        )
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Listener failed: {e}")

if __name__ == '__main__':
    listen_for_commands()
