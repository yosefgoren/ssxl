# supply_app.py
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Tuple


# Hard-coded sales estimates per weekday
sales_estimates: Dict[str, float] = {
    "Monday": 100.0,
    "Tuesday": 120.0,
    "Wednesday": 90.0,
    "Thursday": 110.0,
    "Friday": 150.0,
    "Saturday": 200.0,
    "Sunday": 130.0,
}

# Hard-coded supply items: name -> (coefficient, unit)
supply_items: Dict[str, Tuple[float, str]] = {
    "Tomatoes": (0.05, "kg"),
    "Cheese": (0.03, "kg"),
    "Bread": (0.02, "loaves"),
    "Chicken": (0.04, "kg"),
}


class SupplyApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root: tk.Tk = root
        self.root.title("Restaurant Supply Calculator")

        # Frame for weekday checkboxes
        self.days_frame: ttk.LabelFrame = ttk.LabelFrame(root, text="Select Days")
        self.days_frame.pack(padx=10, pady=10, fill="x")

        self.day_vars: Dict[str, tk.BooleanVar] = {}
        for day in sales_estimates:
            var: tk.BooleanVar = tk.BooleanVar()
            cb: ttk.Checkbutton = ttk.Checkbutton(self.days_frame, text=day, variable=var)
            cb.pack(anchor="w")
            self.day_vars[day] = var

        # Optional override for total sales estimate
        self.override_frame: ttk.LabelFrame = ttk.LabelFrame(root, text="Override Sales Estimate")
        self.override_frame.pack(padx=10, pady=10, fill="x")

        lbl: ttk.Label = ttk.Label(self.override_frame, text="Total Sales ($):")
        lbl.pack(side="left", padx=5)

        self.override_entry: ttk.Entry = ttk.Entry(self.override_frame, width=10)
        self.override_entry.pack(side="left")

        # Calculate button
        self.calc_button: ttk.Button = ttk.Button(
            root, text="Calculate Supplies", command=self.calculate
        )
        self.calc_button.pack(pady=10)

        # Results table
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

    def calculate(self) -> None:
        """Calculate required supplies based on selected days and override input."""
        # Sum sales estimates for selected days
        total_sales: float = sum(
            sales_estimates[day] for day, var in self.day_vars.items() if var.get()
        )

        # Override if provided
        override: str = self.override_entry.get().strip()
        if override:
            try:
                total_sales = float(override)
            except ValueError:
                messagebox.showerror("Error", "Override must be a number")
                return

        # Clear previous results
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Populate results
        for item, (coef, unit) in supply_items.items():
            required: float = total_sales * coef
            self.tree.insert("", "end", values=(item, coef, round(required, 2), unit))

        # Show total in title
        self.root.title(f"Restaurant Supply Calculator (Total Sales = {total_sales})")


if __name__ == "__main__":
    root: tk.Tk = tk.Tk()
    app: SupplyApp = SupplyApp(root)
    root.mainloop()
