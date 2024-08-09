from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import paramiko
import time
from threading import Thread, Event
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a real secret key

# Global variables to store data and manage intervals
server_data = []
intervals = []  # List to store intervals
stop_thread_event = Event()

def init_db():
    conn = sqlite3.connect('D:\\monitoring-portal\\server_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node TEXT,
            cpu_usage TEXT,
            cpu_percentage TEXT,
            memory_usage TEXT,
            memory_percentage TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def store_stats(node, cpu_usage, cpu_percentage, memory_usage, memory_percentage):
    conn = sqlite3.connect('D:\\monitoring-portal\\server_stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO stats (node, cpu_usage, cpu_percentage, memory_usage, memory_percentage)
        VALUES (?, ?, ?, ?, ?)
    ''', (node, cpu_usage, cpu_percentage, memory_usage, memory_percentage))
    conn.commit()
    conn.close()

def get_kubernetes_node_stats(ip, username, password, port):
    try:
        # Establish SSH connection to the Kubernetes master node
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=username, password=password)
        # Execute kubectl command to get node stats
        stdin, stdout, stderr = ssh.exec_command("kubectl top nodes --no-headers")
        output = stdout.read().decode().strip()
        ssh.close()
        # Parse the output into a structured format
        lines = output.split("\n")
        for line in lines:
            if line:
                parts = line.split()
                store_stats(parts[0], parts[1], parts[2], parts[3], parts[4])
        return {
            'node_stats': [dict(zip(['node', 'cpu_usage', 'cpu_percentage', 'memory_usage', 'memory_percentage'], parts)) for parts in [line.split() for line in lines if line]],
            'timestamp': time.time()
        }
    except Exception as e:
        return {'error': str(e)}

def background_task(ip, username, password, port):
    global server_data, stop_thread_event, intervals
    while not stop_thread_event.is_set():
        for interval in intervals:
            stats = get_kubernetes_node_stats(ip, username, password, port)
            server_data.append(stats)
            # Keep only the last 100 data points
            if len(server_data) > 100:
                server_data = server_data[-100:]
            time.sleep(interval)
            if stop_thread_event.is_set():
                break

def execute_command(ip, username, password, port, command):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=username, password=password)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()
        if error:
            return {"error": error}
        return {"output": output}
    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ip = request.form["ip"]
        username = request.form["username"]
        password = request.form["password"]
        port = int(request.form["port"])
        new_interval = int(request.form["interval"])
        
        # Store in session
        session['ip'] = ip
        session['username'] = username
        session['password'] = password
        session['port'] = port
        
        stop_thread_event.set()
        stop_thread_event.wait()
        stop_thread_event.clear()
        intervals = [new_interval]
        thread = Thread(target=background_task, args=(ip, username, password, port))
        thread.start()
        return redirect(url_for('result'))
    return render_template("index.html")

@app.route("/result")
def result():
    return render_template("result.html")

@app.route("/terminal")
def terminal():
    ip = session.get("ip")
    username = session.get("username")
    password = session.get("password")
    port = session.get("port")
    
    # Check if the required session data is available
    if not ip or not username or not password or not port:
        return redirect(url_for('index'))  # Redirect back to the index if session data is missing

    return render_template("terminal.html", ip=ip, username=username, password=password, port=port)

@app.route("/stats")
def stats():
    conn = sqlite3.connect('D:\\monitoring-portal\\server_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stats ORDER BY timestamp DESC LIMIT 100')
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

@app.route("/data")
def data():
    conn = sqlite3.connect('D:\\monitoring-portal\\server_stats.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM stats ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

@app.route("/update_interval", methods=["POST"])
def update_interval():
    global intervals
    new_interval = int(request.form["interval"])
    intervals = [new_interval]
    return jsonify({"status": "success", "new_interval": new_interval})

@app.route("/execute", methods=["POST"])
def execute():
    data = request.json
    ip = data.get("ip")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    command = data.get("command")
    result = execute_command(ip, username, password, port, command)
    return jsonify(result)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
