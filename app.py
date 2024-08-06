from flask import Flask, render_template, request, redirect, url_for, jsonify
import paramiko
import re
from threading import Thread
import time

app = Flask(__name__)

# Global variables to store data and manage intervals
server_data = []
update_interval = 5  # Default interval in seconds
stop_thread = False

def get_server_stats(ip, username, password, port):
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=username, password=password)

        # Retrieve CPU usage from /proc/stat
        stdin, stdout, stderr = ssh.exec_command("cat /proc/stat | grep '^cpu '")
        cpu_line = stdout.read().decode().strip()
        cpu_times = list(map(int, cpu_line.split()[1:]))
        idle_time = cpu_times[3]
        total_time = sum(cpu_times)
        used_cpu = 100.0 * (1 - idle_time / total_time)

        # Retrieve Memory usage from /proc/meminfo
        stdin, stdout, stderr = ssh.exec_command("cat /proc/meminfo")
        mem_info = stdout.read().decode().strip().split('\n')
        mem_total = int(mem_info[0].split()[1]) // 1024  # Convert kB to MB
        mem_free = int(mem_info[1].split()[1]) // 1024  # Convert kB to MB
        mem_available = int(mem_info[2].split()[1]) // 1024  # Convert kB to MB
        mem_used = mem_total - mem_available

        # Retrieve Storage usage from df
        stdin, stdout, stderr = ssh.exec_command("df -h --output=source,size,used,pcent | grep '^/'")
        storage_lines = stdout.read().decode().strip().split('\n')
        storage_usage = []
        for line in storage_lines:
            parts = re.split(r'\s+', line)
            filesystem, total, used, used_percent = parts[0], parts[1], parts[2], parts[3]
            storage_usage.append({
                'filesystem': filesystem,
                'total': total,
                'used': used,
                'used_percent': used_percent
            })

        ssh.close()

        return {
            'cpu_usage': used_cpu,
            'mem_total': mem_total,
            'mem_used': mem_used,
            'storage_usage': storage_usage
        }

    except Exception as e:
        return {'error': str(e)}




def background_task(ip, username, password, port):
    global server_data, stop_thread
    while not stop_thread:
        stats = get_server_stats(ip, username, password, port)
        stats['timestamp'] = time.time()
        server_data.append(stats)
        # Keep only the last 100 data points
        if len(server_data) > 100:
            server_data = server_data[-100:]
        time.sleep(update_interval)

@app.route("/", methods=["GET", "POST"])
def index():
    global update_interval, stop_thread
    if request.method == "POST":
        ip = request.form["ip"]
        username = request.form["username"]
        password = request.form["password"]
        port = int(request.form["port"])
        update_interval = int(request.form["interval"])
        
        # Stop existing thread if running
        stop_thread = True
        time.sleep(update_interval + 1)
        
        # Start new background thread
        stop_thread = False
        thread = Thread(target=background_task, args=(ip, username, password, port))
        thread.start()
        
        return redirect(url_for('result'))
    
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
    global update_interval
    new_interval = int(request.form["interval"])
    update_interval = new_interval
    return jsonify({"status": "success", "new_interval": new_interval})

if __name__ == "__main__":
    app.run(debug=True)