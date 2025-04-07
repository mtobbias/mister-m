import logging
import time
import pika
from pynput import keyboard

from consts import (
    QUEUE_FALCON_AUDIO,
    RABBITMQ_URI, PRINT_SCREEN, QUEUE_FALCON_SCREEN, START_RECORD, STOP_RECORD
)

APP_NAME = "han_solo.py"
__version__ = "1.0"

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

# ASCII Banner
BANNER = r"""

 ,--.  ,--.                  ,---.         ,--.        
 |  '--'  | ,--,--.,--,--,  '   .-'  ,---. |  | ,---.  
 |  .--.  |' ,-.  ||      \ `.  `-. | .-. ||  || .-. | 
 |  |  |  |\ '-'  ||  ||  | .-'    |' '-' '|  |' '-' ' 
 `--'  `--' `--`--'`--''--' `-----'  `---' `--' `---'  


"""

# Key combinations
COMBO_ACTIONS = {
    frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode(char='m')]): (
    QUEUE_FALCON_SCREEN, PRINT_SCREEN),
    frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode(char='s')]): (
    QUEUE_FALCON_AUDIO, START_RECORD),
    frozenset([keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode(char='r')]): (
    QUEUE_FALCON_AUDIO, STOP_RECORD),
    frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode(char='m')]): (
    QUEUE_FALCON_SCREEN, PRINT_SCREEN),
    frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode(char='s')]): (
    QUEUE_FALCON_AUDIO, START_RECORD),
    frozenset([keyboard.Key.ctrl_r, keyboard.Key.alt_r, keyboard.KeyCode(char='r')]): (
    QUEUE_FALCON_AUDIO, STOP_RECORD),
}

# State
pressed_keys = set()
last_trigger_time = 0
TRIGGER_COOLDOWN = 1.0  # seconds


def send_message(queue_name: str, message: str) -> None:
    """Send a message to a specific RabbitMQ queue."""
    try:
        logging.info(f"Connecting to RabbitMQ to send message to queue: {queue_name}")
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(exchange='', routing_key=queue_name, body=message)
        connection.close()
        logging.info(f"Message successfully sent to queue '{queue_name}': {message}")
    except Exception as e:
        logging.error(f"Failed to send message to queue '{queue_name}': {e}")


def handle_key_combinations():
    """Check and handle key combination triggers."""
    global last_trigger_time
    now = time.time()

    if now - last_trigger_time < TRIGGER_COOLDOWN:
        return  # Prevent repeated triggering

    current_keys = frozenset(pressed_keys)

    for combo, (queue, event) in COMBO_ACTIONS.items():
        if combo.issubset(current_keys):
            logging.info(f"Trigger detected: sending '{event}' to queue '{queue}'")
            send_message(queue, event)
            last_trigger_time = now
            break


def on_press(key):
    pressed_keys.add(key)
    handle_key_combinations()


def on_release(key):
    pressed_keys.discard(key)


def listen_for_commands():
    print(BANNER)
    logging.info("HanSolo Agent is online.")
    logging.info("Listening for secure key triggers:")
    logging.info(" - Ctrl + Alt + M => Trigger Screenshot")
    logging.info(" - Ctrl + Alt + S => Start Audio Recording")
    logging.info(" - Ctrl + Alt + R => Stop Audio Recording")
    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        logging.info("HanSolo Agent terminated by user.")


def ghostkey():
    return None


if __name__ == '__main__':
    listen_for_commands()
