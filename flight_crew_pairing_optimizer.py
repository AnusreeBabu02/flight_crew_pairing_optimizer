#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Airline Flight Crew Pairing Optimizer
================================================
0/1 Knapsack solved with Dynamic Programming, visualised step by step in Tkinter.

Domain mapping
--------------
    item            -> candidate flight leg / pairing
    weight[i]       -> required duty hours of the flight
    value[i]        -> mission value (profit points) of the flight
    capacity W      -> maximum legal duty limit (FAA / DGCA style shift cap, hours)

Recurrence relation (the heart of the algorithm)
------------------------------------------------
    dp[i][w] = best total mission value using only the first i flights
               with at most w duty hours available.

    dp[0][w] = 0                                         (no flights -> no value)
    dp[i][w] = dp[i-1][w]                                if weight[i] > w
    dp[i][w] = max( dp[i-1][w],                          (EXCLUDE flight i)
                    value[i] + dp[i-1][w - weight[i]] )  (INCLUDE flight i)

Complexity
----------
    Time  : O(N * W)  - every one of the (N+1)*(W+1) cells is computed once in O(1).
    Space : O(N * W)  - the full table is kept (needed for backtracking and for
                        the visualisation; a rolling 1-D array would give O(W) space
                        but could not reconstruct the chosen roster).
    Backtracking: O(N).

Only the Python standard library is used (tkinter / ttk).
Run:  python flight_crew_pairing_optimizer.py
"""

import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from tkinter import ttk, messagebox

# --------------------------------------------------------------------------- #
#  Constants                                                                  #
# --------------------------------------------------------------------------- #
COL_ACTIVE = "#FDE047"    # cell being evaluated            (bright yellow)
COL_EXCLUDE = "#BAE6FD"   # dp[i-1][w]       reference      (soft blue)
COL_INCLUDE = "#DDD6FE"   # dp[i-1][w-wt]    reference      (soft purple)
COL_SETTLED = "#CBD5E1"   # evaluated / settled cell        (slate)
COL_BLANK = "#F8FAFC"     # not yet evaluated               (near white)
COL_PATH = "#86EFAC"      # backtracking solution path      (vibrant green)
COL_GRID_LINE = "#94A3B8"
COL_HEADER_BG = "#1E293B"
COL_HEADER_FG = "#F8FAFC"

CELL_W, CELL_H = 46, 32          # DP cell size in pixels
HDR_W, HDR_H = 175, 30           # row-header width / column-header height

MAX_CAPACITY = 40                # keeps the grid a sensible size
DEFAULT_CAPACITY = 12

DEFAULT_FLIGHTS = [
    # code,   route,     duty hours, mission value
    ("AI101", "BOM-DEL", 3, 40),
    ("6E204", "DEL-BLR", 4, 55),
    ("UK813", "BLR-HYD", 2, 25),
    ("AI560", "HYD-MAA", 3, 38),
    ("SG417", "MAA-CCU", 5, 72),
    ("AI772", "CCU-GOI", 4, 48),
    ("6E339", "GOI-COK", 2, 30),
    ("IX645", "COK-TRV", 1, 12),
]


@dataclass
class Flight:
    """One candidate flight pairing = one knapsack item."""
    code: str
    route: str
    hours: int    # weight
    value: int    # profit


# --------------------------------------------------------------------------- #
#  Algorithm layer (no GUI code)                                              #
# --------------------------------------------------------------------------- #
class KnapsackSolver:
    """0/1 knapsack DP exposed as a generator so the GUI can step through it."""

    def __init__(self, flights, capacity):
        self.flights = list(flights)
        self.n = len(self.flights)
        self.W = capacity
        # Space complexity O(N*W): (N+1) rows x (W+1) columns.
        # Row 0 (no flights) and every cell start at 0 -> this IS the base case
        # dp[0][w] = 0.  With an empty roster (n = 0) the table is just row 0;
        # with W = 0 the table is just column 0 and nothing can ever fit
        # (every weight >= 1h), so all values stay 0.
        self.dp = [[0] * (self.W + 1) for _ in range(self.n + 1)]
        self.selected = []        # indices (0-based) of chosen flights
        self.total_hours = 0
        self.total_value = 0

    def steps(self):
        """Yield one event dict per DP cell, then per backtracking cell."""
        n, W, dp, flights = self.n, self.W, self.dp, self.flights

        # ---------------- Phase 1: forward table fill -> O(N * W) ---------- #
        for i in range(1, n + 1):                 # rows    : flights 1..N
            f = flights[i - 1]
            for w in range(W + 1):                # columns : sub-capacity 0..W
                exclude = dp[i - 1][w]            # option A: skip flight i
                if f.hours > w:
                    # Boundary case: flight is longer than the sub-capacity w
                    # (always true for w = 0 because hours >= 1) -> it cannot
                    # be taken, so the value is inherited from the row above.
                    dp[i][w] = exclude
                    yield {"kind": "fill", "i": i, "w": w, "flight": f,
                           "fits": False, "exclude": exclude, "ref": None,
                           "include": None, "choice": "EXCLUDE",
                           "result": dp[i][w]}
                else:
                    # option B: take flight i; remaining hours w - weight[i]
                    # are filled optimally by the first i-1 flights.
                    ref = dp[i - 1][w - f.hours]
                    include = f.value + ref
                    # Strict '>' => on a tie we prefer EXCLUDE.  Backtracking
                    # relies on the same rule (dp[i][w] != dp[i-1][w]).
                    if include > exclude:
                        dp[i][w] = include
                        choice = "INCLUDE"
                    else:
                        dp[i][w] = exclude
                        choice = "EXCLUDE"
                    yield {"kind": "fill", "i": i, "w": w, "flight": f,
                           "fits": True, "exclude": exclude, "ref": ref,
                           "include": include, "choice": choice,
                           "result": dp[i][w]}

        # ---------------- Phase 2: backtracking -> O(N) -------------------- #
        i, w = n, W
        chosen = []
        while i > 0:
            f = flights[i - 1]
            # If the value changed versus the row above, flight i was INCLUDED.
            took = dp[i][w] != dp[i - 1][w]
            nxt_w = w - f.hours if took else w
            yield {"kind": "back", "i": i, "w": w, "flight": f, "took": took,
                   "val": dp[i][w], "above": dp[i - 1][w],
                   "next": (i - 1, nxt_w)}
            if took:
                chosen.append(i - 1)
                w = nxt_w
            i -= 1
        # Row 0 reached.  Every dp[0][*] is 0, so the walk may end at dp[0][w]
        # with w > 0 when some duty hours remain unused (w == 0 if the limit
        # was used exactly, i.e. the cell dp[0][0]).
        yield {"kind": "back_end", "i": 0, "w": w}

        chosen.reverse()
        self.selected = chosen
        self.total_hours = sum(flights[k].hours for k in chosen)
        self.total_value = dp[n][W]
        yield {"kind": "done"}


# --------------------------------------------------------------------------- #
#  Canvas layer                                                               #
# --------------------------------------------------------------------------- #
class DPGridView:
    """Scrollable canvas that renders the DP matrix with sticky headers."""

    STATE_COLOR = {"blank": COL_BLANK, "settled": COL_SETTLED, "path": COL_PATH}

    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text="Dynamic Programming Matrix  dp[i][w]")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.frame, background="white", highlightthickness=0)
        self.vbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self._on_xscroll, yscrollcommand=self._on_yscroll)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")

        self.cell_font = tkfont.Font(family="Courier New", size=10, weight="bold")
        self.hdr_font = tkfont.Font(family="Helvetica", size=9, weight="bold")

        self.rects, self.texts, self.base = {}, {}, {}
        self.temp = []
        self.grid_w = self.grid_h = 1
        self._hx = self._hy = 0.0
        self.on_cell_click = None

        self.canvas.bind("<Button-1>", self._click)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._hwheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    # ----- scrolling helpers (keep headers pinned to the viewport edge) ----- #
    def _on_xscroll(self, first, last):
        self.hbar.set(first, last)
        self._fix_headers()

    def _on_yscroll(self, first, last):
        self.vbar.set(first, last)
        self._fix_headers()

    def _fix_headers(self):
        dx = self.canvas.canvasx(0) - self._hx
        dy = self.canvas.canvasy(0) - self._hy
        if dx:
            self.canvas.move("rowhdr", dx, 0)
            self.canvas.move("corner", dx, 0)
            self._hx += dx
        if dy:
            self.canvas.move("colhdr", 0, dy)
            self.canvas.move("corner", 0, dy)
            self._hy += dy

    def _wheel(self, e):
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _hwheel(self, e):
        self.canvas.xview_scroll(-1 if e.delta > 0 else 1, "units")

    # ----- building the grid ------------------------------------------------ #
    def build(self, flights, capacity):
        cv = self.canvas
        cv.delete("all")
        self.rects, self.texts, self.base, self.temp = {}, {}, {}, []
        self._hx = self._hy = 0.0
        n, W = len(flights), capacity

        for i in range(n + 1):
            for w in range(W + 1):
                x0, y0 = HDR_W + w * CELL_W, HDR_H + i * CELL_H
                state = "settled" if i == 0 else "blank"   # row 0 = base case
                self.base[(i, w)] = state
                self.rects[(i, w)] = cv.create_rectangle(
                    x0, y0, x0 + CELL_W, y0 + CELL_H,
                    fill=self.STATE_COLOR[state], outline=COL_GRID_LINE)
                self.texts[(i, w)] = cv.create_text(
                    x0 + CELL_W / 2, y0 + CELL_H / 2,
                    text="0" if i == 0 else "", font=self.cell_font, fill="#0F172A")

        # row headers (flight codes)
        for i in range(n + 1):
            y0 = HDR_H + i * CELL_H
            label = "i=0  (no flights)" if i == 0 else \
                f"i={i}  {flights[i - 1].code}  ({flights[i - 1].hours}h, {flights[i - 1].value})"
            cv.create_rectangle(0, y0, HDR_W, y0 + CELL_H, fill=COL_HEADER_BG,
                                outline=COL_GRID_LINE, tags="rowhdr")
            cv.create_text(8, y0 + CELL_H / 2, text=label, anchor="w",
                           fill=COL_HEADER_FG, font=self.hdr_font, tags="rowhdr")

        # column headers (hours)
        for w in range(W + 1):
            x0 = HDR_W + w * CELL_W
            cv.create_rectangle(x0, 0, x0 + CELL_W, HDR_H, fill=COL_HEADER_BG,
                                outline=COL_GRID_LINE, tags="colhdr")
            cv.create_text(x0 + CELL_W / 2, HDR_H / 2, text=f"{w}h",
                           fill=COL_HEADER_FG, font=self.hdr_font, tags="colhdr")

        # corner
        cv.create_rectangle(0, 0, HDR_W, HDR_H, fill="#0F172A",
                            outline=COL_GRID_LINE, tags="corner")
        cv.create_text(HDR_W / 2, HDR_H / 2, text="Flight  \\  Duty hours",
                       fill=COL_HEADER_FG, font=self.hdr_font, tags="corner")

        cv.tag_raise("rowhdr")
        cv.tag_raise("colhdr")
        cv.tag_raise("corner")

        self.grid_w = HDR_W + (W + 1) * CELL_W + 2
        self.grid_h = HDR_H + (n + 1) * CELL_H + 2
        cv.configure(scrollregion=(0, 0, self.grid_w, self.grid_h))
        cv.xview_moveto(0)
        cv.yview_moveto(0)

    # ----- cell painting ---------------------------------------------------- #
    def set_value(self, cell, value):
        self.canvas.itemconfig(self.texts[cell], text=str(value))

    def set_state(self, cell, state):
        self.base[cell] = state
        self.canvas.itemconfig(self.rects[cell], fill=self.STATE_COLOR[state])

    def clear_temp(self):
        """Restore temporary highlights to each cell's settled colour."""
        for cell in self.temp:
            self.canvas.itemconfig(self.rects[cell],
                                   fill=self.STATE_COLOR[self.base[cell]],
                                   outline=COL_GRID_LINE, width=1)
        self.temp = []

    def mark_temp(self, cells):
        """cells: list of (cell, colour, thick_outline). Later items paint on top."""
        self.clear_temp()
        for cell, colour, thick in cells:
            self.canvas.itemconfig(self.rects[cell], fill=colour,
                                   outline="#0F172A" if thick else COL_GRID_LINE,
                                   width=2 if thick else 1)
            self.temp.append(cell)

    def ensure_visible(self, cell):
        i, w = cell
        cv = self.canvas
        x0, y0 = HDR_W + w * CELL_W, HDR_H + i * CELL_H
        vx, vy = cv.canvasx(0), cv.canvasy(0)
        vw, vh = cv.winfo_width(), cv.winfo_height()
        if vw <= 1 or vh <= 1:
            return
        if x0 < vx + HDR_W or x0 + CELL_W > vx + vw:
            cv.xview_moveto(max(0, x0 - HDR_W - CELL_W * 2) / self.grid_w)
        if y0 < vy + HDR_H or y0 + CELL_H > vy + vh:
            cv.yview_moveto(max(0, y0 - HDR_H - CELL_H * 2) / self.grid_h)

    # ----- clicking a cell -------------------------------------------------- #
    def _click(self, event):
        if event.x < HDR_W or event.y < HDR_H or not self.on_cell_click:
            return
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        w = int((x - HDR_W) // CELL_W)
        i = int((y - HDR_H) // CELL_H)
        if (i, w) in self.rects:
            self.on_cell_click((i, w))


# --------------------------------------------------------------------------- #
#  Add-flight dialog                                                          #
# --------------------------------------------------------------------------- #
class FlightDialog(tk.Toplevel):
    """Modal dialog that collects a custom flight."""

    def __init__(self, parent, existing_codes):
        super().__init__(parent)
        self.title("Add Custom Flight")
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        self.existing = {c.upper() for c in existing_codes}

        self.v_code = tk.StringVar()
        self.v_org = tk.StringVar()
        self.v_dst = tk.StringVar()
        self.v_hours = tk.StringVar(value="3")
        self.v_value = tk.StringVar(value="30")

        body = ttk.Frame(self, padding=14)
        body.grid(sticky="nsew")
        rows = [("Flight Code", self.v_code), ("Origin (e.g. BOM)", self.v_org),
                ("Destination (e.g. DEL)", self.v_dst),
                ("Required Duty Hours (1-24)", self.v_hours),
                ("Mission Value (points)", self.v_value)]
        self.first_entry = None
        for r, (label, var) in enumerate(rows):
            ttk.Label(body, text=label).grid(row=r, column=0, sticky="w", pady=4, padx=(0, 10))
            e = ttk.Entry(body, textvariable=var, width=22)
            e.grid(row=r, column=1, pady=4)
            if self.first_entry is None:
                self.first_entry = e

        btns = ttk.Frame(body)
        btns.grid(row=len(rows), column=0, columnspan=2, pady=(12, 0), sticky="e")
        ttk.Button(btns, text="Add Flight", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.first_entry.focus_set()

    def _ok(self):
        code = self.v_code.get().strip().upper()
        org = self.v_org.get().strip().upper()
        dst = self.v_dst.get().strip().upper()
        if not code or not org or not dst:
            messagebox.showerror("Missing data", "Code, origin and destination are required.", parent=self)
            return
        if code in self.existing:
            messagebox.showerror("Duplicate", f"Flight code {code} already exists.", parent=self)
            return
        try:
            hours = int(self.v_hours.get())
            value = int(self.v_value.get())
        except ValueError:
            messagebox.showerror("Invalid number", "Hours and value must be whole numbers.", parent=self)
            return
        if not 1 <= hours <= 24:
            messagebox.showerror("Invalid hours", "Duty hours must be between 1 and 24.", parent=self)
            return
        if not 0 <= value <= 10000:
            messagebox.showerror("Invalid value", "Mission value must be between 0 and 10000.", parent=self)
            return
        self.result = Flight(code, f"{org}-{dst}", hours, value)
        self.destroy()


# --------------------------------------------------------------------------- #
#  Main application                                                           #
# --------------------------------------------------------------------------- #
class FlightPairingApp:
    """Owns the GUI state and drives the solver generator via root.after()."""

    def __init__(self, root):
        self.root = root
        root.title("Automated Airline Flight Crew Pairing Optimizer  -  0/1 Knapsack (DP)")
        root.geometry("1340x820")
        root.minsize(1100, 680)

        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass

        self.flights = [Flight(*f) for f in DEFAULT_FLIGHTS]
        self.capacity = DEFAULT_CAPACITY
        self.solver = None
        self.gen = None
        self.running = False
        self.finished = False
        self.after_id = None
        self.decisions = {}          # (i, w) -> inspection lines, for click-to-inspect
        self.cells_done = 0
        self.cells_total = 0

        self.bold = tkfont.Font(family="Helvetica", size=10, weight="bold")

        self._build_ui()
        self._refresh_tree()
        self.reset()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ======================================================================= #
    #  UI construction                                                        #
    # ======================================================================= #
    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---------------- Left sidebar: manifest + capacity ---------------- #
        left = ttk.Frame(self.root, padding=8)
        left.grid(row=0, column=0, sticky="ns")

        manifest = ttk.LabelFrame(left, text="Flight Manifest (candidate pairings)", padding=6)
        manifest.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(0, weight=1)

        cols = ("code", "route", "hours", "value")
        self.tree = ttk.Treeview(manifest, columns=cols, show="headings",
                                 height=14, selectmode="browse")
        heads = {"code": ("Flight Code", 80), "route": ("Origin-Dest", 85),
                 "hours": ("Duty Hrs (wt)", 85), "value": ("Value (pts)", 80)}
        for c in cols:
            self.tree.heading(c, text=heads[c][0])
            self.tree.column(c, width=heads[c][1], anchor="center")
        sb = ttk.Scrollbar(manifest, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        manifest.rowconfigure(0, weight=1)

        self.lbl_count = ttk.Label(manifest, text="")
        self.lbl_count.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_row = ttk.Frame(manifest)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(btn_row, text="Add Custom Flight", command=self.add_flight).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btn_row, text="Remove Selected", command=self.remove_flight).grid(row=0, column=1, sticky="ew")
        ttk.Button(btn_row, text="Restore Defaults", command=self.restore_defaults).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(4, 0))
        ttk.Button(btn_row, text="Clear All", command=self.clear_flights).grid(row=1, column=1, sticky="ew", pady=(4, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        cap = ttk.LabelFrame(left, text="Maximum Legal Duty Limit", padding=8)
        cap.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.v_cap = tk.StringVar(value=str(self.capacity))
        ttk.Label(cap, text="Capacity W (hours, 0-%d):" % MAX_CAPACITY).grid(row=0, column=0, sticky="w")
        spin = ttk.Spinbox(cap, from_=0, to=MAX_CAPACITY, width=6, textvariable=self.v_cap)
        spin.grid(row=0, column=1, padx=6)
        spin.bind("<Return>", lambda e: self.apply_capacity())
        ttk.Button(cap, text="Apply", command=self.apply_capacity).grid(row=0, column=2)
        ttk.Label(cap, foreground="#475569", wraplength=330,
                  text="Typical shift caps are 10-14 h (FAA / DGCA). Changing the "
                       "manifest or the limit rebuilds the matrix.").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # ---------------- Right side ---------------------------------------- #
        right = ttk.Frame(self.root, padding=(0, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=3)
        right.rowconfigure(2, weight=2)

        # ----- control bar ----- #
        ctrl = ttk.LabelFrame(right, text="Animation Controls", padding=6)
        ctrl.grid(row=0, column=0, sticky="ew")
        self.btn_play = ttk.Button(ctrl, text="▶ Play / Auto-Solve", command=self.play)
        self.btn_step = ttk.Button(ctrl, text="Single Step", command=self.single_step)
        self.btn_pause = ttk.Button(ctrl, text="❚❚ Pause", command=self.pause)
        self.btn_reset = ttk.Button(ctrl, text="⟲ Reset", command=self.reset)
        for k, b in enumerate((self.btn_play, self.btn_step, self.btn_pause, self.btn_reset)):
            b.grid(row=0, column=k, padx=3)

        self.speed = tk.Scale(ctrl, from_=10, to=1500, resolution=10, orient="horizontal",
                              length=230, label="Step delay (ms)", showvalue=True)
        self.speed.set(250)
        self.speed.grid(row=0, column=4, padx=(14, 6))

        self.lbl_status = ttk.Label(ctrl, text="", font=self.bold)
        self.lbl_status.grid(row=0, column=5, padx=10, sticky="w")

        legend = ttk.Frame(ctrl)
        legend.grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))
        for text, colour in (("Active cell", COL_ACTIVE), ("Exclude ref  dp[i-1][w]", COL_EXCLUDE),
                             ("Include ref  dp[i-1][w-wt]", COL_INCLUDE),
                             ("Settled", COL_SETTLED), ("Solution path", COL_PATH)):
            tk.Label(legend, text="  ", background=colour, relief="solid", bd=1).pack(side="left", padx=(8, 3))
            ttk.Label(legend, text=text).pack(side="left")

        # ----- DP grid ----- #
        self.dp_view = DPGridView(right)
        self.dp_view.frame.grid(row=1, column=0, sticky="nsew", pady=8)
        self.dp_view.on_cell_click = self.inspect_cell

        # ----- bottom panels ----- #
        bottom = ttk.Frame(right)
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)
        bottom.rowconfigure(0, weight=1)

        self.txt_inspect = self._make_text_panel(bottom, 0, "Decision & Inspection Panel")
        self.txt_summary = self._make_text_panel(bottom, 1, "Final Crew Roster")

    def _make_text_panel(self, parent, column, title):
        box = ttk.LabelFrame(parent, text=title, padding=4)
        box.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if column == 0 else 0)
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)
        text = tk.Text(box, height=9, wrap="word", state="disabled", font="TkFixedFont",
                       background="#FFFFFF", relief="flat", padx=6, pady=4)
        bar = ttk.Scrollbar(box, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=bar.set)
        text.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")
        text.tag_configure("head", font=self.bold)
        text.tag_configure("mono", font="TkFixedFont")
        text.tag_configure("excl", foreground="#0369A1")
        text.tag_configure("incl", foreground="#6D28D9")
        text.tag_configure("warn", foreground="#B45309")
        text.tag_configure("good", foreground="#15803D", font=self.bold)
        text.tag_configure("excl_b", foreground="#0369A1", font=self.bold)
        text.tag_configure("incl_b", foreground="#6D28D9", font=self.bold)
        text.tag_configure("dim", foreground="#64748B")
        return text

    @staticmethod
    def _set_text(widget, lines):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for text, tag in lines:
            widget.insert("end", text, tag)
        widget.configure(state="disabled")

    # ======================================================================= #
    #  Manifest / capacity management                                         #
    # ======================================================================= #
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, f in enumerate(self.flights):
            self.tree.insert("", "end", iid=str(idx), values=(f.code, f.route, f.hours, f.value))
        self.lbl_count.configure(text=f"{len(self.flights)} candidate flight(s)")

    def add_flight(self):
        dlg = FlightDialog(self.root, [f.code for f in self.flights])
        self.root.wait_window(dlg)
        if dlg.result:
            self.flights.append(dlg.result)
            self._refresh_tree()
            self.reset()

    def remove_flight(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Remove flight", "Select a flight in the manifest first.")
            return
        del self.flights[int(sel[0])]
        self._refresh_tree()
        self.reset()

    def restore_defaults(self):
        self.flights = [Flight(*f) for f in DEFAULT_FLIGHTS]
        self._refresh_tree()
        self.reset()

    def clear_flights(self):
        # Boundary case: empty roster -> only row 0 exists, optimum = 0.
        self.flights = []
        self._refresh_tree()
        self.reset()

    def apply_capacity(self):
        try:
            cap = int(self.v_cap.get())
        except ValueError:
            messagebox.showerror("Invalid capacity", "Duty limit must be a whole number of hours.")
            return
        if not 0 <= cap <= MAX_CAPACITY:
            messagebox.showerror("Invalid capacity", f"Duty limit must be between 0 and {MAX_CAPACITY} hours.")
            return
        self.capacity = cap
        self.reset()

    # ======================================================================= #
    #  Animation control                                                      #
    # ======================================================================= #
    def reset(self):
        self._cancel_timer()
        self.running = False
        self.solver = KnapsackSolver(self.flights, self.capacity)
        self.gen = self.solver.steps()
        self.finished = False
        self.decisions.clear()
        self.cells_done = 0
        self.cells_total = self.solver.n * (self.solver.W + 1)
        self.dp_view.build(self.flights, self.capacity)
        self._show_intro()
        self._set_text(self.txt_summary, [("Press Play or Single Step to start.\n", "dim")])
        self._update_status("Ready")
        self._update_buttons()

    def play(self):
        if self.running or self.finished:
            return
        self.running = True
        self._update_buttons()
        self._tick()

    def pause(self):
        self.running = False
        self._cancel_timer()
        self._update_buttons()

    def single_step(self):
        if self.finished:
            return
        if self.running:
            self.pause()
        self._advance()
        self._update_buttons()

    def _tick(self):
        """Non-blocking animation loop driven by root.after()."""
        self.after_id = None
        if not self.running:
            return
        if not self._advance():
            self.running = False
            self._update_buttons()
            return
        self.after_id = self.root.after(int(self.speed.get()), self._tick)

    def _cancel_timer(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def _on_close(self):
        self._cancel_timer()
        self.root.destroy()

    def _update_buttons(self):
        can_go = not self.finished and not self.running
        self.btn_play.state(["!disabled"] if can_go else ["disabled"])
        self.btn_step.state(["!disabled"] if can_go else ["disabled"])
        self.btn_pause.state(["!disabled"] if self.running else ["disabled"])

    def _update_status(self, text):
        self.lbl_status.configure(text=text)

    # ======================================================================= #
    #  Event handling (one generator event -> one visual update)              #
    # ======================================================================= #
    def _advance(self):
        """Run one generator step. Returns True while more steps remain."""
        if self.finished:
            return False
        try:
            ev = next(self.gen)
        except StopIteration:
            self.finished = True
            return False
        self._apply(ev)
        if ev["kind"] == "done":
            self.finished = True
            return False
        return True

    def _apply(self, ev):
        kind = ev["kind"]
        view = self.dp_view

        if kind == "fill":
            i, w, f = ev["i"], ev["w"], ev["flight"]
            cell = (i, w)
            view.set_value(cell, ev["result"])
            view.set_state(cell, "settled")
            marks = [((i - 1, w), COL_EXCLUDE, False)]
            if ev["fits"]:
                marks.append(((i - 1, w - f.hours), COL_INCLUDE, False))
            marks.append((cell, COL_ACTIVE, True))
            view.mark_temp(marks)
            view.ensure_visible(cell)

            lines = self._fill_lines(ev)
            self.decisions[cell] = lines
            self._set_text(self.txt_inspect, lines)
            self.cells_done += 1
            self._update_status(f"Phase 1 - filling table: {self.cells_done}/{self.cells_total} cells")

        elif kind == "back":
            i, w, f = ev["i"], ev["w"], ev["flight"]
            cell = (i, w)
            view.set_state(cell, "path")
            view.mark_temp([(cell, COL_PATH, True)])
            view.ensure_visible(cell)
            self._set_text(self.txt_inspect, self._back_lines(ev))
            self._update_status("Phase 2 - backtracking from dp[N][W]")

        elif kind == "back_end":
            cell = (0, ev["w"])
            view.set_state(cell, "path")
            view.mark_temp([(cell, COL_PATH, True)])
            view.ensure_visible(cell)
            w = ev["w"]
            end_note = ("The walk ended exactly at dp[0][0]: the duty limit was fully used."
                        if w == 0 else
                        f"The walk ended at dp[0][{w}] ({w}h of the limit remain unused; every "
                        f"cell of row 0 equals 0, so this is equivalent to dp[0][0]).")
            self._set_text(self.txt_inspect, [
                ("Backtracking reached row 0 (no flights left to decide).\n", "head"),
                (end_note + "\n", "mono"),
            ])
            self._update_status("Phase 2 - backtracking complete")

        elif kind == "done":
            view.clear_temp()
            self._update_status("Complete")
            self._show_summary()

    # ------------------------- text builders -------------------------------- #
    def _fill_lines(self, ev):
        i, w, f = ev["i"], ev["w"], ev["flight"]
        lines = [
            (f"Evaluating dp[{i}][{w}]  -  Flight {f.code} ({f.route}):  "
             f"weight = {f.hours}h, value = {f.value}\n", "head"),
            ("Recurrence: dp[i][w] = max( dp[i-1][w], value[i] + dp[i-1][w - weight[i]] )\n", "mono"),
            ("\n", "mono"),
        ]
        if not ev["fits"]:
            lines += [
                (f"Boundary check: weight {f.hours}h > sub-capacity w = {w}h  ->  the flight cannot fit.\n", "warn"),
                (f"dp[{i}][{w}] = dp[{i - 1}][{w}] = {ev['exclude']}\n", "excl"),
                ("Decision: EXCLUDED  (kept the upper cell's value)\n", "excl_b"),
            ]
        else:
            ex, inc, ref = ev["exclude"], ev["include"], ev["ref"]
            lines += [
                (f"  EXCLUDE option (blue):   dp[{i - 1}][{w}] = {ex}\n", "excl"),
                (f"  INCLUDE option (purple): value[{i}] + dp[{i - 1}][{w - f.hours}] = "
                 f"{f.value} + {ref} = {inc}\n", "incl"),
                (f"dp[{i}][{w}] = max({ex}, {inc}) = {ev['result']}\n", "mono"),
            ]
            if ev["choice"] == "INCLUDE":
                lines.append((f"Decision: INCLUDED  (upper-left reference {ref} + flight value {f.value} "
                              f"= {inc} beats {ex})\n", "incl_b"))
            elif inc == ex:
                lines.append((f"Decision: EXCLUDED  (tie {ex} = {inc}; the upper value is kept)\n", "excl_b"))
            else:
                lines.append((f"Decision: EXCLUDED  (upper value {ex} is better than {inc})\n", "excl_b"))
        return lines

    def _back_lines(self, ev):
        i, w, f = ev["i"], ev["w"], ev["flight"]
        lines = [
            (f"Backtracking at dp[{i}][{w}] = {ev['val']}   (Flight {f.code})\n", "head"),
            (f"Compare with the cell above: dp[{i - 1}][{w}] = {ev['above']}\n", "mono"),
        ]
        ni, nw = ev["next"]
        if ev["took"]:
            lines += [
                (f"Values differ ({ev['val']} != {ev['above']})  ->  flight {f.code} was INCLUDED.\n", "incl_b"),
                (f"Reduce the remaining limit: w = {w} - {f.hours} = {nw}h, move to dp[{ni}][{nw}].\n", "mono"),
            ]
        else:
            lines += [
                (f"Values equal  ->  flight {f.code} was EXCLUDED.\n", "excl_b"),
                (f"Keep w = {w}h, move straight up to dp[{ni}][{nw}].\n", "mono"),
            ]
        return lines

    def _show_intro(self):
        n, W = len(self.flights), self.capacity
        lines = [
            ("0/1 Knapsack  -  Flight Crew Pairing\n", "head"),
            ("dp[i][w] = max( dp[i-1][w],  value[i] + dp[i-1][w - weight[i]] )\n", "mono"),
            (f"\nMatrix size: {n + 1} rows x {W + 1} columns   "
             f"(Time O(N*W), Space O(N*W))\n", "dim"),
        ]
        if n == 0:
            lines.append(("Empty roster: there is nothing to optimise; the answer is 0.\n", "warn"))
        elif W == 0:
            lines.append(("Duty limit is 0h: no flight can fit, so every cell stays 0.\n", "warn"))
        lines.append(("Click any evaluated cell to re-inspect its decision.\n", "dim"))
        self._set_text(self.txt_inspect, lines)

    def inspect_cell(self, cell):
        """Click-to-inspect: show the stored decision for an evaluated cell."""
        if cell in self.decisions:
            self._set_text(self.txt_inspect, self.decisions[cell])
        elif cell[0] == 0:
            self._set_text(self.txt_inspect, [
                (f"dp[0][{cell[1]}] = 0\n", "head"),
                ("Base case: with no flights available the value is 0 for every capacity.\n", "mono")])

    def _show_summary(self):
        s = self.solver
        lines = []
        if not s.selected:
            if s.n == 0:
                lines.append(("Empty roster - no flights available.\n", "warn"))
            else:
                lines.append(("No flight selected (limit too small or nothing adds value).\n", "warn"))
        else:
            lines.append(("Selected flights:\n", "head"))
            for k in s.selected:
                f = s.flights[k]
                lines.append((f"  * {f.code:<6} {f.route:<8} {f.hours:>2}h  {f.value:>4} pts\n", "mono"))
        idle = s.W - s.total_hours
        lines += [
            ("\n", "mono"),
            (f"Total duty hours utilised : {s.total_hours} / {s.W} h  ({idle} h idle)\n", "good"),
            (f"Total mission value       : {s.total_value} points\n", "good"),
        ]
        self._set_text(self.txt_summary, lines)


def main():
    root = tk.Tk()
    FlightPairingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
