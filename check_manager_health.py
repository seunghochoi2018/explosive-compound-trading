import psutil
import time

print("="*70)
print("UNIFIED MANAGER HEALTH CHECK")
print("="*70)

# 1. Ollama memory check
print("\n1. Ollama Memory Status (should be < 12GB)")
for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
    try:
        if 'ollama.exe' in proc.info['name'].lower():
            memory_gb = proc.info['memory_info'].rss / 1024 / 1024 / 1024
            status = "OK" if memory_gb < 12 else "ALERT"
            print(f"   PID {proc.info['pid']}: {memory_gb:.2f}GB [{status}]")
    except:
        pass

# 2. Python processes
print("\n2. Python Processes (should be 3: manager + 2 traders)")
python_count = 0
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'python' in proc.info['name'].lower():
            python_count += 1
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else 'N/A'
            if 'unified' in cmdline:
                print(f"   Manager: PID {proc.info['pid']}")
            elif 'eth' in cmdline.lower():
                print(f"   ETH Trader: PID {proc.info['pid']}")
            elif 'kis' in cmdline.lower():
                print(f"   KIS Trader: PID {proc.info['pid']}")
    except:
        pass

print(f"\n   Total: {python_count} Python processes")
if python_count == 3:
    print("   Status: OK (1 manager + 2 traders)")
else:
    print(f"   Status: WARNING (expected 3, got {python_count})")

# 3. Ollama ports
print("\n3. Ollama Ports (11434, 11435, 11436)")
import socket
for port in [11434, 11435, 11436]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    status = "OPEN" if result == 0 else "CLOSED"
    print(f"   Port {port}: {status}")

print("\n" + "="*70)
print("HEALTH CHECK COMPLETE")
print("="*70)
