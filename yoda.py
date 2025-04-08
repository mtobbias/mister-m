import logging
import os
import requests
import pika
from openai import OpenAI

from consts import (
    RABBITMQ_URI,
    QUEUE_FALCON_ASK,
    QUEUE_FALCON_ASK_AUDIO,
    QUEUE_FALCON_X_WING,
    QUEUE_FALCON_X_WING_AUDIO,
    OPENAI_API_KEY,
    LLM_PROVIDER,
    OLLAMA_MODEL
)

APP_NAME = "yoda.py"
__version__ = "1.2"

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

client = OpenAI(api_key=OPENAI_API_KEY) if LLM_PROVIDER == "gpt" else None


def process_text_with_llm(prompt: str) -> str | None:
    try:
        logging.info(f"{APP_NAME}: Using provider '{LLM_PROVIDER}'")
        if LLM_PROVIDER == "gpt":
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )
            return response.choices[0].message.content

        elif LLM_PROVIDER == "ollama":
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        else:
            logging.error(f"{APP_NAME}: Unsupported LLM_PROVIDER: {LLM_PROVIDER}")
            return None

    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to process text with LLM: {e}")
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


def handle_message(prompt: str, origin_queue: str):
    logging.info(f"{APP_NAME}: Received from '{origin_queue}': {prompt}")
    result = process_text_with_llm(prompt)
    if result:
        if origin_queue == QUEUE_FALCON_ASK:
            send_to_queue(QUEUE_FALCON_X_WING, result)
        elif origin_queue == QUEUE_FALCON_ASK_AUDIO:
            send_to_queue(QUEUE_FALCON_X_WING_AUDIO, result)


def start_listener(queue_name: str):
    def callback(ch, method, properties, body):
        prompt = body.decode()
        handle_message(prompt, queue_name)

    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=True
        )
        logging.info(f"{APP_NAME}: Listening on '{queue_name}'")
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to listen on '{queue_name}': {e}")


def listen_for_commands():
    print(BANNER)

    if not RABBITMQ_URI:
        logging.critical(f"{APP_NAME}: Missing RABBITMQ_URI.")
        return

    logging.info(f"{APP_NAME}: Agent is online using '{LLM_PROVIDER}'.")

    # Start both listeners in threads
    import threading
    threading.Thread(target=start_listener, args=(QUEUE_FALCON_ASK,), daemon=True).start()
    threading.Thread(target=start_listener, args=(QUEUE_FALCON_ASK_AUDIO,), daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            pass
    except KeyboardInterrupt:
        logging.info(f"{APP_NAME}: Agent interrupted and stopped.")


if __name__ == '__main__':
    listen_for_commands()
