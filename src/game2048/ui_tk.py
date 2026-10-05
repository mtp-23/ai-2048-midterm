"""Responsive Tkinter UI for humans and AI agents.

Tkinter normally ships with Python, so the viewer intentionally has no
third-party GUI dependency. Agent computation is
performed on a worker thread; even a slow search must not freeze the window.
"""

from __future__ import annotations

import importlib
import importlib.util
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Any, Callable

from .engine import Game
from .types import Move

BG, PANEL, PANEL_LIGHT = "#0f172a", "#172033", "#202b40"
TEXT, MUTED, ACCENT, ACCENT_ACTIVE = "#f8fafc", "#94a3b8", "#38bdf8", "#0ea5e9"
BOARD_BG, EMPTY = "#273449", "#334155"
LIMITED_MODE = "Giới hạn tổng thời gian"
UNLIMITED_MODE = "Chạy đến game over"
UNLIMITED_DECISION_HINT_MS = 50.0

TILE_COLORS: dict[int, tuple[str, str]] = {
    0: (EMPTY, MUTED), 2: ("#e2e8f0", "#334155"), 4: ("#cbd5e1", "#334155"),
    8: ("#fdba74", "#431407"), 16: ("#fb923c", "#fff7ed"),
    32: ("#f97316", "#fff7ed"), 64: ("#ef4444", "#fef2f2"),
    128: ("#fde047", "#422006"), 256: ("#facc15", "#422006"),
    512: ("#eab308", "#fffbeb"), 1024: ("#a3e635", "#1a2e05"),
    2048: ("#22c55e", "#f0fdf4"), 4096: ("#06b6d4", "#ecfeff"),
    8192: ("#8b5cf6", "#f5f3ff"), 16384: ("#d946ef", "#fdf4ff"),
}

def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError):
        return False


def _available_agent_specs() -> dict[str, str | None]:
    specs: dict[str, str | None] = {
        "Human": None,
        "Boss 0 · Random": "student.examples.random_agent:Agent",
        "Student agent": "student.agent:Agent",
    }
    private_bosses = (
        ("Boss 1 · Local", "instructor.bosses.boss1_greedy:Agent"),
        ("Boss 2 · Local", "instructor.bosses.boss2_expectimax:Agent"),
        ("Boss 3 · Local", "instructor.bosses.boss3_optimized_expectimax:Agent"),
        ("Boss 4 · Local", "instructor.bosses.boss4_omega:Agent"),
    )
    for label, spec in private_bosses:
        if _module_available(spec.partition(":")[0]):
            specs[label] = spec
    return specs


AGENT_SPECS = _available_agent_specs()


def _rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
                  radius: float, **kwargs: Any) -> int:
    points = (
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def _load_agent(spec: str) -> Any:
    module_name, separator, class_name = spec.partition(":")
    if not separator:
        raise ValueError("Agent phải có dạng package.module:ClassName")
    return getattr(importlib.import_module(module_name), class_name)()


@dataclass(slots=True)
class _Decision:
    generation: int
    move: Move | int | None
    elapsed_ms: float
    error: BaseException | None = None


class GameUI:
    """Interactive 2048 viewer with a non-blocking AI runner."""

    def __init__(self, seed: int = 0, agent: Any | None = None,
                 agent_spec: str | None = None, total_time_sec: float = 60.0) -> None:
        self.root = tk.Tk()
        self.root.title("2048 · AI Arena")
        self.root.configure(bg=BG)
        self.root.geometry("940x650")
        self.root.minsize(820, 590)

        self.seed_var = tk.StringVar(value=str(seed))
        self.budget_var = tk.StringVar(value=f"{total_time_sec:g}")
        self.time_mode_var = tk.StringVar(value=LIMITED_MODE)
        self.delay_var = tk.IntVar(value=35)
        self.agent_choice = tk.StringVar(value="Human")
        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.score_var = tk.StringVar(value="0")
        self.best_var = tk.StringVar(value="0")
        self.moves_var = tk.StringVar(value="0")
        self.time_var = tk.StringVar(value=f"{total_time_sec:.1f}s")

        self._external_agent = agent
        if agent_spec:
            label = next((name for name, spec in AGENT_SPECS.items() if spec == agent_spec), agent_spec)
            if label not in AGENT_SPECS:
                AGENT_SPECS[label] = agent_spec
            self.agent_choice.set(label)
        elif agent is not None:
            label = f"Custom · {getattr(agent, 'name', type(agent).__name__)}"
            AGENT_SPECS[label] = "__external__"
            self.agent_choice.set(label)

        self.game = Game(seed)
        self.agent: Any | None = None
        self.running = False
        self.thinking = False
        self.total_budget_ms: float | None = max(0.0, total_time_sec * 1000.0)
        self.used_time_ms = 0.0
        self._generation = 0
        self._decisions: list[_Decision] = []
        self._decision_lock = threading.Lock()

        self._configure_styles()
        self._build()
        self._bind()
        self._select_agent(show_error=False)
        self._render()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(20, self._tick)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Arena.TCombobox", fieldbackground=PANEL_LIGHT, background=PANEL_LIGHT,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=PANEL_LIGHT, padding=8)
        style.map("Arena.TCombobox", fieldbackground=[("readonly", PANEL_LIGHT)],
                  selectbackground=[("readonly", PANEL_LIGHT)], selectforeground=[("readonly", TEXT)])
        style.configure("Arena.Horizontal.TScale", background=PANEL, troughcolor=PANEL_LIGHT,
                        bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG, padx=24, pady=20)
        shell.pack(fill="both", expand=True)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_columnconfigure(1, minsize=290)
        shell.grid_rowconfigure(1, weight=1)

        title = tk.Frame(shell, bg=BG)
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        tk.Label(title, text="2048", bg=BG, fg=TEXT, font=("Segoe UI", 30, "bold")).pack(side="left")
        tk.Label(title, text="AI ARENA", bg=ACCENT, fg=BG, padx=9, pady=4,
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=12, pady=(8, 0))
        tk.Label(title, text="← ↑ → ↓  hoặc  WASD", bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="right", pady=(10, 0))

        board_card = tk.Frame(shell, bg=BOARD_BG, padx=12, pady=12)
        board_card.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
        self.canvas = tk.Canvas(board_card, bg=BOARD_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw_board())

        side = tk.Frame(shell, bg=PANEL, padx=18, pady=18)
        side.grid(row=1, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        stats = tk.Frame(side, bg=PANEL)
        stats.grid(row=0, column=0, sticky="ew")
        for col, (caption, variable) in enumerate((("SCORE", self.score_var), ("BEST TILE", self.best_var))):
            card = tk.Frame(stats, bg=PANEL_LIGHT, padx=12, pady=9)
            card.grid(row=0, column=col, sticky="ew", padx=(0, 5) if col == 0 else (5, 0))
            stats.grid_columnconfigure(col, weight=1)
            tk.Label(card, text=caption, bg=PANEL_LIGHT, fg=MUTED,
                     font=("Segoe UI", 8, "bold")).pack()
            tk.Label(card, textvariable=variable, bg=PANEL_LIGHT, fg=TEXT,
                     font=("Segoe UI", 18, "bold")).pack()

        self._section_label(side, "CHẾ ĐỘ", 1, (19, 5))
        self.agent_box = ttk.Combobox(side, textvariable=self.agent_choice, values=list(AGENT_SPECS),
                                      state="readonly", style="Arena.TCombobox")
        self.agent_box.grid(row=2, column=0, sticky="ew")
        self.agent_box.bind("<<ComboboxSelected>>", lambda _event: self.restart())

        form = tk.Frame(side, bg=PANEL)
        form.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        form.grid_columnconfigure((0, 1), weight=1)
        self._field(form, "SEED", self.seed_var, 0)
        self.budget_entry = self._field(form, "TOTAL SEC", self.budget_var, 1)

        self._section_label(side, "ĐIỀU KIỆN KẾT THÚC", 4, (14, 4))
        self.time_mode_box = ttk.Combobox(
            side,
            textvariable=self.time_mode_var,
            values=(LIMITED_MODE, UNLIMITED_MODE),
            state="readonly",
            style="Arena.TCombobox",
        )
        self.time_mode_box.grid(row=5, column=0, sticky="ew")
        self.time_mode_box.bind("<<ComboboxSelected>>", lambda _event: self.restart())

        self._section_label(side, "TỐC ĐỘ HIỂN THỊ", 6, (14, 2))
        ttk.Scale(side, from_=0, to=500, variable=self.delay_var, orient="horizontal",
                  style="Arena.Horizontal.TScale").grid(row=7, column=0, sticky="ew")
        speed_row = tk.Frame(side, bg=PANEL)
        speed_row.grid(row=8, column=0, sticky="ew")
        tk.Label(speed_row, text="Nhanh", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(speed_row, text="Chậm", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="right")

        details = tk.Frame(side, bg=PANEL_LIGHT, padx=12, pady=10)
        details.grid(row=9, column=0, sticky="ew", pady=(14, 0))
        self._detail(details, "Nước đi", self.moves_var, 0)
        self._detail(details, "Thời gian còn", self.time_var, 1)

        controls = tk.Frame(side, bg=PANEL)
        controls.grid(row=10, column=0, sticky="ew", pady=(14, 0))
        controls.grid_columnconfigure((0, 1), weight=1)
        self.start_button = self._button(controls, "▶  CHẠY", self.toggle, primary=True)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._button(controls, "↻  VÁN MỚI", self.restart).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        tk.Label(side, textvariable=self.status_var, bg=PANEL, fg=ACCENT,
                 wraplength=250, justify="left", anchor="w",
                 font=("Segoe UI", 10, "bold")).grid(row=11, column=0, sticky="ew", pady=(13, 0))
        tk.Label(side, text="Space: chạy/dừng  ·  R: ván mới  ·  Esc: thoát",
                 bg=PANEL, fg=MUTED, wraplength=250, justify="left",
                 font=("Segoe UI", 8)).grid(row=12, column=0, sticky="ew", pady=(7, 0))

    @staticmethod
    def _section_label(parent: tk.Widget, text: str, row: int, pady: tuple[int, int]) -> None:
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=row, column=0, sticky="w", pady=pady)

    @staticmethod
    def _field(parent: tk.Widget, label: str, variable: tk.StringVar, column: int) -> tk.Entry:
        frame = tk.Frame(parent, bg=PANEL)
        frame.grid(row=0, column=column, sticky="ew", padx=(0, 5) if column == 0 else (5, 0))
        tk.Label(frame, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        entry = tk.Entry(frame, textvariable=variable, bg=PANEL_LIGHT, fg=TEXT,
                         disabledbackground="#111827", disabledforeground=MUTED,
                         insertbackground=TEXT, relief="flat", highlightthickness=1,
                         highlightbackground=PANEL_LIGHT, highlightcolor=ACCENT,
                         font=("Segoe UI", 11), justify="center")
        entry.pack(fill="x", ipady=7, pady=(4, 0))
        return entry

    @staticmethod
    def _detail(parent: tk.Widget, caption: str, variable: tk.StringVar, row: int) -> None:
        tk.Label(parent, text=caption, bg=PANEL_LIGHT, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=2)
        tk.Label(parent, textvariable=variable, bg=PANEL_LIGHT, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).grid(row=row, column=1, sticky="e", pady=2)
        parent.grid_columnconfigure(1, weight=1)

    @staticmethod
    def _button(parent: tk.Widget, text: str, command: Callable[[], None], primary: bool = False) -> tk.Button:
        background, foreground = (ACCENT, BG) if primary else (PANEL_LIGHT, TEXT)
        active = ACCENT_ACTIVE if primary else "#334155"
        return tk.Button(parent, text=text, command=command, bg=background, fg=foreground,
                         activebackground=active, activeforeground=foreground, relief="flat",
                         cursor="hand2", padx=10, pady=10, font=("Segoe UI", 9, "bold"))

    def _bind(self) -> None:
        bindings = {"<Up>": Move.UP, "w": Move.UP, "W": Move.UP,
                    "<Down>": Move.DOWN, "s": Move.DOWN, "S": Move.DOWN,
                    "<Left>": Move.LEFT, "a": Move.LEFT, "A": Move.LEFT,
                    "<Right>": Move.RIGHT, "d": Move.RIGHT, "D": Move.RIGHT}
        for key, move in bindings.items():
            self.root.bind(key, lambda _event, selected=move: self._human_move(selected))
        self.root.bind("r", lambda _event: self.restart())
        self.root.bind("R", lambda _event: self.restart())
        self.root.bind("<space>", lambda _event: self.toggle())
        self.root.bind("<Escape>", lambda _event: self._close())

    def _parse_settings(self) -> tuple[int, float | None]:
        seed = int(self.seed_var.get().strip())
        if self.time_mode_var.get() == UNLIMITED_MODE:
            return seed, None
        budget = float(self.budget_var.get().strip())
        if budget <= 0:
            raise ValueError("Total sec phải lớn hơn 0")
        return seed, budget

    def _select_agent(self, show_error: bool = True) -> bool:
        spec = AGENT_SPECS[self.agent_choice.get()]
        try:
            self.agent = (None if spec is None else self._external_agent if spec == "__external__"
                          else _load_agent(spec))
            if self.agent is not None:
                self.agent.reset(self.game.seed)
            return True
        except Exception as exc:
            self.agent = None
            self.agent_choice.set("Human")
            if show_error:
                messagebox.showerror("Không tải được agent", f"{type(exc).__name__}: {exc}")
            return False

    def restart(self) -> None:
        try:
            seed, budget = self._parse_settings()
        except ValueError as exc:
            messagebox.showerror("Thiết lập không hợp lệ", str(exc))
            return
        self.running = False
        self._generation += 1
        self.thinking = False
        self.game = Game(seed)
        self.total_budget_ms = None if budget is None else budget * 1000.0
        self.used_time_ms = 0.0
        self._select_agent()
        self.status_var.set("Dùng phím mũi tên / WASD" if self.agent is None else "Sẵn sàng chạy agent")
        self._render()

    def toggle(self) -> None:
        if self.agent is None:
            self.status_var.set("Chế độ Human · dùng phím mũi tên hoặc WASD")
            return
        if (self.game.game_over
                or (self.total_budget_ms is not None
                    and self.used_time_ms >= self.total_budget_ms)):
            return
        self.running = not self.running
        self.status_var.set("Đang suy nghĩ…" if self.running else "Đã tạm dừng")
        self._render_controls()

    def _human_move(self, move: Move) -> None:
        if self.agent is None and not self.game.game_over and self.game.move(move):
            if self.game.game_over:
                self.status_var.set("Game over · nhấn R để chơi lại")
            self._render()

    def _start_decision(self) -> None:
        remaining = (None if self.total_budget_ms is None else
                     max(0.0, self.total_budget_ms - self.used_time_ms))
        if remaining is not None and remaining <= 0.0:
            self._finish("Hết ngân sách thời gian")
            return
        decision_hint = remaining if remaining is not None else UNLIMITED_DECISION_HINT_MS
        generation = self._generation
        obs = self.game.observe(remaining, self.total_budget_ms)
        agent = self.agent
        self.thinking = True
        self.status_var.set("Đang suy nghĩ…")

        def worker() -> None:
            started = time.perf_counter_ns()
            move: Move | int | None = None
            error: BaseException | None = None
            try:
                move = agent.choose_move(obs, decision_hint)
            except BaseException as exc:
                error = exc
            elapsed = (time.perf_counter_ns() - started) / 1_000_000.0
            with self._decision_lock:
                self._decisions.append(_Decision(generation, move, elapsed, error))

        threading.Thread(target=worker, name="2048-agent", daemon=True).start()

    def _consume_decision(self) -> None:
        with self._decision_lock:
            decisions, self._decisions = self._decisions, []
        decision = next((item for item in reversed(decisions)
                         if item.generation == self._generation), None)
        if decision is None:
            return
        self.thinking = False
        self.used_time_ms += decision.elapsed_ms
        if decision.error is not None:
            self._finish(f"Agent lỗi: {type(decision.error).__name__}: {decision.error}")
            return
        if (self.total_budget_ms is not None
                and self.used_time_ms > self.total_budget_ms):
            self._finish("Hết ngân sách · nước cuối không được áp dụng")
            return
        try:
            move = Move(decision.move)
        except (TypeError, ValueError):
            self._finish(f"Nước đi không hợp lệ: {decision.move!r}")
            return
        if move not in self.game.available_moves:
            self._finish(f"Agent chọn nước cấm: {move.name}")
            return
        self.game.move(move)
        if self.game.game_over:
            self._finish("Game over · ván đấu kết thúc bình thường")
        else:
            self.status_var.set(f"Vừa đi {move.name} · {decision.elapsed_ms:.1f} ms")
        self._render()

    def _finish(self, message: str) -> None:
        self.running = self.thinking = False
        self.status_var.set(message)
        self._render_controls()

    def _tick(self) -> None:
        self._consume_decision()
        if self.running and not self.thinking and not self.game.game_over:
            self.thinking = True  # Reserve the slot so repeated ticks cannot queue starts.
            self.root.after(max(0, self.delay_var.get()), self._start_if_ready)
        self._render_clock()
        self.root.after(25, self._tick)

    def _start_if_ready(self) -> None:
        self.thinking = False
        if self.running and not self.game.game_over:
            self._start_decision()

    def _render_clock(self) -> None:
        if self.agent is None or self.total_budget_ms is None:
            self.time_var.set("Đến game over")
            return
        remaining = max(0.0, self.total_budget_ms - self.used_time_ms)
        self.time_var.set(f"{remaining / 1000:.2f}s")

    def _render(self) -> None:
        self.score_var.set(f"{self.game.score:,}".replace(",", "."))
        self.best_var.set(str(int(self.game.board.max())))
        self.moves_var.set(str(self.game.move_count))
        self._render_clock()
        self._render_controls()
        self._draw_board()

    def _render_controls(self) -> None:
        self.start_button.configure(text="Ⅱ  DỪNG" if self.running else "▶  CHẠY")
        locked = self.running or self.thinking
        self.agent_box.configure(state="disabled" if locked else "readonly")
        self.time_mode_box.configure(state="disabled" if locked else "readonly")
        budget_disabled = locked or self.time_mode_var.get() == UNLIMITED_MODE
        self.budget_entry.configure(state="disabled" if budget_disabled else "normal")

    def _draw_board(self) -> None:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width <= 10 or height <= 10:
            return
        self.canvas.delete("all")
        side = min(width, height)
        gap, origin_x, origin_y = max(7.0, side * 0.018), (width - side) / 2, (height - side) / 2
        cell = (side - 5 * gap) / 4
        spawn_position = self.game.last_spawn[0] if self.game.last_spawn else None
        for row in range(4):
            for col in range(4):
                value = int(self.game.board[row, col])
                fill, foreground = TILE_COLORS.get(value, ("#ec4899", "#fff1f2"))
                x1, y1 = origin_x + gap + col * (cell + gap), origin_y + gap + row * (cell + gap)
                x2, y2 = x1 + cell, y1 + cell
                spawned = spawn_position == (row, col)
                _rounded_rect(self.canvas, x1, y1, x2, y2, min(13, cell * 0.12), fill=fill,
                              outline=ACCENT if spawned else fill, width=2 if spawned else 0)
                if value:
                    digits = len(str(value))
                    font_size = max(15, int(cell * (0.31 if digits <= 3 else 0.25 if digits == 4 else 0.20)))
                    self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=str(value),
                                            fill=foreground, font=("Segoe UI", font_size, "bold"))

    def _close(self) -> None:
        self.running = False
        self._generation += 1
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def launch(seed: int = 0, agent: Any | None = None, *, agent_spec: str | None = None,
           total_time_sec: float = 60.0) -> None:
    GameUI(seed, agent, agent_spec, total_time_sec).run()
