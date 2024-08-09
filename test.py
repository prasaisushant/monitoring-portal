import paramiko

def test_ssh_connection(ip, port, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port=port, username=username, password=password)
        print(f"Successfully connected to {ip}:{port}")
        ssh.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

test_ssh_connection("192.168.237.134", 22, "abc", "abc")
