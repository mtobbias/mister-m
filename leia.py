import os
import tempfile
import threading
import time
import uuid
import logging
from queue import Queue

import numpy as np
import sounddevice as sd
import pika
from pydub import AudioSegment
from faster_whisper import WhisperModel
from openai import OpenAI

from consts import (
    RABBITMQ_URI,
    LEIA_QUEUE_OUTPUT,
    LEIA_TRANSCRIBE_PROVIDER,
    LEIA_OPENAI_API_KEY,
    LEIA_SAMPLERATE,
    LEIA_CHUNK_DURATION,
    LEIA_OVERLAP,
    LEIA_BUFFER_SIZE,
    LEIA_STEP_SIZE,
    LEIA_NOISE_THRESHOLD,
)

APP_NAME = "leia.py"
__version__ = "2.3"

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

🎙️ “Leia recording, transcribing, and transmitting almost in real-time. The Force is with you.”
"""

# === MODELS ===
if LEIA_TRANSCRIBE_PROVIDER == "local":
    model = WhisperModel("tiny", compute_type="int8", local_files_only=False)
    openai_client = None
elif LEIA_TRANSCRIBE_PROVIDER == "openai":
    openai_client = OpenAI(api_key=LEIA_OPENAI_API_KEY)
    model = None
else:
    raise ValueError(f"{APP_NAME}: Unknown LEIA_TRANSCRIBE_PROVIDER: {LEIA_TRANSCRIBE_PROVIDER}")

# === STATE ===
audio_buffer = np.zeros((0, 1), dtype=np.float32)
audio_queue = Queue()
is_running = True
last_transcription = ""
context_buffer = []

def audio_callback(indata, frames, time_info, status):
    global audio_buffer
    if status:
        logging.warning(f"Audio status: {status}")
    cleaned = np.where(np.abs(indata) < LEIA_NOISE_THRESHOLD, 0.0, indata)
    audio_buffer = np.concatenate((audio_buffer, cleaned), axis=0)

def transcribe_audio(audio_np) -> str | None:
    try:
        if np.max(np.abs(audio_np)) < LEIA_NOISE_THRESHOLD:
            logging.debug(f"{APP_NAME}: Chunk ignored due to noise threshold.")
            return None

        wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        audio_segment = AudioSegment(
            (audio_np * 32767).astype(np.int16).tobytes(),
            frame_rate=LEIA_SAMPLERATE,
            sample_width=2,
            channels=1
        )
        audio_segment.export(wav_path, format="wav")

        if LEIA_TRANSCRIBE_PROVIDER == "local":
            segments, _ = model.transcribe(
                wav_path,
                beam_size=5,
                vad_filter=True
            )
            transcription_parts = [seg.text.strip() for seg in segments]
            transcription = " ".join(transcription_parts).strip()

        elif LEIA_TRANSCRIBE_PROVIDER == "openai":
            with open(wav_path, "rb") as audio_file:
                response = openai_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-1",
                    language="pt",
                    response_format="text"
                )
                transcription = response.strip()
                logging.debug(f"{APP_NAME}: OpenAI transcription result: {transcription}")

        logging.info(f"{APP_NAME}: Final transcription: {transcription}")
        return transcription if transcription else None

    except Exception as e:
        logging.error(f"{APP_NAME}: Transcription error: {e}")
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
        logging.info(f"{APP_NAME}: Sent to '{queue_name}': {message}")
    except Exception as e:
        logging.error(f"{APP_NAME}: Failed to send to queue: {e}")

def processor_loop():
    global audio_buffer

    while is_running:
        time.sleep(LEIA_CHUNK_DURATION - LEIA_OVERLAP)
        if len(audio_buffer) < LEIA_BUFFER_SIZE:
            continue

        chunk = audio_buffer[:LEIA_BUFFER_SIZE]
        audio_buffer = audio_buffer[LEIA_STEP_SIZE:]
        audio_queue.put(chunk)
        logging.debug(f"{APP_NAME}: Chunk added to queue (current size: {audio_queue.qsize()})")

def transcription_worker():
    global last_transcription, context_buffer

    while is_running:
        chunk = audio_queue.get()
        transcription = transcribe_audio(chunk)
        if transcription:
            context_buffer.append(transcription)
            if len(context_buffer) >= 2:
                full_text = " ".join(context_buffer).strip()
                if full_text != last_transcription:
                    logging.info("\n" + "-" * 60)
                    logging.info(f"🗣️  New transcription (with context):\n{full_text}")
                    logging.info("-" * 60)
                    send_to_queue(LEIA_QUEUE_OUTPUT, full_text)
                    last_transcription = full_text
                    context_buffer.clear()
        audio_queue.task_done()

def listen_for_commands():
    global is_running
    print(BANNER)
    logging.info(f"{APP_NAME}: Recording and transcribing in near real-time (chunk={LEIA_CHUNK_DURATION}s, overlap={LEIA_OVERLAP}s)...")
    logging.info(f"{APP_NAME}: Transcription provider: {LEIA_TRANSCRIBE_PROVIDER}")
    is_running = True

    threading.Thread(target=processor_loop, daemon=True).start()
    threading.Thread(target=transcription_worker, daemon=True).start()

    with sd.InputStream(callback=audio_callback, channels=1, samplerate=LEIA_SAMPLERATE):
        while is_running:
            sd.sleep(100)

if __name__ == '__main__':
    try:
        listen_for_commands()
    except KeyboardInterrupt:
        is_running = False
        logging.info(f"{APP_NAME}: Stopped by user.")
