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
from consts import RABBITMQ_URI, QUEUE_FALCON_X_WING_AUDIO

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

# === CONFIG ===
samplerate = 44100
chunk_duration = 3.0
overlap = 1.0
buffer_size = int(samplerate * chunk_duration)
step_size = int(samplerate * (chunk_duration - overlap))
noise_threshold = 0.01

# === MODEL ===
model = WhisperModel("tiny", compute_type="int8", local_files_only=False)

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
    cleaned = np.where(np.abs(indata) < noise_threshold, 0.0, indata)
    audio_buffer = np.concatenate((audio_buffer, cleaned), axis=0)


def transcribe_audio(audio_np) -> str | None:
    try:
        if np.max(np.abs(audio_np)) < noise_threshold:
            logging.debug(f"{APP_NAME}: Chunk ignored due to noise threshold.")
            return None

        wav_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        audio_segment = AudioSegment(
            (audio_np * 32767).astype(np.int16).tobytes(),
            frame_rate=samplerate,
            sample_width=2,
            channels=1
        )
        audio_segment.export(wav_path, format="wav")

        segments, _ = model.transcribe(
            wav_path,
            beam_size=5,
            vad_filter=True
        )

        transcription_parts = []
        for seg in segments:
            logging.debug(f"{APP_NAME}: Segment: [{seg.start:.2f}s - {seg.end:.2f}s] {seg.text.strip()}")
            transcription_parts.append(seg.text.strip())

        transcription = " ".join(transcription_parts).strip()
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
        time.sleep(chunk_duration - overlap)

        if len(audio_buffer) < buffer_size:
            continue

        chunk = audio_buffer[:buffer_size]
        audio_buffer = audio_buffer[step_size:]
        audio_queue.put(chunk)

        logging.debug(f"{APP_NAME}: Chunk added to queue (current size: {audio_queue.qsize()})")


def transcription_worker():
    global last_transcription, context_buffer

    while is_running:
        chunk = audio_queue.get()
        transcription = transcribe_audio(chunk)
        if transcription:
            context_buffer.append(transcription)
            logging.debug(f"{APP_NAME}: Accumulated context: {context_buffer}")

            if len(context_buffer) >= 2:
                full_text = " ".join(context_buffer).strip()
                if full_text != last_transcription:
                    logging.info("\n" + "-" * 60)
                    logging.info(f"🗣️  New transcription (with context):\n{full_text}")
                    logging.info("-" * 60)
                    send_to_queue(QUEUE_FALCON_X_WING_AUDIO, full_text)
                    last_transcription = full_text
                    context_buffer.clear()
        audio_queue.task_done()


def start_recording_loop():
    global is_running
    print(BANNER)
    logging.info(f"{APP_NAME}: Recording and transcribing in near real-time (chunk={chunk_duration}s, overlap={overlap}s)...")
    is_running = True

    processor = threading.Thread(target=processor_loop, daemon=True)
    transcriber = threading.Thread(target=transcription_worker, daemon=True)

    processor.start()
    transcriber.start()

    with sd.InputStream(callback=audio_callback, channels=1, samplerate=samplerate):
        while is_running:
            sd.sleep(100)


if __name__ == '__main__':
    try:
        start_recording_loop()
    except KeyboardInterrupt:
        is_running = False
        logging.info(f"{APP_NAME}: Stopped by user.")
