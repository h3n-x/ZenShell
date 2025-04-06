import os
import threading
import asyncio
import subprocess
from flask import Flask, render_template_string, jsonify
import time
import psutil
import datetime

app = Flask(__name__)

# Variables globales para almacenar información del bot
bot_process = None
start_time = None
restart_count = 0

# HTML para la página principal
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ZenShell Bot - Panel de Control</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #23272A;
            color: #FFFFFF;
            font-family: 'Poppins', sans-serif;
        }
        .navbar {
            background-color: #2C2F33;
        }
        .card {
            background-color: #2C2F33;
            border: none;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        .card-header {
            background-color: #7289DA;
            color: white;
            font-weight: bold;
        }
        .btn-primary {
            background-color: #7289DA;
            border-color: #7289DA;
        }
        .btn-danger {
            background-color: #F04747;
            border-color: #F04747;
        }
        .status-badge {
            font-size: 1.2rem;
            padding: 8px 15px;
        }
        .status-online {
            background-color: #43B581;
        }
        .status-offline {
            background-color: #F04747;
        }
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">
                <img src="https://cdn.discordapp.com/avatars/1353078906189647912/a_1234567890.png" alt="ZenShell Logo" width="30" height="30" class="d-inline-block align-text-top me-2">
                ZenShell Bot - Panel de Control
            </a>
        </div>
    </nav>

    <div class="container">
        <div class="row">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-header">
                        Estado del Bot
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-4">
                            <h5>Estado actual:</h5>
                            <span class="badge status-badge {{ 'status-online' if status == 'online' else 'status-offline' }}">
                                {{ status.upper() }}
                            </span>
                        </div>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Tiempo de actividad:</strong> {{ uptime }}</p>
                                <p><strong>Reinicios:</strong> {{ restart_count }}</p>
                                <p><strong>PID:</strong> {{ pid }}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Uso de CPU:</strong> {{ cpu_usage }}%</p>
                                <p><strong>Uso de memoria:</strong> {{ memory_usage }} MB</p>
                                <p><strong>Última actualización:</strong> {{ last_update }}</p>
                            </div>
                        </div>
                        <div class="d-flex justify-content-center mt-3">
                            <form method="post" action="/restart" class="me-2">
                                <button type="submit" class="btn btn-primary">Reiniciar Bot</button>
                            </form>
                            <form method="post" action="/stop" class="ms-2">
                                <button type="submit" class="btn btn-danger">Detener Bot</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card">
                    <div class="card-header">
                        Logs Recientes
                    </div>
                    <div class="card-body">
                        <div class="logs-container" style="height: 300px; overflow-y: auto;">
                            <pre class="text-light">{{ logs }}</pre>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <a href="/" class="btn btn-primary refresh-btn">
        ↻
    </a>

    <script>
        // Auto-refresh cada 30 segundos
        setTimeout(function() {
            window.location.reload();
        }, 30000);
    </script>
</body>
</html>
"""

def get_bot_logs(lines=20):
    """Obtiene las últimas líneas del log del bot"""
    try:
        log_path = "bot.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                logs = f.readlines()
                return "".join(logs[-lines:])
        return "No hay logs disponibles"
    except Exception as e:
        return f"Error al leer logs: {str(e)}"

def format_uptime(seconds):
    """Formatea el tiempo de actividad en un formato legible"""
    if seconds < 60:
        return f"{seconds} segundos"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minutos"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} horas, {minutes} minutos"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days} días, {hours} horas"

def start_bot():
    """Inicia el proceso del bot"""
    global bot_process, start_time
    
    # Configurar la redirección de salida a un archivo de log
    log_file = open("bot.log", "a")
    
    # Iniciar el proceso del bot
    bot_process = subprocess.Popen(
        ["python", "main.py"],
        stdout=log_file,
        stderr=log_file,
        text=True
    )
    
    start_time = time.time()
    print(f"Bot iniciado con PID: {bot_process.pid}")

def check_bot_status():
    """Verifica el estado del bot y lo reinicia si es necesario"""
    global bot_process, start_time, restart_count
    
    while True:
        if bot_process is None:
            # Si el proceso no existe, iniciar el bot
            start_bot()
            restart_count += 1
        elif bot_process.poll() is not None:
            # Si el proceso ha terminado, reiniciar el bot
            print(f"Bot terminado con código: {bot_process.returncode}. Reiniciando...")
            start_bot()
            restart_count += 1
            
        # Esperar antes de la siguiente verificación
        time.sleep(30)

@app.route('/')
def index():
    """Página principal del panel de control"""
    global bot_process, start_time, restart_count
    
    # Obtener información del proceso
    status = "offline"
    pid = "N/A"
    cpu_usage = "0.0"
    memory_usage = "0.0"
    uptime = "0 segundos"
    
    if bot_process is not None and bot_process.poll() is None:
        status = "online"
        pid = bot_process.pid
        
        try:
            process = psutil.Process(pid)
            cpu_usage = f"{process.cpu_percent(interval=0.1):.1f}"
            memory_usage = f"{process.memory_info().rss / (1024 * 1024):.1f}"
            
            if start_time:
                uptime_seconds = int(time.time() - start_time)
                uptime = format_uptime(uptime_seconds)
        except:
            pass
    
    # Obtener logs recientes
    logs = get_bot_logs(30)
    
    # Renderizar la plantilla
    return render_template_string(
        DASHBOARD_HTML,
        status=status,
        pid=pid,
        cpu_usage=cpu_usage,
        memory_usage=memory_usage,
        uptime=uptime,
        restart_count=restart_count,
        logs=logs,
        last_update=datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    )

@app.route('/restart', methods=['POST'])
def restart_bot():
    """Reinicia el bot"""
    global bot_process, restart_count
    
    if bot_process is not None:
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        except:
            bot_process.kill()
        
        bot_process = None
        restart_count += 1
    
    start_bot()
    return jsonify({"status": "success", "message": "Bot reiniciado correctamente"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    """Detiene el bot"""
    global bot_process
    
    if bot_process is not None:
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        except:
            bot_process.kill()
        
        bot_process = None
    
    return jsonify({"status": "success", "message": "Bot detenido correctamente"})

@app.route('/api/status')
def api_status():
    """API para obtener el estado del bot"""
    global bot_process, start_time, restart_count
    
    status = "offline"
    pid = None
    cpu_usage = 0
    memory_usage = 0
    uptime_seconds = 0
    
    if bot_process is not None and bot_process.poll() is None:
        status = "online"
        pid = bot_process.pid
        
        try:
            process = psutil.Process(pid)
            cpu_usage = process.cpu_percent(interval=0.1)
            memory_usage = process.memory_info().rss / (1024 * 1024)
            
            if start_time:
                uptime_seconds = int(time.time() - start_time)
        except:
            pass
    
    return jsonify({
        "status": status,
        "pid": pid,
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": format_uptime(uptime_seconds),
        "restart_count": restart_count,
        "last_update": datetime.datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Iniciar el hilo de monitoreo del bot
    monitor_thread = threading.Thread(target=check_bot_status, daemon=True)
    monitor_thread.start()
    
    # Iniciar la aplicación Flask
    app.run(host='0.0.0.0', port=5000, debug=False)
