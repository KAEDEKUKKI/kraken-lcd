"""
硬體感測收集模組 (monitor.collector)
負責收集 CPU 使用率與溫度、記憶體使用量與百分比、以及 NVIDIA GPU 使用率與溫度。
"""

import subprocess
import psutil


def get_cpu_info(sample_interval: float = 0.2) -> dict:
    cpu_percent = psutil.cpu_percent(interval=sample_interval)
    cpu_freq = psutil.cpu_freq()
    cpu_temp = None
    try:
        temps = psutil.sensors_temperatures()
        for name in ["k10temp", "coretemp", "zenpower", "nct6798", "nct6775", "cpu_thermal", "acpitz"]:
            if name in temps:
                entries = temps[name]
                if entries:
                    valid_temps = [e.current for e in entries if e.current is not None]
                    if valid_temps:
                        cpu_temp = max(valid_temps)
                        break
        if cpu_temp is None and temps:
            for entries in temps.values():
                valid_temps = [e.current for e in entries if e.current is not None]
                if valid_temps:
                    cpu_temp = max(valid_temps)
                    break
    except Exception:
        pass
    return {
        "usage": cpu_percent,
        "freq_mhz": cpu_freq.current if cpu_freq else None,
        "temp": cpu_temp,
    }


def get_memory_info() -> dict:
    mem = psutil.virtual_memory()
    return {
        "total_gb": mem.total / (1024**3),
        "used_gb": mem.used / (1024**3),
        "percent": mem.percent,
    }


def get_gpu_info() -> dict:
    gpu_info = {"usage": None, "temp": None, "vram_percent": None}
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 4:
                gpu_info["usage"] = float(parts[0])
                gpu_info["temp"] = float(parts[1])
                mem_used = float(parts[2])
                mem_total = float(parts[3])
                gpu_info["vram_percent"] = (
                    (mem_used / mem_total * 100.0) if mem_total > 0 else None
                )
    except Exception:
        pass
    return gpu_info


def collect_system_metrics(include_gpu: bool = True, sample_interval: float = 0.2) -> dict:
    return {
        "cpu": get_cpu_info(sample_interval=sample_interval),
        "mem": get_memory_info(),
        "gpu": get_gpu_info() if include_gpu else {"usage": None, "temp": None, "vram_percent": None},
    }
