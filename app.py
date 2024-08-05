from flask import Flask, request, render_template, redirect, url_for
import paramiko
import psutil
import pandas as pd
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from sklearn.linear_model import LinearRegression
import numpy as np

app = Flask(__name__)

# Database setup
DATABASE_URI = 'sqlite:///monitoring.db'
engine = create_engine(DATABASE_URI)

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_server', methods=['POST'])
def add_server():
    ip = request.form['ip']
    username = request.form['username']
    password = request.form['password']
    port = request.form['port']
    interval = int(request.form['interval'])
    
    # Store server details in the database
    server = {'ip': ip, 'username': username, 'password': password, 'port': port, 'interval': interval}
    df = pd.DataFrame([server])
    df.to_sql('servers', engine, if_exists='append', index=False)

    # Schedule data collection
    scheduler.add_job(collect_data, 'interval', minutes=interval, args=[server])

    return redirect(url_for('index'))

def collect_data(server):
    ip = server['ip']
    username = server['username']
    password = server['password']
    port = server['port']

    # Connect to the server via SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, port=int(port))

    # Gather system information
    stdin, stdout, stderr = ssh.exec_command('top -bn1 | grep "Cpu(s)"')
    cpu_usage = stdout.read().decode('utf-8').strip().split()[1]

    stdin, stdout, stderr = ssh.exec_command('free -m')
    memory_usage = stdout.read().decode('utf-8').strip().split()[8]

    stdin, stdout, stderr = ssh.exec_command('df -h | grep "^/dev"')
    storage_usage = stdout.read().decode('utf-8').strip().split()[4].replace('%', '')

    stdin, stdout, stderr = ssh.exec_command('ifstat 1 1 | tail -1')
    network_stats = stdout.read().decode('utf-8').strip().split()

    # Close SSH connection
    ssh.close()

    # Store data in the database
    data = {
        'timestamp': pd.Timestamp.now(),
        'cpu_usage': float(cpu_usage),
        'memory_usage': float(memory_usage),
        'storage_usage': float(storage_usage),
        'network_stats': float(network_stats[0]),
        'ip': ip
    }
    df = pd.DataFrame([data])
    df.to_sql('monitoring_data', engine, if_exists='append', index=False)

@app.route('/visualize')
def visualize():
    # Query the database for the collected data
    df = pd.read_sql('monitoring_data', engine)
    
    # Generate visualizations using matplotlib or seaborn
    fig, ax = plt.subplots(2, 2, figsize=(15, 10))
    
    sns.lineplot(x='timestamp', y='cpu_usage', data=df, ax=ax[0, 0])
    ax[0, 0].set_title('CPU Usage Over Time')

    sns.lineplot(x='timestamp', y='memory_usage', data=df, ax=ax[0, 1])
    ax[0, 1].set_title('Memory Usage Over Time')

    sns.lineplot(x='timestamp', y='storage_usage', data=df, ax=ax[1, 0])
    ax[1, 0].set_title('Storage Usage Over Time')

    sns.lineplot(x='timestamp', y='network_stats', data=df, ax=ax[1, 1])
    ax[1, 1].set_title('Network Usage Over Time')
    
    # Save the figure to a BytesIO object
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    
    return render_template('visualize.html', image_base64=image_base64)

@app.route('/predict')
def predict():
    df = pd.read_sql('monitoring_data', engine)

    # Prepare the data for machine learning
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].map(pd.Timestamp.timestamp)
    
    X = df[['timestamp']]
    y_cpu = df['cpu_usage']
    y_memory = df['memory_usage']
    
    model_cpu = LinearRegression().fit(X, y_cpu)
    model_memory = LinearRegression().fit(X, y_memory)
    
    # Make predictions
    future_timestamp = pd.Timestamp.now() + pd.Timedelta(days=1)
    future_timestamp = future_timestamp.timestamp()
    
    predicted_cpu = model_cpu.predict([[future_timestamp]])
    predicted_memory = model_memory.predict([[future_timestamp]])
    
    return render_template('predict.html', cpu=predicted_cpu[0], memory=predicted_memory[0])

if __name__ == '__main__':
    app.run(debug=True)
