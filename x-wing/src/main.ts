import {app, BrowserWindow, session, ipcMain} from 'electron';
import path from 'path';
import amqp from 'amqplib';
import dotenv from 'dotenv';

dotenv.config();

let mainWindow: BrowserWindow | null = null;

const APP_NAME = 'x-wing';
const QUEUE_FALCON_MISTER_M = 'QUEUE_FALCON_MISTER_M';
const QUEUE_FALCON_AUDIO = 'QUEUE_FALCON_AUDIO';
const QUEUE_FALCON_ASK = 'QUEUE_FALCON_ASK';
const QUEUE_FALCON_SCREEN = 'QUEUE_FALCON_SCREEN';
const RABBITMQ_URI = process.env.RABBITMQ_URI || 'amqp://falcon:falcon@localhost:5672';

export const EVENTS = {
    CLOSE_APP: 'close-app',
    START_RECORD: 'start-record',
    STOP_RECORD: 'stop-record',
    PRINT_SCREEN: 'print-screen',
    USER_TEXT_INPUT: 'user-text-input',
    NEW_MESSAGE: 'new-message'
};

async function startRabbitMQListener(): Promise<void> {
    try {
        const connection = await amqp.connect(RABBITMQ_URI);
        const channel = await connection.createChannel();
        await channel.assertQueue(QUEUE_FALCON_MISTER_M, {durable: true});
        console.log(`[${APP_NAME}] 🎧 Listening on queue: ${QUEUE_FALCON_MISTER_M}`);

        channel.consume(QUEUE_FALCON_MISTER_M, (msg) => {
            if (msg !== null) {
                const messageContent = msg.content.toString();
                console.log(`[${APP_NAME}] 📩 Message received: ${messageContent}`);
                if (mainWindow?.webContents) {
                    mainWindow.webContents.send(EVENTS.NEW_MESSAGE, messageContent);
                }

                channel.ack(msg);
            }
        });
    } catch (error) {
        console.error(`[${APP_NAME}] ❌ Failed to connect to RabbitMQ:`, error);
    }
}

function createWindow(): void {
    const {width: screenWidth} = require('electron').screen.getPrimaryDisplay().workAreaSize;

    const windowWidth = 600;
    const windowHeight = 400;

    mainWindow = new BrowserWindow({
        width: windowWidth,
        height: windowHeight,
        x: screenWidth - windowWidth,
        y: 0,
        alwaysOnTop: true,
        frame: false,
        skipTaskbar: true,
        transparent: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            allowDisplayingInsecureContent: false,
            nodeIntegration: false,
            contextIsolation: true,
            devTools: false,
        },
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    session.defaultSession.webRequest.onBeforeRequest(
        {urls: ['*://*/*']},
        (details, callback) => {
            callback(details.url.includes('webrtc') ? {cancel: true} : {});
        }
    );

    mainWindow.once('ready-to-show', () => {
        mainWindow?.show();
        console.log(`[${APP_NAME}] 🚀 Window is ready.`);
        startRabbitMQListener();
    });
}

const sendRabbitMessage = async (queueName: string, message: string) => {
    try {
        const connection = await amqp.connect(RABBITMQ_URI);
        const channel = await connection.createChannel();
        await channel.assertQueue(queueName, {durable: true});
        channel.sendToQueue(queueName, Buffer.from(message));
        await channel.close();
        await connection.close();
        console.log(`[${APP_NAME}] 📤 Message sent to queue '${queueName}': ${message}`);
    } catch (error) {
        console.error(`[${APP_NAME}] ❌ Failed to send message to queue '${queueName}':`, error);
    }
};

const sendRabbit = async (message: string) => {
    await sendRabbitMessage(QUEUE_FALCON_AUDIO, message);
};

app.whenReady().then(() => {
    console.log(`[${APP_NAME}] ✅ Application started.`);
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});


ipcMain.on(EVENTS.NEW_MESSAGE, (event, arg) => {
    console.log(`[${APP_NAME}] 💬 Renderer says: ${arg}`);
    event.reply('resposta', 'Message received by Electron.');
});

ipcMain.on(EVENTS.CLOSE_APP, () => {
    console.log(`[${APP_NAME}] 🔌 Closing application.`);
    app.quit();
});

ipcMain.on(EVENTS.START_RECORD, () => {
    console.log(`[${APP_NAME}] 🎙️ Sending START_RECORD command.`);
    sendRabbit('START_RECORD');
});

ipcMain.on(EVENTS.STOP_RECORD, () => {
    console.log(`[${APP_NAME}] 🛑 Sending STOP_RECORD command.`);
    sendRabbit('STOP_RECORD');
});

ipcMain.on(EVENTS.PRINT_SCREEN, () => {
    console.log(`[${APP_NAME}] 📸 Sending PRINT_SCREEN command.`);
    sendRabbitMessage(QUEUE_FALCON_SCREEN, 'PRINT_SCREEN');
});

ipcMain.on(EVENTS.USER_TEXT_INPUT, (_event, message) => {
    const prompt = `Help with this problem:\n\n${message}\n`;
    console.log(`[${APP_NAME}] ✉️ Sending user input to GPT.`);
    sendRabbitMessage(QUEUE_FALCON_ASK, prompt);
});
