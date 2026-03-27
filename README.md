# 🧠 Cognitive Games Hub

A collection of **6 cognitive skill assessment games** built with Python, bundled with a **Streamlit dashboard** that launches each game and visualizes your performance across key cognitive dimensions.

---

## 🎮 Games Included

| Game | Library | Cognitive Skills Assessed |
|------|---------|--------------------------|
| **Stroop Test** (`Stroop1.py`) | Tkinter | Attention & Focus, Processing Speed, Cognitive Flexibility |
| **Tower of Hanoi** (`Tower_of_Hanoi_2.py`) | Pygame | Spatial Awareness, Problem-Solving, Planning |
| **Slide Puzzle** (`slide_puzzle_multi_round.py`) | Pygame | Spatial Reasoning, Problem-Solving (3 rounds: 3×4, 4×4, 5×5) |
| **Memory Grid** (`memory_grid_modified.py`) | Pygame | Memory, Attention & Focus |
| **Pattern Matching** (`Pattern_Matching_1.py`) | Tkinter | Processing Speed, Attention, Consistency (3 rounds: 4×4, 8×8, 12×12) |
| **Shape–Color Switch** (`shape_color_grid.py`) | Pygame | Cognitive Flexibility, Reaction Time (3 rounds) |

---

## 🖥️ Dashboard

Two dashboard versions are included:

- **`app3.py`** — Unified dashboard that launches games as subprocesses and reads results from `game_results.json`
- **`app4.py`** — Enhanced version with per-game result discovery (scans output files and stdout for JSON), richer visualizations using Plotly and Altair

---

## 📁 Project Structure

```
streamlit-cognitive-games/
│
├── app3.py                        # Streamlit dashboard v1
├── app4.py                        # Streamlit dashboard v2 (recommended)
│
├── Stroop1.py                     # Stroop Color-Word Test
├── Tower_of_Hanoi_2.py            # Tower of Hanoi (Pygame)
├── slide_puzzle_multi_round.py    # Slide Puzzle — 3 rounds (Pygame)
├── memory_grid_modified.py        # Memory Grid (Pygame)
├── Pattern_Matching_1.py          # Pattern Matching — 3 rounds (Tkinter)
├── shape_color_grid.py            # Shape–Color Switch (Pygame)
│
├── requirements.txt               # Python dependencies
├── .gitignore                     # Files to exclude from Git
└── README.md                      # This file
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.8 or higher
- pip

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/streamlit-cognitive-games.git
cd streamlit-cognitive-games
```

### 2. (Optional) Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
streamlit run app4.py
```

> To run any game standalone, just execute it directly:
> ```bash
> python Stroop1.py
> python Tower_of_Hanoi_2.py
> ```

---

## 📊 Cognitive Skills Assessed

Each game measures a subset of these 7 cognitive dimensions:

- 🧠 **Memory**
- 🎯 **Attention & Focus**
- 🔢 **Problem-Solving & Logical Thinking**
- 🗺️ **Spatial Awareness & Planning**
- ⚡ **Processing Speed & Reaction Time**
- 🔄 **Cognitive Flexibility**
- 🖱️ **Hand–Eye Coordination & Motor Skills**

Results are saved to `game_results.json` and aggregated in the dashboard.

---

## 📦 Dependencies

See [`requirements.txt`](requirements.txt) for the full list. Key packages:

- `streamlit` — Dashboard UI
- `pygame` — Game rendering for Pygame-based games
- `plotly` — Interactive charts
- `altair` — Declarative visualizations
- `pandas` — Data manipulation

---

## 🤝 Contributing

Pull requests are welcome! To contribute:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
