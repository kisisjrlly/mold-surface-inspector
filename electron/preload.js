const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // 启动 WebSocket 服务器
    startWSServer: (config) => ipcRenderer.invoke('start-ws-server', config),
    
    // 停止 WebSocket 服务器
    stopWSServer: () => ipcRenderer.invoke('stop-ws-server'),
    
    // 监听服务器停止事件
    onWSServerStopped: (callback) => ipcRenderer.on('ws-server-stopped', callback)
});
