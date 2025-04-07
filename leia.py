import logging
import os
import tempfile
import threading
import uuid

import numpy as np
import pika
import sounddevice as sd
from pydub import AudioSegment

from consts import (
    RABBITMQ_URI,
    QUEUE_FALCON_AUDIO, START_RECORD, STOP_RECORD, QUEUE_FALCON_TO_SPEECH,
)

APP_NAME = "leia.py"
__version__ = "1.0"

logging.basicConfig(
    level=logging.INFO,
    format=f'%(asctime)s | {APP_NAME} | %(levelname)s | %(message)s'
)

BANNER = r"""

,--.          ,--.         
|  |    ,---. `--' ,--,--. 
|  |   | .-. :,--.' ,-.  | 
|  '--.\   --.|  |\ '-'  | 
`-----' `----'`--' `--`--' 

📡 “Ajude-me, Obi-Wan Kenobi. Você é minha única esperança.”

"""

is_recording = False
recording_thread = None
audio_data = []
samplerate = 44100  # CD-quality sample rate

def audio_callback(indata, frames, time, status):
    if status:
        logging.warning(f"Audio status: {status}")
    audio_data.append(indata.copy())

def start_audio_recording():
    global is_recording, audio_data, recording_thread
    if is_recording:
        logging.info(f"{APP_NAME}: Recording is already in progress.")
        return

    is_recording = True
    audio_data = []

    def record():
        with sd.InputStream(callback=audio_callback, channels=1, samplerate=samplerate):
            logging.info(f"{APP_NAME}: Audio recording started.")
            while is_recording:
                sd.sleep(100)

    recording_thread = threading.Thread(target=record)
    recording_thread.start()

def stop_audio_recording_and_save():
    global is_recording, recording_thread
    if not is_recording:
        logging.info(f"{APP_NAME}: Recording is not active.")
        return None

    is_recording = False
    recording_thread.join()
    logging.info(f"{APP_NAME}: Audio recording stopped.")

    audio_np = np.concatenate(audio_data)
    wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
    mp3_path = wav_path.replace(".wav", ".mp3")

    audio_segment = AudioSegment(
        (audio_np * 32767).astype(np.int16).tobytes(),
        frame_rate=samplerate,
        sample_width=2,
        channels=1
    )
    audio_segment.export(mp3_path, format="mp3")
    logging.info(f"{APP_NAME}: Audio saved as: {mp3_path}")
    return mp3_path

def send_message(queue, message):
    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=message.encode()
        )
        logging.info(f"{APP_NAME}: Message sent to '{queue}': {message}")
        connection.close()
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to send message: {e}")

def on_message(ch, method, properties, body):
    message = body.decode()
    logging.info(f"{APP_NAME}: Received command: {message}")

    if message == START_RECORD:
        start_audio_recording()

    elif message == STOP_RECORD:
        audio_path = stop_audio_recording_and_save()
        if audio_path:
            send_message(QUEUE_FALCON_TO_SPEECH, audio_path)

def listen_for_commands():
    print(BANNER)
    logging.info(f"{APP_NAME}: Listening for audio commands...")

    try:
        params = pika.URLParameters(RABBITMQ_URI)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_FALCON_AUDIO, durable=True)
        channel.basic_consume(
            queue=QUEUE_FALCON_AUDIO,
            on_message_callback=on_message,
            auto_ack=True
        )
        channel.start_consuming()
    except Exception as e:
        logging.error(f"{APP_NAME}: Listener encountered an error: {e}")

if __name__ == '__main__':
    listen_for_commands()
