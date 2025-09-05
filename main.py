# supply_app.py
import tkinter as tk
from tkinter import ttk, messagebox

# Hard-coded sales estimates per weekday
sales_estimates = {
    "Monday": 100,
    "Tuesday": 120,
    "Wednesday": 90,
    "Thursday": 110,
    "Friday": 150,
    "Saturday": 200,
    "Sunday": 130,
}

# Hard-coded supply items and coefficients
supply_items = {
    "Tomatoes (kg)": 0.05,
    "Cheese (kg)": 0.03,
    "Bread (loaves)": 0.02,
    "Chicken (kg)": 0.04,
}


class SupplyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Restaurant Supply Calculator")

        # Frame for weekday checkboxes
        self.days_frame = ttk.LabelFrame(root, text="Select Days")
        self.days_frame.pack(padx=10, pady=10, fill="x")

        self.day_vars = {}
        for day in sales_estimates:
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.days_frame, text=day, variable=var)
            cb.pack(anchor="w")
            self.day_vars[day] = var

        # Optional override for total sales estimate
        self.override_frame = ttk.LabelFrame(root, text="Override Sales Estimate")
        self.override_frame.pack(padx=10, pady=10, fill="x")

        ttk.Label(self.override_frame, text="Total Sales ($):").pack(side="left", padx=5)
        self.override_entry = ttk.Entry(self.override_frame, width=10)
        self.override_entry.pack(side="left")

        # Calculate button
        self.calc_button = ttk.Button(root, text="Calculate Supplies", command=self.calculate)
        self.calc_button.pack(pady=10)

        # Results table
        self.tree = ttk.Treeview(
            root, columns=("Item", "Coefficient", "Required"), show="headings"
        )
        self.tree.heading("Item", text="Item")
        self.tree.heading("Coefficient", text="Coefficient")
        self.tree.heading("Required", text="Required")

        self.tree.column("Item", width=150, anchor="w")
        self.tree.column("Coefficient", width=100, anchor="center")
        self.tree.column("Required", width=100, anchor="center")

        self.tree.pack(padx=10, pady=10, fill="both", expand=True)

    def calculate(self):
        # Sum sales estimates for selected days
        total_sales = sum(
            sales_estimates[day] for day, var in self.day_vars.items() if var.get()
        )

        # Override if provided
        override = self.override_entry.get().strip()
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
        for item, coef in supply_items.items():
            required = total_sales * coef
            self.tree.insert("", "end", values=(item, coef, round(required, 2)))

        # Show total in title
        self.root.title(f"Restaurant Supply Calculator (Total Sales = {total_sales})")


if __name__ == "__main__":
    root = tk.Tk()
    app = SupplyApp(root)
    root.mainloop()
