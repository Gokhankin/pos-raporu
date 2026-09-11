
import os, subprocess

for pid in [1612, 2683821]:
    res = subprocess.run(["pwdx", str(pid)], capture_output=True, text=True)
    print(res.stdout)
    res2 = subprocess.run(["ls", "-l", f"/proc/{pid}/cwd"], capture_output=True, text=True)
    print(res2.stdout)
    res3 = subprocess.run(["ls", "-l", f"/proc/{pid}/exe"], capture_output=True, text=True)
    print(res3.stdout)

# Also check auto-start scripts in home or crontab or autostart
print("--- Crontab ---")
res_cron = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
print(res_cron.stdout)

print("--- Autostart desktop entries ---")
res_auto = subprocess.run(["ls", "-la", "/home/society/.config/autostart"], capture_output=True, text=True)
print(res_auto.stdout)
