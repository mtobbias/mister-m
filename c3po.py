import os
import logging
import base64
import pika
import requests
from openai import OpenAI

from consts import RABBITMQ_URI, QUEUE_FALCON_DESCRIBE, QUEUE_FALCON_ASK,C3P0_LLM_PROVIDER,C3PO_OLLAMA_MODEL,C3PO_OPENAI_API_KEY

APP_NAME = "c3po.py"
__version__ = "1.0"


logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

BANNER = r"""
 ,-----.       ,----.,------. ,-----.  
'  .--./,-----.'.-.  |  .--. '  .-.  ' 
|  |    '-----'  .' <|  '--' |  | |  | 
'  '--'\       /'-'  |  | --''  '-'  ' 
 `-----'       `----'`--'     `-----'  

🤖🛠️ Como fomos nos meter nessa enrascada?"
"""


client = OpenAI(api_key=C3PO_OPENAI_API_KEY) if C3P0_LLM_PROVIDER == "openai" else None


def describe_image(file_path):
    try:
        logging.info(f"{APP_NAME}: Describing image from path: {file_path}")
        with open(file_path, "rb") as img_file:
            image_bytes = img_file.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        if C3P0_LLM_PROVIDER == "openai":
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe the contents of this screenshot in detail."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            description = response.choices[0].message.content

        elif C3P0_LLM_PROVIDER == "ollama":
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": C3PO_OLLAMA_MODEL,
                    "prompt": "Describe the contents of this screenshot in detail.",
                    "images": [image_base64],
                    "stream": False
                }
            )
            response.raise_for_status()
            description = response.json().get("response", "No description returned.")

        else:
            raise ValueError(f"Unsupported LLM provider: {C3P0_LLM_PROVIDER}")

        logging.info(f"{APP_NAME}: Image description successfully generated.")
        return description

    except Exception as e:
        logging.error(f"{APP_NAME}: Error while describing image: {e}")
        return None


def send_to_queue(queue_name, message):
    try:
        logging.info(f"{APP_NAME}: Connecting to RabbitMQ to send message to queue: {queue_name}")
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
        logging.info(f"{APP_NAME}: Message successfully sent to queue: {queue_name}")
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to send message to queue '{queue_name}': {e}")


def on_message(ch, method, properties, body):
    file_path = body.decode()
    logging.info(f"{APP_NAME}: Received message with image path: {file_path}")

    if not os.path.exists(file_path):
        logging.warning(f"{APP_NAME}: File not found at path: {file_path}")
        return

    description = describe_image(file_path)
    if description:
        print(f"\n📝 Description:\n{description}\n")
        send_to_queue(QUEUE_FALCON_ASK, description)
    else:
        logging.warning(f"{APP_NAME}: No description was generated from the image.")


def listen_for_commands():
    print(BANNER)

    if not RABBITMQ_URI:
        logging.critical(f"{APP_NAME}: Environment variable RABBITMQ_URI is not set. Exiting.")
        return

    logging.info(f"{APP_NAME}: C-3PO Agent is now online using LLM_PROVIDER='{C3P0_LLM_PROVIDER}'.")
    logging.info(f"{APP_NAME}: Awaiting image paths for processing...")

    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_DESCRIBE, durable=True)
        channel.basic_consume(
            queue=QUEUE_FALCON_DESCRIBE,
            on_message_callback=on_message,
            auto_ack=True
        )
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Error starting message listener: {e}")


if __name__ == '__main__':
    listen_for_commands()
