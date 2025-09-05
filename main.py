# supply_app.py
from __future__ import annotations
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Tuple, Any


SUPPLIES_FILE: str = "./supplies.json"


# -------------------------------
# Data Manager
# -------------------------------
class SupplyData:
    def __init__(self, path: str = SUPPLIES_FILE) -> None:
        self.path: str = path
        self.sales_estimates: Dict[str, float] = {}
        self.supply_items: Dict[str, Tuple[float, str]] = {}
        self.dirty: bool = False

        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            # create empty file with defaults
            self.sales_estimates = {
                "Monday": 100.0,
                "Tuesday": 120.0,
                "Wednesday": 90.0,
                "Thursday": 110.0,
                "Friday": 150.0,
                "Saturday": 200.0,
                "Sunday": 130.0,
            }
            self.supply_items = {}
            self.save()
        else:
            with open(self.path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            self.sales_estimates = {
                k: float(v) for k, v in data.get("sales_estimates", {}).items()
            }
            self.supply_items = {
                k: tuple(v) for k, v in data.get("supply_items", {}).items()
            }

    def save(self) -> None:
        data: Dict[str, Any] = {
            "sales_estimates": self.sales_estimates,
            "supply_items": self.supply_items,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.dirty = False

    def add_item(self, name: str, coef: float, unit: str) -> None:
        self.supply_items[name] = (coef, unit)
        self.dirty = True


# -------------------------------
# GUI Application
# -------------------------------
class SupplyApp:
    def __init__(self, root: tk.Tk, data: SupplyData) -> None:
        self.root: tk.Tk = root
        self.data: SupplyData = data
        self.root.title("Restaurant Supply Calculator")

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.bind("<Control-s>", lambda event: self.save())

        # --- Frames
        self.days_frame: ttk.LabelFrame = ttk.LabelFrame(root, text="Select Days")
        self.days_frame.pack(padx=10, pady=10, fill="x")

        self.day_vars: Dict[str, tk.BooleanVar] = {}
        self.day_entries: Dict[str, ttk.Entry] = {}

        for day in self.data.sales_estimates:
            row: ttk.Frame = ttk.Frame(self.days_frame)
            row.pack(fill="x", pady=2)

            var: tk.BooleanVar = tk.BooleanVar()
            cb: ttk.Checkbutton = ttk.Checkbutton(row, text=day, variable=var)
            cb.pack(side="left")

            entry: ttk.Entry = ttk.Entry(row, width=8)
            entry.insert(0, str(self.data.sales_estimates[day]))
            entry.pack(side="left", padx=5)

            self.day_vars[day] = var
            self.day_entries[day] = entry

        # Optional override for total sales estimate
        self.override_frame: ttk.LabelFrame = ttk.LabelFrame(
            root, text="Override Sales Estimate"
        )
        self.override_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.override_frame, text="Total Sales ($):").pack(side="left", padx=5)
        self.override_entry: ttk.Entry = ttk.Entry(self.override_frame, width=10)
        self.override_entry.pack(side="left")

        self.calc_button: ttk.Button = ttk.Button(
            root, text="Calculate Supplies", command=self.calculate
        )
        self.calc_button.pack(pady=10)

        # Treeview
        self.tree: ttk.Treeview = ttk.Treeview(
            root, columns=("Item", "Coefficient", "Required", "Unit"), show="headings"
        )
        self.tree.heading("Item", text="Item")
        self.tree.heading("Coefficient", text="Coefficient")
        self.tree.heading("Required", text="Required")
        self.tree.heading("Unit", text="Unit")

        self.tree.column("Item", width=150, anchor="w")
        self.tree.column("Coefficient", width=100, anchor="center")
        self.tree.column("Required", width=100, anchor="center")
        self.tree.column("Unit", width=100, anchor="center")

        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

        # Buttons
        btn_frame: ttk.Frame = ttk.Frame(root)
        btn_frame.pack(pady=5, fill="x")

        ttk.Button(btn_frame, text="Add Item", command=self.add_item).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="Save Supplies Configuration", command=self.save).pack(
            side="right", padx=5
        )

    def calculate(self) -> None:
        """Calculate required supplies based on selected days and override input."""
        # Update sales_estimates from entries
        for day, entry in self.day_entries.items():
            try:
                self.data.sales_estimates[day] = float(entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", f"Invalid number for {day}")
                return
        self.data.dirty = True

        # Sum sales estimates for selected days
        total_sales: float = sum(
            self.data.sales_estimates[day]
            for day, var in self.day_vars.items()
            if var.get()
        )

        override: str = self.override_entry.get().strip()
        if override:
            try:
                total_sales = float(override)
            except ValueError:
                messagebox.showerror("Error", "Override must be a number")
                return

        for row in self.tree.get_children():
            self.tree.delete(row)

        for item, (coef, unit) in self.data.supply_items.items():
            required: float = total_sales * coef
            self.tree.insert("", "end", values=(item, coef, round(required, 2), unit))

        self.root.title(f"Restaurant Supply Calculator (Total Sales = {total_sales})")

    def add_item(self) -> None:
        """Prompt user to add a new supply item."""
        name: str | None = simpledialog.askstring("Add Item", "Item name:")
        if not name:
            return
        try:
            coef: float = float(
                simpledialog.askstring("Add Item", "Sales coefficient:", parent=self.root)
                or "0"
            )
        except ValueError:
            messagebox.showerror("Error", "Coefficient must be a number")
            return
        unit: str | None = simpledialog.askstring("Add Item", "Unit (e.g., kg, loaves):")
        if not unit:
            return
        self.data.add_item(name, coef, unit)
        messagebox.showinfo("Added", f"Item '{name}' added (unsaved changes).")

    def save(self) -> None:
        self.data.save()
        messagebox.showinfo("Saved", "Supplies configuration saved successfully.")

    def on_exit(self) -> None:
        if self.data.dirty:
            if messagebox.askyesno("Unsaved Changes", "Save changes before exit?"):
                self.data.save()
        self.root.destroy()


if __name__ == "__main__":
    root: tk.Tk = tk.Tk()
    data: SupplyData = SupplyData()
    app: SupplyApp = SupplyApp(root, data)
    root.mainloop()
