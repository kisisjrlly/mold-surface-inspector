const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow = null;
let pythonProcess = null;

// 检测 Python 路径
function getPythonPath() {
    // 尝试常见的 conda inspector 环境路径
    const condaPaths = [
        'C:\\Users\\16902\\.conda\\envs\\inspector\\python.exe',
        path.join(process.env.USERPROFILE, '.conda', 'envs', 'inspector', 'python.exe'),
        path.join(process.env.LOCALAPPDATA, 'anaconda3', 'envs', 'inspector', 'python.exe'),
        'D:\\software\\miniconda\\envs\\inspector\\python.exe'
    ];
    
    for (const pyPath of condaPaths) {
        if (fs.existsSync(pyPath)) {
            console.log(`找到 Python 环境: ${pyPath}`);
            return pyPath;
        }
    }
    
    // 如果找不到 inspector 环境，使用环境变量
    if (process.env.CONDA_PYTHON_EXE) {
        console.log(`使用环境变量 Python: ${process.env.CONDA_PYTHON_EXE}`);
        return process.env.CONDA_PYTHON_EXE;
    }
    
    // 最后尝试系统 Python（可能缺少依赖）
    console.warn('警告: 未找到 inspector 环境，使用系统 Python 可能缺少必要的包');
    return 'python';
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        title: '模具曲面精度分析系统',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));
    
    // 开发时打开 DevTools
    // mainWindow.webContents.openDevTools();
}

// IPC: 启动 WebSocket 服务器
ipcMain.handle('start-ws-server', async (event, config) => {
    // 如果已有服务在运行，先停止
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return new Promise((resolve, reject) => {
        const { plcIp, plcPort } = config;
        const pythonPath = getPythonPath();
        const scriptPath = path.join(__dirname, '..', 'electron_ws_server.py');
        const args = [scriptPath, plcIp, plcPort.toString()];
        
        console.log(`启动 WebSocket 服务: ${pythonPath} ${args.join(' ')}`);
        
        pythonProcess = spawn(pythonPath, args, {
            cwd: path.join(__dirname, '..')
        });
        
        let startupOutput = '';
        let hasResolved = false;
        
        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString();
            console.log('[WS Server]', output);
            startupOutput += output;
            
            // 检测启动成功标志
            if (!hasResolved && (output.includes('WebSocket server started') || output.includes('server listening'))) {
                hasResolved = true;
                resolve({ success: true, message: 'WebSocket 服务器启动成功' });
            }
        });
        
        pythonProcess.stderr.on('data', (data) => {
            const errOutput = data.toString();
            console.error('[WS Server Error]', errOutput);
            startupOutput += errOutput;
            
            // Python 日志库可能将 INFO 级别输出到 stderr，也检测成功标志
            if (!hasResolved && (errOutput.includes('WebSocket server started') || errOutput.includes('server listening'))) {
                hasResolved = true;
                resolve({ success: true, message: 'WebSocket 服务器启动成功' });
            }
            
            // 只有明确的错误才拒绝（Traceback, ModuleNotFoundError 等）
            if (!hasResolved && (errOutput.includes('Traceback') || errOutput.includes('Error:') || errOutput.includes('ModuleNotFoundError'))) {
                hasResolved = true;
                reject({ success: false, message: `启动失败: ${errOutput.substring(0, 200)}` });
            }
        });
        
        pythonProcess.on('error', (error) => {
            if (!hasResolved) {
                hasResolved = true;
                reject({ success: false, message: `无法启动 Python: ${error.message}` });
            }
        });
        
        pythonProcess.on('exit', (code) => {
            console.log(`WebSocket 服务器退出，代码: ${code}`);
            pythonProcess = null;
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send('ws-server-stopped', code);
            }
        });
        
        // 5秒超时
        setTimeout(() => {
            if (!hasResolved) {
                hasResolved = true;
                reject({ success: false, message: '启动超时，请检查 Python 环境和依赖包是否已安装' });
            }
        }, 5000);
    });
});

// IPC: 停止 WebSocket 服务器
ipcMain.handle('stop-ws-server', async () => {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
        return { success: true, message: 'WebSocket 服务器已停止' };
    }
    return { success: false, message: '没有运行中的服务器' };
});

app.whenReady().then(() => {
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    // 清理 Python 进程
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
});
