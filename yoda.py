import logging
import os

import pika
from dotenv import load_dotenv
from openai import OpenAI

from consts import RABBITMQ_URI, QUEUE_FALCON_ASK, QUEUE_FALCON_X_WING

APP_NAME = "yoda.py"
__version__ = "1.0"

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

BANNER = r"""

,--.   ,--.        ,--.         
 \  `.'  /,---.  ,-|  | ,--,--. 
  '.    /| .-. |' .-. |' ,-.  | 
    |  | ' '-' '\ `-' |\ '-'  | 
    `--'  `---'  `---'  `--`--' 

     🧙‍♂️ Que a Força esteja com você - M. Yoda
"""


def process_text_with_gpt(prompt: str) -> str | None:
    try:
        logging.info(f"{APP_NAME}: Sending prompt to OpenAI GPT model...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        answer = response.choices[0].message.content
        logging.info(f"{APP_NAME}: Response received from GPT.")
        return answer
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to process text with GPT: {e}")
        return None


def send_to_queue(queue_name: str, message: str):
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
        logging.error(f"{APP_NAME}: Failed to send message to queue '{queue_name}': {e}")


def on_message(ch, method, properties, body):
    prompt = body.decode()
    logging.info(f"{APP_NAME}: Received prompt: {prompt}")
    result = process_text_with_gpt(prompt)
    if result:
        send_to_queue(QUEUE_FALCON_X_WING, result)


def listen_for_commands():
    print(BANNER)

    if not RABBITMQ_URI:
        logging.critical(f"{APP_NAME}: Missing RabbitMQ URI in environment.")
        return

    logging.info(f"{APP_NAME}: Agent is online.")
    logging.info(f"{APP_NAME}: Listening for prompts on queue '{QUEUE_FALCON_ASK}'...")

    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_ASK, durable=True)
        channel.basic_consume(
            queue=QUEUE_FALCON_ASK,
            on_message_callback=on_message,
            auto_ack=True
        )
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Listener failed: {e}")


if __name__ == '__main__':
    listen_for_commands()