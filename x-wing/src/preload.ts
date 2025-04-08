const { contextBridge, ipcRenderer } = require('electron');

export const EVENTS = {
    CLOSE_APP: 'close-app',
    START_RECORD: 'start-record',
    STOP_RECORD: 'stop-record',
    PRINT_SCREEN: 'print-screen',
    USER_TEXT_INPUT: 'user-text-input',
    NEW_MESSAGE: 'new-message',
    NEW_MESSAGE_AUDIO: 'new-message-audio'
};

contextBridge.exposeInMainWorld('electronAPI', {
    closeApp: () => ipcRenderer.send(EVENTS.CLOSE_APP),
    startRecording: () => ipcRenderer.send(EVENTS.START_RECORD),
    stopRecording: () => ipcRenderer.send(EVENTS.STOP_RECORD),
    takeScreenshot: () => ipcRenderer.send(EVENTS.PRINT_SCREEN),
    sendUserText: (text: string) => ipcRenderer.send(EVENTS.USER_TEXT_INPUT, text),
    onNewMessage: (callback: (message: string) => void) =>
        ipcRenderer.on(EVENTS.NEW_MESSAGE, (_event:any, message:any) => callback(message)),
    onNewMessageAudio: (callback: (message: string) => void) =>
        ipcRenderer.on(EVENTS.NEW_MESSAGE_AUDIO, (_event:any, message:any) => callback(message))
});
