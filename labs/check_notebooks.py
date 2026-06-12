"""Execute every course notebook code cell without requiring Jupyter."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
plt.show = lambda *args, **kwargs: None


def check_notebook(path: Path) -> int:
    notebook = json.loads(path.read_text())
    namespace = {"display": lambda *args, **kwargs: None}
    executed = 0
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        exec(compile(source, f"{path.name}:cell-{index}", "exec"), namespace)
        executed += 1
    plt.close("all")
    return executed


def main() -> None:
    notebooks = sorted((ROOT / "labs").glob("[0-9][0-9]-*/*.ipynb"))
    total_cells = 0
    for notebook in notebooks:
        cells = check_notebook(notebook)
        total_cells += cells
        print(f"{notebook.relative_to(ROOT)}: {cells} code cells passed")
    print(f"Notebook check passed: {len(notebooks)} notebooks, {total_cells} code cells.")


if __name__ == "__main__":
    main()
