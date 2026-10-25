# ✈️ Automated Airline Flight Crew Pairing Optimizer

A desktop app that solves the **0/1 Knapsack Problem with Dynamic Programming** and shows every step of it, built with Python and Tkinter for a Design and Analysis of Algorithms (DAA) assignment.
<img width="1346" height="719" alt="Screenshot 2026-10-25 195703" src="https://github.com/user-attachments/assets/60132e00-f9db-4912-9f45-4d1b04724dbe" />
<img width="1366" height="720" alt="image" src="https://github.com/user-attachments/assets/249d7b23-46fb-493b-8f18-981fa2b2f41d" />


Airlines must build crew pairings that maximise mission value without breaking legal duty-time limits (FAA / DGCA style shift caps). This maps directly onto 0/1 Knapsack:

| Knapsack concept | Aviation meaning |
|---|---|
| Item | Candidate flight pairing |
| Weight | Required duty hours |
| Profit | Mission value (points) |
| Capacity `W` | Maximum legal duty limit (hours) |

## Features

- **Flight manifest:** table of candidate flights with default data, an "Add Custom Flight" dialog (with validation), remove, restore defaults and clear all.
- **Editable duty limit:** 0 to 40 hours.
- **Interactive DP grid:** rows are flights `0..N`, columns are `0h..Wh`. Cells show their computed values, and you can click any evaluated cell to re-inspect its decision.
- **Decision & Inspection panel:** shows the recurrence for the active cell and whether the flight was **EXCLUDED** or **INCLUDED**.
- **Step-by-step animation:** Play / Auto-Solve, Single Step, Pause, Reset and a live speed slider (10 to 1500 ms).
- **Backtracking animation:** after the table is filled, the path from `dp[N][W]` back to row 0 is highlighted, then the final roster, hours used and total value are shown.
- **Zero dependencies:** standard library only (`tkinter`, `ttk`).

### Colour legend

| Colour | Meaning |
|---|---|
| 🟨 `#FDE047` | Active cell being evaluated |
| 🟦 `#BAE6FD` | Exclude reference `dp[i-1][w]` |
| 🟪 `#DDD6FE` | Include reference `dp[i-1][w - weight]` |
| ⬜ Slate | Settled cell |
| 🟩 `#86EFAC` | Backtracking solution path |

## The algorithm

```
dp[0][w] = 0
dp[i][w] = dp[i-1][w]                                          if weight[i] > w
dp[i][w] = max( dp[i-1][w],                                    # EXCLUDE flight i
                value[i] + dp[i-1][w - weight[i]] )            # INCLUDE flight i
```

- **Time complexity:** O(N · W)
- **Space complexity:** O(N · W). The full table is kept so the chosen flights can be recovered by backtracking.
- **Backtracking:** O(N). If `dp[i][w] != dp[i-1][w]`, flight `i` was included.
- **Boundary cases handled:** a flight longer than the current sub-capacity, a 0-hour limit, an empty roster, and ties (ties prefer exclude, and backtracking uses the same rule).

## Getting started

Requires Python 3.7+ with Tkinter (included with the standard Python installer on Windows and macOS).

```bash
# Linux only, if Tkinter is missing:
sudo apt install python3-tk

python flight_crew_pairing_optimizer.py
```

## Code structure

| Class | Responsibility |
|---|---|
| `Flight` | Dataclass for one knapsack item |
| `KnapsackSolver` | Pure DP logic, exposed as a generator that yields one event per cell |
| `DPGridView` | Scrollable canvas that draws the matrix, headers and highlights |
| `FlightDialog` | Modal dialog for adding a custom flight |
| `FlightPairingApp` | GUI state, controls, and the `root.after()` animation loop |

## Default example

With the built-in 8 flights and a 12-hour limit, the optimiser selects `6E204`, `SG417`, `6E339` and `IX645`: 12 duty hours for **169** mission points.

## Course context

Built for a university DAA assignment on dynamic programming and the 0/1 Knapsack problem.
