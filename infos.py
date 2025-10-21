#!/usr/bin/env python3
import psutil
import platform
import subprocess
from datetime import timedelta
import time


def get_system_info():
    info = {}

    # Nom et version du système
    info["system"] = platform.system()
    info["release"] = platform.release()
    info["kernel"] = platform.version()

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = psutil.time.time() - boot_time
    info["uptime"] = str(timedelta(seconds=int(uptime_seconds)))

    # CPU
    info["cpu_usage_percent"] = psutil.cpu_percent(interval=1)
    info["cpu_cores"] = psutil.cpu_count(logical=True)

    # Températures CPU
    temps = psutil.sensors_temperatures()
    if "coretemp" in temps:
        cpu_temps = [t.current for t in temps["coretemp"]]
        info["cpu_temp_avg"] = round(sum(cpu_temps) / len(cpu_temps), 1)
    else:
        info["cpu_temp_avg"] = None  # Certains systèmes n'exposent pas les capteurs

    # Mémoire
    mem = psutil.virtual_memory()
    info["ram_used_percent"] = mem.percent
    info["ram_total_gb"] = round(mem.total / (1024**3), 2)

    # Batterie
    try:
        battery = psutil.sensors_battery()
        if battery:
            info["battery_percent"] = battery.percent
            info["power_plugged"] = battery.power_plugged
        else:
            info["battery_percent"] = None
    except Exception:
        info["battery_percent"] = None

    # Utilisation disque
    disk = psutil.disk_usage("/")
    info["disk_used_percent"] = disk.percent

    # Consommation en Watts (Linux uniquement)
    try:
        with open("/sys/class/powercap/intel-rapl:0/energy_uj") as f:
            energy1 = int(f.read().strip())
        time.sleep(1.0)
        with open("/sys/class/powercap/intel-rapl:0/energy_uj") as f:
            energy2 = int(f.read().strip())
        power_watts = (energy2 - energy1) / (1.0 * 1_000_000)  # µJ → J → W
        info["power (Watts)"] = round(power_watts, 2)
    except Exception as e:
        info["power (Watts)"] = e

    return info


if __name__ == "__main__":
    infos = get_system_info()
    print("=== System Info ===")
    for k, v in infos.items():
        print(f"{k:20s}: {v}")
