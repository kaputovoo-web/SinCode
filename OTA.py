#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STM32 OTA 上位机（Python + tkinter + pyserial）

功能：
  1. 串口调试终端：收发、HEX 显示、HEX 发送
  2. OTA 升级：触发升级(AA 55 99) → 选 bin → 发固件帧(AA 55 target size data crc)
  3. App 切换：AA 55 01(切App1) / AA 55 02(切App2)

依赖：pip install pyserial        （tkinter 是 Python 自带）
用法：python ota_tool.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import serial
import serial.tools.list_ports
import threading
import queue
import time
import os

# ================= CRC16（与 boot 完全一致：CCITT 0x1021，初值 0xFFFF） =================
def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if (crc & 0x8000) else (crc << 1) & 0xFFFF
    return crc

# ================= 固件帧 =================
# 帧格式: AA 55 target size_lo size_hi  data...  crc_lo crc_hi
def build_firmware_frame(data: bytes, target: int) -> bytes:
    return (bytes([0xAA, 0x55, target])
            + len(data).to_bytes(2, 'little')
            + data
            + crc16(data).to_bytes(2, 'little'))

class OtaTool:
    def __init__(self, root):
        self.root = root
        root.title("STM32 OTA 上位机")
        root.geometry("800x600")
        self.ser = None
        self.rx_q = queue.Queue()
        self._build_ui()
        root.after(80, self._poll_queue)     # 定时把串口收到的数据刷进界面
        self._refresh_ports()

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=6)
        top.pack(fill=tk.X)

        ttk.Label(top, text="串口:").pack(side=tk.LEFT)
        self.port_cb = ttk.Combobox(top, width=12)
        self.port_cb.pack(side=tk.LEFT, padx=(4, 2))
        ttk.Button(top, text="刷新", width=5, command=self._refresh_ports).pack(side=tk.LEFT)

        ttk.Label(top, text="波特率:").pack(side=tk.LEFT, padx=(12, 2))
        self.baud_cb = ttk.Combobox(top, width=9, values=["9600", "115200", "230400", "460800", "921600"])
        self.baud_cb.set("115200")
        self.baud_cb.pack(side=tk.LEFT)

        self.connect_btn = ttk.Button(top, text="连接", command=self._toggle_connect)
        self.connect_btn.pack(side=tk.LEFT, padx=(14, 0))
        self.status_lbl = ttk.Label(top, text="● 未连接", foreground="gray")
        self.status_lbl.pack(side=tk.LEFT, padx=8)

        # ---- 串口终端 ----
        term_frame = ttk.LabelFrame(self.root, text="串口终端（boot 调试输出 / 收发）", padding=6)
        term_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))
        self.term = scrolledtext.ScrolledText(term_frame, state=tk.DISABLED, font=("Consolas", 9))
        self.term.pack(fill=tk.BOTH, expand=True)

        tbar = ttk.Frame(term_frame)
        tbar.pack(fill=tk.X, pady=(2, 0))
        self.hexview_var = tk.BooleanVar()
        ttk.Checkbutton(tbar, text="HEX 显示", variable=self.hexview_var).pack(side=tk.LEFT)
        ttk.Button(tbar, text="清空", command=self._clear_term).pack(side=tk.LEFT, padx=8)

        # ---- 发送行 ----
        tx = ttk.Frame(self.root, padding=6)
        tx.pack(fill=tk.X)
        self.tx_entry = ttk.Entry(tx)
        self.tx_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.hexsend_var = tk.BooleanVar()
        ttk.Checkbutton(tx, text="HEX 发送", variable=self.hexsend_var).pack(side=tk.LEFT, padx=4)
        ttk.Button(tx, text="发送", command=self._send_tx).pack(side=tk.LEFT)
        ttk.Button(tx, text="升级命令 AA 55 99", command=self._send_trigger).pack(side=tk.LEFT, padx=(10, 0))

        # ---- OTA 区 ----
        ota = ttk.LabelFrame(self.root, text="OTA 固件升级", padding=6)
        ota.pack(fill=tk.X, padx=6, pady=6)

        r1 = ttk.Frame(ota); r1.pack(fill=tk.X)
        ttk.Label(r1, text="固件:").pack(side=tk.LEFT)
        self.bin_entry = ttk.Entry(r1)
        self.bin_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(r1, text="选择...", command=self._pick_bin).pack(side=tk.LEFT)

        r2 = ttk.Frame(ota); r2.pack(fill=tk.X, pady=(4, 0))
        self.target_var = tk.IntVar(value=2)
        ttk.Radiobutton(r2, text="目标 App1", variable=self.target_var, value=1).pack(side=tk.LEFT)
        ttk.Radiobutton(r2, text="目标 App2", variable=self.target_var, value=2).pack(side=tk.LEFT, padx=(14, 0))
        ttk.Button(r2, text="切换 → App1", command=lambda: self._send_cmd([0xAA, 0x55, 0x01])).pack(side=tk.LEFT, padx=(30, 0))
        ttk.Button(r2, text="切换 → App2", command=lambda: self._send_cmd([0xAA, 0x55, 0x02])).pack(side=tk.LEFT, padx=(6, 0))

        r3 = ttk.Frame(ota); r3.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(r3, text="触发升级", command=self._send_trigger).pack(side=tk.LEFT)
        ttk.Button(r3, text="发送固件帧", command=self._send_firmware).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(r3, text="一键升级（触发→等1.5s→发帧）", command=self._one_click_upgrade).pack(side=tk.LEFT, padx=(8, 0))

    # ---------------- 串口 ----------------
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_cb['values'] = ports
        if ports and not self.port_cb.get():
            self.port_cb.set(ports[0])

    def _toggle_connect(self):
        if self.ser and self.ser.is_open:
            self._close_serial()
            return
        port = self.port_cb.get().strip()
        baud = int(self.baud_cb.get())
        if not port:
            self._log("[错误] 请选择串口")
            return
        try:
            self.ser = serial.Serial(port, baud, timeout=0.05)
            self.status_lbl.config(text="● 已连接", foreground="green")
            self.connect_btn.config(text="断开")
            self._log(f"[已连接] {port} @ {baud}")
            threading.Thread(target=self._rx_thread, daemon=True).start()
        except Exception as e:
            self._log(f"[错误] 打开串口失败: {e}")

    def _close_serial(self):
        if self.ser:
            try: self.ser.close()
            except Exception: pass
            self.ser = None
        self.status_lbl.config(text="● 未连接", foreground="gray")
        self.connect_btn.config(text="连接")

    def _rx_thread(self):
        while self.ser and self.ser.is_open:
            try:
                n = self.ser.in_waiting
                if n:
                    self.rx_q.put(self.ser.read(n))
                else:
                    time.sleep(0.02)
            except Exception:
                break

    def _poll_queue(self):
        try:
            while True:
                data = self.rx_q.get_nowait()
                self._log_bytes(data)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_queue)

    def _send_bytes(self, data: bytes):
        if not (self.ser and self.ser.is_open):
            self._log("[错误] 串口未连接")
            return False
        try:
            self.ser.write(data)
            self._log(f"[TX] {data.hex(' ').upper()}" if len(data) < 64 else f"[TX] {len(data)} 字节")
            return True
        except Exception as e:
            self._log(f"[错误] 发送失败: {e}")
            return False

    # ---------------- 终端 ----------------
    def _log(self, text: str):
        self.term.config(state=tk.NORMAL)
        self.term.insert(tk.END, text + "\n")
        self.term.see(tk.END)
        self.term.config(state=tk.DISABLED)

    def _log_bytes(self, data: bytes):
        if self.hexview_var.get():
            self._log(data.hex(" ").upper())
        else:
            try:
                text = data.decode("ascii", errors="replace")
            except Exception:
                text = data.hex(" ")
            self.term.config(state=tk.NORMAL)
            self.term.insert(tk.END, text)
            self.term.see(tk.END)
            self.term.config(state=tk.DISABLED)

    def _clear_term(self):
        self.term.config(state=tk.NORMAL)
        self.term.delete("1.0", tk.END)
        self.term.config(state=tk.DISABLED)

    def _send_tx(self):
        s = self.tx_entry.get()
        if not s:
            return
        if self.hexsend_var.get():
            try:
                data = bytes.fromhex(s.replace(" ", "").replace(",", "").replace("0x", ""))
            except ValueError:
                self._log("[错误] HEX 格式不对")
                return
        else:
            data = s.encode("ascii", errors="replace")
        self._send_bytes(data)

    # ---------------- 命令 / OTA ----------------
    def _send_cmd(self, cmds):
        self._send_bytes(bytes(cmds))

    def _send_trigger(self):
        self._send_bytes(bytes([0xAA, 0x55, 0x99]))   # App 收到 → 复位 → boot 进升级模式

    def _pick_bin(self):
        path = filedialog.askopenfilename(filetypes=[("bin 固件", "*.bin"), ("所有文件", "*.*")])
        if path:
            self.bin_entry.delete(0, tk.END)
            self.bin_entry.insert(0, path)

    def _send_firmware(self):
        path = self.bin_entry.get().strip()
        if not os.path.isfile(path):
            self._log("[错误] 请先选择固件 .bin")
            return
        data = open(path, "rb").read()
        target = self.target_var.get()
        frame = build_firmware_frame(data, target)
        self._log(f"[固件] {os.path.basename(path)} {len(data)}B  CRC=0x{crc16(data):04X}  → App{target}")
        # 分小块发送，防 boot 环形缓冲溢出
        for i in range(0, len(frame), 128):
            if not self._send_bytes(frame[i:i + 128]):
                return
            time.sleep(0.005)

    def _one_click_upgrade(self):
        def worker():
            self._send_trigger()
            time.sleep(1.5)          # 等 App 复位 → boot 进升级模式
            self._send_firmware()
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    OtaTool(root)
    root.mainloop()
