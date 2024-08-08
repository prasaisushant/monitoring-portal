from flask import Flask, request, render_template, jsonify
import paramiko
import json
import time
import threading

app = Flask(__name__)

# Store user input globally
user_input = {
    'ip': '',
    'username': '',
    'password': '',
    'port': 22,
    'interval': 5
}

# For storing stats
stats_data = {'cpu': [], 'memory': []}

def fetch_stats():
    global stats_data
    while True:
        if user_input['ip']:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(user_input['ip'], port=user_input['port'], username=user_input['username'], password=user_input['password'])
                stdin, stdout, stderr = ssh.exec_command("kubectl top nodes")
                output = stdout.read().decode()

                # Process output to get CPU and memory usage
                lines = output.splitlines()[1:]
                for line in lines:
                    parts = line.split()
                    cpu = float(parts[1].replace('%', ''))
                    memory = float(parts[2].replace('%', ''))
                    stats_data['cpu'].append(cpu)
                    stats_data['memory'].append(memory)

                ssh.close()
            except Exception as e:
                print(f"Error: {e}")

        time.sleep(user_input['interval'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        global user_input
        user_input = {
            'ip': request.form['ip'],
            'username': request.form['username'],
            'password': request.form['password'],
            'port': int(request.form['port']),
            'interval': int(request.form['interval'])
        }

        # Start fetching stats in a separate thread
        threading.Thread(target=fetch_stats, daemon=True).start()

    return render_template('index.html')

@app.route('/stats')
def stats():
    global stats_data
    return jsonify(stats_data)

if __name__ == '__main__':
    app.run(debug=True)
