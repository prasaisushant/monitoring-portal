from flask import Flask, render_template, request, redirect, url_for, jsonify
import paramiko
import time
from threading import Thread, Event

app = Flask(__name__)

# Global variables to store data and manage intervals
server_data = []
intervals = []  # List to store intervals
stop_thread_event = Event()

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
        node_stats = []
        for line in lines:
            if line:
                parts = line.split()
                node_stats.append({
                    'node': parts[0],
                    'cpu_usage': parts[1],
                    'cpu_percentage': parts[2],
                    'memory_usage': parts[3],
                    'memory_percentage': parts[4]
                })
        return {
            'node_stats': node_stats,
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
    global stop_thread, intervals
    if request.method == "POST":
        ip = request.form["ip"]
        username = request.form["username"]
        password = request.form["password"]
        port = int(request.form["port"])
        new_interval = int(request.form["interval"])
        action = request.form["action"]

        if action == "get_stats":
            # Stop existing thread if running
            stop_thread = True
            # Ensure the intervals list is not empty before using max
            if intervals:
                time.sleep(max(intervals) + 1)  # Wait for the longest interval
            else:
                time.sleep(1)  # Default wait time if intervals is empty
            # Start new background thread
            stop_thread = False
            intervals = [new_interval]
            thread = Thread(target=background_task, args=(ip, username, password, port))
            thread.start()
            
            return redirect(url_for('result', ip=ip, username=username, port=port))
        
        elif action == "open_terminal":
            return redirect(url_for('terminal', ip=ip, username=username, password=password, port=port))

    return render_template("index.html")




@app.route("/result")
def result():
    return render_template("result.html")

@app.route("/stats")
def stats():
    global server_data
    return jsonify(server_data)

@app.route("/update_interval", methods=["POST"])
def update_interval():
    global intervals
    new_interval = int(request.form["interval"])
    intervals = [new_interval]
    return jsonify({"status": "success", "new_interval": new_interval})

@app.route("/terminal")
def terminal():
    ip = request.args.get("ip", "")
    username = request.args.get("username", "")
    password = request.args.get("password", "")
    port = request.args.get("port", "22")
    return render_template("terminal.html", ip=ip, username=username, password=password, port=port)

@app.route("/execute", methods=["POST"])
def execute():
    data = request.json
    ip = data.get("ip")
    username = data.get("username")
    password = data.get("password")
    port = int(data.get("port", 22))
    command = data.get("command")
    print(f"Executing command: {command} on {ip}:{port}")
    result = execute_command(ip, username, password, port, command)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
