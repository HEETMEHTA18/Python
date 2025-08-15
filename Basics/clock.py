import time
from datetime import datetime

print("⏰ Digital Clock (Press Ctrl+C to stop)")

try:
    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print(f"\r{current_time}", end="")
        time.sleep(1)
except KeyboardInterrupt:
    print("\n👋 Clock stopped.")
