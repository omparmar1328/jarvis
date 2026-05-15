import { app, BrowserWindow, dialog } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn, execSync } from 'child_process';
import fs from 'fs';
import http from 'http';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let pythonProcess = null;
let server = null;
const SERVER_PORT = 30001; 
const LOG_FILE = path.join(app.getPath('documents'), 'bait_launch_log.txt');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line);
  console.log(msg);
}

// Clear log on start
try { fs.writeFileSync(LOG_FILE, '--- BAIT LAUNCH LOG ---\n'); } catch(e) {}

function startInternalServer() {
  log('Starting Internal UI Server...');
  const baseDir = app.isPackaged ? path.join(app.getAppPath(), 'ui-build') : path.join(__dirname, 'ui-build');
  log(`UI Source Directory: ${baseDir}`);
  
  if (!fs.existsSync(baseDir)) {
    log(`CRITICAL ERROR: UI Directory missing at ${baseDir}`);
    return;
  }

  server = http.createServer((req, res) => {
    let urlPath = req.url === '/' ? '/index.html' : req.url;
    // Strip query strings for file lookup
    urlPath = urlPath.split('?')[0];
    
    let filePath = path.join(baseDir, urlPath);
    log(`UI Request: ${req.url} -> ${filePath}`);

    fs.readFile(filePath, (err, data) => {
      if (err) {
        log(`404: ${filePath}`);
        res.statusCode = 404;
        res.end('Not Found');
        return;
      }
      
      const ext = path.extname(filePath);
      const mimeTypes = {
        '.html': 'text/html',
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.svg': 'image/svg+xml',
        '.png': 'image/png',
        '.json': 'application/json'
      };
      res.setHeader('Content-Type', mimeTypes[ext] || 'application/octet-stream');
      res.end(data);
    });
  });

  server.listen(SERVER_PORT, '127.0.0.1', () => {
    log(`Internal UI Server active at http://127.0.0.1:${SERVER_PORT}`);
  });
}

function startPythonBackend() {
  log('Initializing Python Brain...');
  const isDev = !app.isPackaged;
  const rootDir = path.join(__dirname, '..');
  
  // Feature: Kill any existing process on port 8000 to prevent 'Address already in use'
  try {
    log('Checking for existing processes on port 8000...');
    execSync('lsof -ti:8000 | xargs kill -9', { stdio: 'ignore' });
    log('Port 8000 cleared.');
  } catch (e) {
    // No process found, which is fine
  }

  if (isDev) {
    const pythonScript = path.join(rootDir, 'server.py');
    log(`Dev Mode: Launching Brain via python3 ${pythonScript}`);
    
    try {
      pythonProcess = spawn('python3', [pythonScript], {
        stdio: 'inherit',
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });
      log('Brain script started successfully.');
    } catch (e) {
      log(`EXCEPTION starting Python: ${e.message}`);
    }
    return;
  }

  // Packaged production path
  let serverPath = path.join(process.resourcesPath, 'server', 'server');
  if (!fs.existsSync(serverPath)) {
    const altPath = path.join(process.resourcesPath, 'server');
    if (fs.existsSync(altPath)) serverPath = altPath;
  }

  log(`Resolved Brain Path: ${serverPath}`);

  try {
    if (fs.existsSync(serverPath)) {
      execSync(`chmod +x "${serverPath}"`);
      pythonProcess = spawn(serverPath, [], {
        stdio: 'inherit',
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
      });
      log('Brain binary spawned successfully.');
    } else {
      log('ERROR: Brain binary missing!');
    }
  } catch (e) {
    log(`EXCEPTION starting Brain: ${e.message}`);
  }
}

function createWindow() {
  log('Creating Application Window...');
  const win = new BrowserWindow({
    width: 1300,
    height: 900,
    titleBarStyle: 'hiddenInset',
    vibrancy: 'under-window',
    visualEffectState: 'active',
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      devTools: true,
      webSecurity: false,
    },
  });

  if (!app.isPackaged) {
    win.loadURL('http://localhost:5173');
  } else {
    const targetUrl = `http://127.0.0.1:${SERVER_PORT}/index.html`;
    log(`Loading URL: ${targetUrl}`);
    win.loadURL(targetUrl).catch(err => {
      log(`LOAD ERROR: ${err.message}`);
      dialog.showErrorBox('Launch Error', `Failed to load UI: ${err.message}\nCheck ${LOG_FILE} for details.`);
    });
  }

  win.webContents.openDevTools();
}

app.whenReady().then(() => {
  log('App Ready.');
  if (app.isPackaged) startInternalServer();
  startPythonBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  log('App Closing.');
  if (pythonProcess) pythonProcess.kill();
  if (server) server.close();
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) pythonProcess.kill();
  if (server) server.close();
});
