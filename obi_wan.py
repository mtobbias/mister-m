import os
import logging
import pika
from dotenv import load_dotenv
from openai import OpenAI

from consts import (
    RABBITMQ_URI,
    QUEUE_FALCON_TO_SPEECH,
    QUEUE_FALCON_MISTER_M
)

APP_NAME = "obi_wan.py"
__version__ = "1.0"

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

BANNER = r"""

  ,--. ,--.   ,--.       ,--.   ,--.                 
 /    \|  |-. `--',-----.|  |   |  | ,--,--.,--,--,  
|  ()  | .-. ',--.'-----'|  |.'.|  |' ,-.  ||      \ 
 \    /| `-' ||  |       |   ,'.   |\ '-'  ||  ||  | 
  `--'  `---' `--'       '--'   '--' `--`--'`--''--' 

🚗 ...precisa aprender o alcance da Força, se quiser vir comigo para Alderaan

"""

def transcribe_audio(file_path):
    try:
        logging.info(f"{APP_NAME}: Starting transcription: {file_path}")
        with open(file_path, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="pt"
            )
        logging.info(f"{APP_NAME}: Transcription complete.")
        return result
    except Exception as e:
        logging.error(f"{APP_NAME}: Transcription error: {e}")
        return None

def send_to_queue(queue_name, message):
    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message.encode(),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        logging.info(f"{APP_NAME}: Message sent to queue '{queue_name}'")
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to send message to queue {queue_name}: {e}")

def on_message(ch, method, properties, body):
    file_path = body.decode()
    logging.info(f"{APP_NAME}: Received audio path: {file_path}")

    if not os.path.exists(file_path):
        logging.warning(f"{APP_NAME}: Audio file not found: {file_path}")
        return

    transcription = transcribe_audio(file_path)
    if transcription:
        print(f"\n🗣️ Transcription:\n{transcription}\n")
        send_to_queue(QUEUE_FALCON_MISTER_M, transcription)

def listen_for_commands():
    print(BANNER)

    if not RABBITMQ_URI:
        logging.critical(f"{APP_NAME}: RABBITMQ_URI is not set.")
        return

    logging.info(f"{APP_NAME}: Whisprr agent is online.")
    logging.info(f"{APP_NAME}: Waiting for audio files to transcribe...")

    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_TO_SPEECH, durable=True)
        channel.basic_consume(
            queue=QUEUE_FALCON_TO_SPEECH,
            on_message_callback=on_message,
            auto_ack=True
        )
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Listener failed: {e}")

if __name__ == '__main__':
    listen_for_commands()
