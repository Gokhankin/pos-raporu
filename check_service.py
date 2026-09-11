
import os, subprocess

print("--- Systemd services related to pos ---")
res = subprocess.run(["systemctl", "list-units", "--type=service", "--all", "*pos*"], capture_output=True, text=True)
print(res.stdout)

print("--- Check processes for pos_backend ---")
res2 = subprocess.run(["ps", "-ef"], capture_output=True, text=True)
for line in res2.stdout.splitlines():
    if "pos" in line.lower() or "5070" in line:
        print(line)
