"""Run with python gui.py. A local viewer; solution.py stays independent."""

import importlib
import multiprocessing as mp
import time
import tkinter as tk
from tkinter import ttk

from sokoban import PROBLEMS, SokobanState, sokoban_goal_state
from validation import validate_solution


def solve_worker(connection, map_index, budget):
    """Isolate the solver so stopping a search also releases its memory."""
    try:
        import solution
        importlib.reload(solution)
        initial = PROBLEMS[map_index]
        started = time.monotonic()
        final = solution.solve(initial, timebound=budget)
        elapsed = time.monotonic() - started
        if final is False:
            connection.send((False, elapsed, 'Chưa tìm được lời giải.'))
            return
        valid, detail = validate_solution(PROBLEMS[map_index], final)
        if not valid:
            raise ValueError(detail)
        path = []
        while final is not None:
            path.append((final.robots, final.boxes, final.action, final.gval))
            final = final.parent
        connection.send((list(reversed(path)), elapsed, ''))
    except Exception as exc:
        connection.send((False, 0, f'{type(exc).__name__}: {exc}'))
    finally:
        connection.close()


class Viewer:
    def __init__(self, root):
        self.root = root
        root.title('Sokoban — Solution viewer')
        root.geometry('850x720')
        root.minsize(700, 580)
        self.process = self.connection = None
        self.playing = False
        self.frame = 0
        self.path = []
        self.map_var = tk.StringVar(value='Map 1')
        self.budget = tk.StringVar(value='10')
        self.speed = tk.StringVar(value='250')
        self.status = tk.StringVar()
        self.step_info = tk.StringVar()
        self.manual = tk.BooleanVar(value=False)
        self.robot = tk.StringVar(value='0')
        self.saved_replay = None

        bar = ttk.Frame(root, padding=12)
        bar.pack(fill='x')
        ttk.Button(bar, text='◀ Map', command=lambda: self.change_map(-1)).pack(side='left')
        self.selector = ttk.Combobox(bar, textvariable=self.map_var, state='readonly',
                                     values=[f'Map {i+1}' for i in range(len(PROBLEMS))], width=10)
        self.selector.pack(side='left', padx=6)
        self.selector.bind('<<ComboboxSelected>>', lambda event: self.load_map())
        ttk.Button(bar, text='Map ▶', command=lambda: self.change_map(1)).pack(side='left')
        ttk.Label(bar, text='Giới hạn (giây):').pack(side='left', padx=(18, 4))
        ttk.Entry(bar, textvariable=self.budget, width=6).pack(side='left')
        ttk.Button(bar, text='Giải', command=self.solve).pack(side='left', padx=6)
        ttk.Button(bar, text='Dừng giải', command=self.cancel).pack(side='left')

        ttk.Label(root, textvariable=self.status, padding=(12, 0), wraplength=800).pack(fill='x')
        self.canvas = tk.Canvas(root, bg='#eef2f6', highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=12, pady=12)
        self.canvas.bind('<Configure>', lambda event: self.draw())
        ttk.Label(root, text='Tường: xám  •  Đích: vòng xanh  •  Thùng: nâu/xanh khi đúng đích  •  Robot: số',
                  anchor='center').pack(fill='x')
        controls = ttk.Frame(root, padding=12)
        controls.pack(fill='x')
        for label, command in [('Về đầu', self.restart), ('◀ Bước', lambda: self.step(-1)),
                               ('Phát / Tạm dừng', self.toggle), ('Bước ▶', lambda: self.step(1))]:
            ttk.Button(controls, text=label, command=command).pack(side='left', padx=3)
        ttk.Label(controls, text='ms/bước:').pack(side='left', padx=(12, 4))
        ttk.Combobox(controls, textvariable=self.speed, values=['100', '250', '500', '1000'],
                     state='readonly', width=6).pack(side='left')
        manual_bar = ttk.Frame(root, padding=(12, 0, 12, 8))
        manual_bar.pack(fill='x')
        ttk.Checkbutton(manual_bar, text='Tự điều khiển từ bước hiện tại', variable=self.manual,
                        command=self.set_manual).pack(side='left')
        ttk.Label(manual_bar, text='Robot:').pack(side='left', padx=(12, 4))
        self.robot_selector = ttk.Combobox(manual_bar, textvariable=self.robot,
                                          state='readonly', width=4)
        self.robot_selector.pack(side='left')
        self.robot_selector.bind('<<ComboboxSelected>>', lambda event: self.canvas.focus_set())
        ttk.Button(manual_bar, text='Quay lại lời giải', command=self.restore_replay).pack(side='left', padx=8)
        ttk.Label(manual_bar, text='Di chuyển: ↑ ↓ ← → • Hoàn tác: ◀ Bước').pack(side='left')
        ttk.Label(root, textvariable=self.step_info, padding=(12, 0, 12, 12)).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW', self.close)
        for key in ('Up', 'Right', 'Down', 'Left'):
            root.bind(f'<{key}>', self.on_arrow)
        self.canvas.bind('<Button-1>', lambda event: self.canvas.focus_set())
        self.load_map()
        root.after(100, self.poll)
        root.after(250, self.tick)

    def change_map(self, delta):
        self.selector.current((self.selector.current() + delta) % len(PROBLEMS))
        self.load_map()

    def load_map(self):
        self.stop_worker()
        self.playing = False
        self.frame = 0
        self.manual.set(False)
        self.saved_replay = None
        self.initial = PROBLEMS[self.selector.current()]
        s = self.initial
        self.robot_selector.configure(values=[str(i) for i in range(len(s.robots))])
        self.robot.set('0')
        self.path = [(s.robots, s.boxes, s.action, s.gval)]
        self.status.set(f'{self.map_var.get()} • {s.width}×{s.height} • '
                        f'{len(s.boxes)} thùng • {len(s.robots)} robot. Nhấn Giải để bắt đầu.')
        self.draw()

    def solve(self):
        try:
            budget = float(self.budget.get())
            if not 0 < budget <= 3600:
                raise ValueError
        except ValueError:
            self.status.set('Nhập giới hạn thời gian lớn hơn 0 và không quá 3600 giây.')
            return
        self.load_map()
        self.connection, sender = mp.Pipe(duplex=False)
        self.process = mp.Process(target=solve_worker,
                                  args=(sender, self.selector.current(), budget), daemon=True)
        self.process.start()
        sender.close()
        self.started = time.monotonic()
        self.deadline = self.started + budget + 2
        self.status.set('Đang giải…')

    def stop_worker(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join()
            self.process.close()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def cancel(self):
        if self.process is not None:
            self.stop_worker()
            self.status.set('Đã dừng tìm kiếm. Có thể giải lại hoặc chuyển map.')

    def poll(self):
        if self.process is not None:
            if self.connection.poll():
                try:
                    path, elapsed, error = self.connection.recv()
                except (EOFError, OSError):
                    path, elapsed, error = False, 0, 'Tiến trình giải kết thúc bất thường.'
                self.stop_worker()
                if path is False:
                    self.status.set(f'{error} Thời gian: {elapsed:.3f}s')
                else:
                    self.path = path
                    self.frame = 0
                    pushes = sum(a[1] != b[1] for a, b in zip(path, path[1:]))
                    self.status.set(f'Đã giải: {len(path)-1} bước • {pushes} lần đẩy • '
                                    f'{elapsed:.3f}s. Nhấn Phát để xem từ đầu.')
                    self.draw()
            elif not self.process.is_alive():
                self.stop_worker()
                self.status.set('Tiến trình giải kết thúc mà không trả kết quả.')
            elif time.monotonic() >= self.deadline:
                self.stop_worker()
                self.status.set('Đã hết giới hạn thời gian; dừng tiến trình giải.')
            else:
                self.status.set(f'Đang giải… {time.monotonic()-self.started:.1f}s')
        self.root.after(100, self.poll)

    def restart(self):
        self.playing = False
        self.frame = 0
        self.draw()

    def set_manual(self):
        self.playing = False
        if self.manual.get():
            if self.process is not None:
                self.cancel()
            self.saved_replay = (self.path, self.frame, self.status.get())
            self.path = self.path[:self.frame+1]
            self.status.set('Tự điều khiển: chọn robot rồi dùng phím mũi tên. Có thể lùi bước để thử hướng khác.')
            self.canvas.focus_set()
            self.draw()
        else:
            self.restore_replay()

    def restore_replay(self):
        self.playing = False
        self.manual.set(False)
        if self.saved_replay is not None:
            self.path, self.frame, status = self.saved_replay
            self.saved_replay = None
            self.status.set(status)
        self.draw()

    def on_arrow(self, event):
        if isinstance(event.widget, (ttk.Entry, ttk.Combobox, tk.Entry)):
            return
        if self.manual.get():
            self.move_robot(event.keysym)
        elif event.keysym in ('Left', 'Right'):
            self.step(-1 if event.keysym == 'Left' else 1)
        return 'break'

    def move_robot(self, direction):
        if not self.manual.get():
            return
        self.playing = False
        robots, boxes, action, cost = self.path[self.frame]
        s = self.initial
        current = SokobanState(action, cost, None, s.width, s.height,
                               robots, boxes, s.storage, s.obstacles)
        wanted = f'{self.robot.get()} {direction.lower()}'
        child = next((item for item in current.successors() if item.action.lower() == wanted), None)
        if child is None:
            self.status.set('Không thể đi hướng này: gặp tường, robot, thùng hoặc biên bản đồ.')
            return
        self.path = self.path[:self.frame+1]
        self.path.append((child.robots, child.boxes, child.action, child.gval))
        self.frame += 1
        self.status.set('Đã tới đích!' if sokoban_goal_state(child) else
                        'Tự điều khiển • Dùng ◀ Bước để hoàn tác, sau đó thử hướng khác.')
        self.draw()

    def step(self, delta):
        self.playing = False
        self.frame = max(0, min(len(self.path)-1, self.frame + delta))
        self.draw()

    def toggle(self):
        if len(self.path) < 2:
            return
        if self.frame == len(self.path)-1:
            self.frame = 0
            self.draw()
        self.playing = not self.playing

    def tick(self):
        if self.playing:
            self.frame = min(self.frame+1, len(self.path)-1)
            self.draw()
            if self.frame == len(self.path)-1:
                self.playing = False
        self.root.after(int(self.speed.get()), self.tick)

    def draw(self):
        if not self.path:
            return
        c, s = self.canvas, self.initial
        c.delete('all')
        tile = max(1, min((c.winfo_width()-30)/(s.width+2),
                          (c.winfo_height()-30)/(s.height+2), 64))
        ox = (c.winfo_width() - (s.width+2)*tile)/2
        oy = (c.winfo_height() - (s.height+2)*tile)/2
        robots, boxes, action, cost = self.path[self.frame]
        for y in range(-1, s.height+1):
            for x in range(-1, s.width+1):
                p = (x, y)
                left, top = ox+(x+1)*tile, oy+(y+1)*tile
                wall = x in (-1, s.width) or y in (-1, s.height) or p in s.obstacles
                c.create_rectangle(left, top, left+tile, top+tile,
                                   fill='#475569' if wall else '#ffffff', outline='#cbd5e1')
                if p in s.storage:
                    c.create_oval(left+tile*.3, top+tile*.3, left+tile*.7, top+tile*.7,
                                  outline='#16a34a', width=3)
                if p in boxes:
                    c.create_rectangle(left+tile*.14, top+tile*.14, left+tile*.86, top+tile*.86,
                                       fill='#22c55e' if p in s.storage else '#c68b48', outline='#76502a', width=2)
                if p in robots:
                    c.create_oval(left+tile*.15, top+tile*.15, left+tile*.85, top+tile*.85,
                                  fill='#2563eb', outline=('#f59e0b' if self.manual.get() and
                                  robots.index(p) == int(self.robot.get()) else '#1e40af'), width=3)
                    c.create_text(left+tile/2, top+tile/2, text=str(robots.index(p)),
                                  fill='white', font=('Segoe UI', max(7, int(tile*.26)), 'bold'))
        self.step_info.set(f'Bước {self.frame}/{len(self.path)-1} • g = {cost} • Hành động: {action}')

    def close(self):
        self.stop_worker()
        self.root.destroy()


if __name__ == '__main__':
    mp.freeze_support()
    root = tk.Tk()
    Viewer(root)
    root.mainloop()
