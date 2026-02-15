const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'DamaiHelper - 大麦抢票助手',
    icon: path.join(__dirname, 'icon.png'),
    show: false
  });

  // 开发环境加载本地服务器，生产环境加载打包后的文件
  const isDev = process.env.NODE_ENV === 'development';
  
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    // 生产环境
    const frontendPath = app.isPackaged
      ? path.join(process.resourcesPath, 'frontend/index.html')
      : path.join(__dirname, '../frontend/build/index.html');
    
    mainWindow.loadFile(frontendPath);
  }

  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function checkPythonInstalled() {
  return new Promise((resolve) => {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const checkProcess = spawn(pythonCmd, ['--version']);
    
    checkProcess.on('error', () => {
      resolve(false);
    });
    
    checkProcess.on('close', (code) => {
      resolve(code === 0);
    });
  });
}

async function startBackend() {
  // 检查Python是否安装
  const pythonInstalled = await checkPythonInstalled();
  
  if (!pythonInstalled) {
    dialog.showErrorBox(
      '缺少Python环境',
      'DamaiHelper需要Python 3.9或更高版本。\n\n请访问 https://www.python.org 下载安装Python。'
    );
    app.quit();
    return;
  }

  // 启动Python后端服务
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
  
  // 确定backend路径
  const backendPath = app.isPackaged
    ? path.join(process.resourcesPath, 'backend/main.py')
    : path.join(__dirname, '../backend/main.py');
  
  const backendDir = path.dirname(backendPath);
  
  console.log('Starting backend:', backendPath);
  console.log('Backend directory:', backendDir);
  
  backendProcess = spawn(pythonPath, [backendPath], {
    cwd: backendDir,
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`);
  });

  backendProcess.on('error', (error) => {
    console.error('Failed to start backend:', error);
    dialog.showErrorBox(
      '后端启动失败',
      `无法启动后端服务：${error.message}\n\n请确保已安装所有Python依赖。`
    );
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
    if (code !== 0 && code !== null) {
      dialog.showErrorBox(
        '后端异常退出',
        `后端服务异常退出，退出码：${code}`
      );
    }
  });
}

function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend...');
    backendProcess.kill();
    backendProcess = null;
  }
}

app.on('ready', async () => {
  console.log('App is ready');
  console.log('Is packaged:', app.isPackaged);
  console.log('Resources path:', process.resourcesPath);
  
  // 启动后端
  await startBackend();
  
  // 等待后端启动
  setTimeout(() => {
    createWindow();
  }, 3000);
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

