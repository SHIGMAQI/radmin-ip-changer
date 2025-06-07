import tkinter as tk
from tkinter import scrolledtext
import subprocess
import platform
import winreg
import ctypes
import sys
import time
import os

SERVICE_NAME = "RvControlSvc"  # Internal Windows service name for Radmin VPN Control Service
SERVICE_EXE = "RvControlSvc.exe"  # Service executable to force kill if needed
GUI_EXE = r"C:\Program Files (x86)\Radmin VPN\RadminVPN.exe"  # GUI executable to launch after restart

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}"', None, 1
        )
        sys.exit()

def delete_radmin_keys(logbox):
    arch = platform.machine()
    # Registry path for 64-bit or 32-bit systems
    path = r"SOFTWARE\WOW6432Node\Famatech\RadminVPN\1.0" if arch.endswith("64") else r"SOFTWARE\Famatech\RadminVPN\1.0"
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_ALL_ACCESS)
        for name in ["IPv4", "IPv6", "RID"]:
            try:
                winreg.DeleteValue(key, name)
                logbox.insert(tk.END, f"[+] Deleted key: {name}\n")
            except FileNotFoundError:
                logbox.insert(tk.END, f"[-] Key not found: {name}\n")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logbox.insert(tk.END, f"[!] Registry error: {e}\n")
        return False

def stop_service(logbox, service_name):
    logbox.insert(tk.END, f"[*] Stopping service: {service_name}...\n")
    subprocess.run(["sc", "stop", service_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for i in range(20):
        result = subprocess.run(["sc", "query", service_name], capture_output=True, text=True)
        if "STOPPED" in result.stdout:
            logbox.insert(tk.END, f"[+] Service stopped: {service_name}\n")
            return True
        time.sleep(0.5)

    logbox.insert(tk.END, "[!] Timeout. Attempting force kill...\n")
    taskkill = subprocess.run(["taskkill", "/F", "/IM", SERVICE_EXE], capture_output=True, text=True)
    if "SUCCESS" in taskkill.stdout.upper() or "TERMINATED" in taskkill.stdout.upper():
        logbox.insert(tk.END, f"[+] {SERVICE_EXE} force-killed.\n")
        return True
    else:
        logbox.insert(tk.END, f"[!] taskkill failed: {taskkill.stdout}\n")
        return False

def start_service(logbox, service_name):
    logbox.insert(tk.END, f"[*] Starting service: {service_name}...\n")
    result = subprocess.run(["sc", "start", service_name], capture_output=True, text=True)
    if "RUNNING" in result.stdout or "START_PENDING" in result.stdout:
        logbox.insert(tk.END, f"[+] Service started: {service_name}\n")
    else:
        logbox.insert(tk.END, f"[!] Failed to start: {result.stdout}\n")

def relaunch_radminvpn(logbox):
    if os.path.exists(GUI_EXE):
        try:
            subprocess.Popen([GUI_EXE])
            logbox.insert(tk.END, "[+] RadminVPN GUI launched.\n")
        except Exception as e:
            logbox.insert(tk.END, f"[!] Failed to launch RadminVPN: {e}\n")
    else:
        logbox.insert(tk.END, "[!] RadminVPN.exe not found.\n")

def do_full_reset():
    logbox.delete(1.0, tk.END)
    logbox.insert(tk.END, "=== Resetting Radmin VPN IP ===\n")
    if delete_radmin_keys(logbox):
        if stop_service(logbox, SERVICE_NAME):
            time.sleep(1)
            start_service(logbox, SERVICE_NAME)
            relaunch_radminvpn(logbox)
            logbox.insert(tk.END, "\n[✓] Done! New IP should be applied.\n")
        else:
            logbox.insert(tk.END, "[!] Could not stop service.\n")
    else:
        logbox.insert(tk.END, "[!] Could not delete registry keys.\n")

run_as_admin()

root = tk.Tk()
root.title("Radmin VPN IP Reset Tool")
root.geometry("520x430")
root.resizable(False, False)

tk.Label(root, text="Radmin VPN IP Reset Tool", font=("Segoe UI", 16)).pack(pady=10)
tk.Button(root, text="Reset Radmin VPN IP", font=("Segoe UI", 13), command=do_full_reset).pack(pady=5)
logbox = scrolledtext.ScrolledText(root, width=64, height=20, font=("Consolas", 10))
logbox.pack(padx=10, pady=10)

root.mainloop()
