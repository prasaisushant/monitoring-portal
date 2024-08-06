from flask import Flask, render_template, request, redirect, url_for
import paramiko
import re

app = Flask(__name__)

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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ip = request.form["ip"]
        username = request.form["username"]
        password = request.form["password"]
        port = int(request.form["port"])

        stats = get_server_stats(ip, username, password, port)
        return render_template("result.html", stats=stats)
    
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

