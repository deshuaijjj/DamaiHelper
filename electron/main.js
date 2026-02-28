const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let backendProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1024,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'DamaiHelper',
    icon: getIconPath(),
    show: false
  });

  // 开发环境加载本地服务器，生产环境加载打包后的文件
  const isDev = !app.isPackaged;
  
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    const frontendPath = path.join(__dirname, '../frontend/build/index.html');
    mainWindow.loadFile(frontendPath);
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function getIconPath() {
  const iconDir = app.isPackaged 
    ? path.join(process.resourcesPath, 'assets')
    : path.join(__dirname, '../assets');
  
  if (process.platform === 'win32') {
    return path.join(iconDir, 'icon.ico');
  } else if (process.platform === 'darwin') {
    return path.join(iconDir, 'icon.icns');
  } else {
    return path.join(iconDir, 'icon.png');
  }
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.get('http://localhost:8000/', (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForBackend(maxWaitTime = 30000) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < maxWaitTime) {
    const isHealthy = await checkBackendHealth();
    if (isHealthy) {
      console.log('Backend is ready!');
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  return false;
}

async function startBackend() {
  const isDev = !app.isPackaged;
  
  // 确定后端可执行文件路径
  let backendExe;
  if (isDev) {
    // 开发模式：使用 Python 直接运行
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const backendMain = path.join(__dirname, '../backend/main.py');
    
    console.log('Starting backend in dev mode:', backendMain);
    
    backendProcess = spawn(pythonCmd, [backendMain], {
      cwd: path.join(__dirname, '../backend'),
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });
  } else {
    // 生产模式：使用 PyInstaller 打包的可执行文件
    const backendDir = path.join(process.resourcesPath, 'backend');
    const exeName = process.platform === 'win32' ? 'main.exe' : 'main';
    backendExe = path.join(backendDir, exeName);
    
    console.log('Starting backend in production mode:', backendExe);
    
    backendProcess = spawn(backendExe, [], {
      cwd: backendDir,
      env: { ...process.env }
    });
  }

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
      `无法启动后端服务：${error.message}`
    );
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend process exited with code ${code}`);
  });

  // 等待后端就绪
  const isReady = await waitForBackend();
  
  if (!isReady) {
    dialog.showErrorBox(
      '后端启动超时',
      '后端服务启动超时（30秒），请检查日志或重新启动应用。'
    );
    app.quit();
  }
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
  
  await startBackend();
  createWindow();
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

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});
