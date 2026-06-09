import json
import os
import time

STATE_FILE = 'task_emulation.json'
LIFETIME_FILE = 'node_stats.txt'

def read_lifetime():
    try:
        if os.path.exists(LIFETIME_FILE):
            with open(LIFETIME_FILE, 'r', encoding='utf-8') as f:
                return int(f.read().strip())
    except Exception:
        pass
    return 0

def write_state(active_tasks, lifetime_tasks):
    payload = {
        'active_tasks': active_tasks,
        'session_tasks': active_tasks,
        'lifetime_tasks': lifetime_tasks,
        'updated_at': time.time()
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    with open(LIFETIME_FILE, 'w', encoding='utf-8') as f:
        f.write(str(lifetime_tasks))

def main():
    lifetime = read_lifetime()
    active = 3
    while True:
        active = 3 + (int(time.time()) % 4)
        lifetime += 1
        write_state(active, lifetime)
        time.sleep(5)

if __name__ == '__main__':
    main()
