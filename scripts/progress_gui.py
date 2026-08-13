"""下载进度条 GUI（Tkinter 桌面窗口）

线程安全：Tk 主循环必须在主线程。launch() 在主线程启动 GUI，
下载在后台线程跑，update() 经 queue 传进度，GUI 线程 after() 轮询；
close() 用 after() 调度到 Tk 线程销毁窗口。
"""

import queue
import threading
import tkinter as tk
from tkinter import ttk


class DownloadProgress:
    """Tkinter 下载进度条窗口（任意线程可 update/close）"""

    def __init__(self, title="ASF 下载进度"):

        self.total_files = 0
        self.done_files = 0
        self.cur_filename = ""
        self.root = None

        self._stop = threading.Event()
        self._launched = False
        self._q = queue.Queue()

    def launch(self):
        """启动 GUI（必须在主线程）；无显示环境时静默降级"""

        try:
            self.root = tk.Tk()
        except Exception:
            # headless/server 无显示：标记未启动即可
            self._launched = False
            return
        self.root.title("ASF Sentinel-1 下载进度")
        self.root.geometry("560x230")

        self.root.resizable(False, False)
        try:
            self.root.attributes("-topmost", True)
        except Exception:
            pass

        # 当前文件信息
        tk.Label(self.root, text="当前文件：", font=("Microsoft YaHei", 10)).pack(
            anchor="w", padx=16, pady=(14, 2)
        )
        self.lbl_file = tk.Label(
            self.root,
            text="准备中...",
            font=("Microsoft YaHei", 9),
            fg="#333333",
            anchor="w",
            width=70,
        )
        self.lbl_file.pack(anchor="w", padx=30)

        # 当前文件进度条
        tk.Label(self.root, text="当前文件：", font=("Microsoft YaHei", 9)).pack(
            anchor="w", padx=16, pady=(8, 2)
        )

        self.cur_bar = ttk.Progressbar(self.root, length=520, mode="determinate")
        self.cur_bar.pack(padx=16)
        self.lbl_cur_pct = tk.Label(
            self.root, text="0.0%", font=("Microsoft YaHei", 9), fg="#1A3C8B"
        )
        self.lbl_cur_pct.pack(anchor="e", padx=20)

        # 总进度条
        tk.Label(self.root, text="总进度：", font=("Microsoft YaHei", 9)).pack(
            anchor="w", padx=16, pady=(12, 2)
        )
        self.total_bar = ttk.Progressbar(self.root, length=520, mode="determinate")

        self.total_bar.pack(padx=16)
        self.lbl_total_pct = tk.Label(
            self.root, text="0/0 (0.0%)", font=("Microsoft YaHei", 9), fg="#1A3C8B"
        )
        self.lbl_total_pct.pack(anchor="e", padx=20)

        self._launched = True
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll)
        self.root.mainloop()

    def _on_close(self):
        self._stop.set()
        self.root.destroy()

    def _poll(self):
        """queue 里取更新刷新 GUI（避免跨线程直接操作 Tk）"""
        if self._stop.is_set():
            return
        try:
            while True:
                msg = self._q.get_nowait()
                kind = msg.get("kind")
                if kind == "progress":
                    self.cur_bar["value"] = msg["cur_pct"] * 100
                    self.lbl_cur_pct.config(text=f"{msg['cur_pct'] * 100:.1f}%")
                    self.total_bar["value"] = msg["tot_pct"] * 100
                    self.lbl_total_pct.config(
                        text=f"{msg['done']}/{msg['total']} ({msg['tot_pct'] * 100:.1f}%)"
                    )
                    fname = msg["filename"]
                    self.lbl_file.config(text=fname[:66] + ("..." if len(fname) > 66 else ""))
                elif kind == "done":
                    self.lbl_cur_pct.config(text="100.0%")
                    self.cur_bar["value"] = 100
        except queue.Empty:
            pass
        if not self._stop.is_set():
            self.root.after(100, self._poll)

    # ---------- 任意线程可调用的接口 ----------
    def set_total(self, n):
        self.total_files = n
        self.done_files = 0

    def update(self, filename, cur_bytes, total_bytes, done_files, total_files):
        """更新进度（线程安全，经 queue 传给 GUI 线程）"""
        self.done_files = done_files
        self.total_files = total_files
        cur_pct = (cur_bytes / total_bytes) if total_bytes else 0.0
        tot_pct = ((done_files + cur_pct) / total_files) if total_files else 0.0
        self._q.put(
            {
                "kind": "progress",
                "cur_pct": min(cur_pct, 1.0),
                "tot_pct": min(tot_pct, 1.0),
                "done": done_files,
                "total": total_files,
                "filename": filename or "",
            }
        )

    def file_done(self):
        """单个文件完成（线程安全）"""
        self.done_files += 1
        self._q.put({"kind": "done"})

    def close(self):
        """关窗（线程安全：调度到 Tk 线程执行）"""

        self._stop.set()
        if self._launched and self.root:
            try:
                self.root.after(0, self.root.destroy)
            except Exception:
                pass
