# supply_app.py
from __future__ import annotations
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Tuple, Any
import sys

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


SUPPLIES_FILE: str = "./supplies.json"


# -------------------------------
# Data Manager
# -------------------------------
class SupplyData:
    def __init__(self, path: str = SUPPLIES_FILE) -> None:
        self.path: str = path
        self.sales_estimates: Dict[str, float] = {}
        self.supply_items: Dict[str, Tuple[float, str]] = {}
        self.dark_mode: bool = True  # default dark
        self.dirty: bool = False

        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            # create empty file with defaults
            self.sales_estimates = {
                "Monday": 0.0,
                "Tuesday": 0.0,
                "Wednesday": 0.0,
                "Thursday": 0.0,
                "Friday": 0.0,
                "Saturday": 0.0,
                "Sunday": 0.0,
            }
            self.supply_items = {}
            self.dark_mode = True
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
            self.dark_mode = bool(data.get("dark_mode", True))

    def save(self) -> None:
        data: Dict[str, Any] = {
            "sales_estimates": self.sales_estimates,
            "supply_items": self.supply_items,
            "dark_mode": self.dark_mode,
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

        btn_frame: ttk.Frame = ttk.Frame(root)
        btn_frame.pack(pady=5, fill="x")

        # Dark mode toggle button
        self.dark_mode_btn: ttk.Button = ttk.Button(btn_frame, text="Dark Mode", command=self.toggle_dark_mode)
        self.dark_mode_btn.pack(pady=4)
        self.update_dark_mode_button()

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

        ttk.Label(self.override_frame, text="Total Sales:").pack(side="left", padx=5)
        self.override_entry: ttk.Entry = ttk.Entry(self.override_frame, width=10)
        self.override_entry.pack(side="left")

        self.calc_button: ttk.Button = ttk.Button(
            root, text="Calculate Supplies", command=self.calculate
        )
        self.calc_button.pack(pady=4)

        # Treeview
        self.tree: ttk.Treeview = ttk.Treeview(
            root, columns=("Item", "Unit", "UPT Coefficient", "Required"), show="headings"
        )
        self.tree.heading("Item", text="Item")
        self.tree.heading("Unit", text="Unit")
        self.tree.heading("UPT Coefficient", text="UPT Coefficient")
        self.tree.heading("Required", text="Required")

        self.tree.column("Item", width=150, anchor="w")
        self.tree.column("Unit", width=100, anchor="center")
        self.tree.column("UPT Coefficient", width=100, anchor="center")
        self.tree.column("Required", width=100, anchor="center")

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

        # --- Messages panel
        self.messages: list[str] = []
        self.messages_frame: ttk.Frame = ttk.Frame(root)
        self.messages_frame.pack(fill="x", padx=5, pady=5)

        self.latest_msg_var: tk.StringVar = tk.StringVar()
        self.latest_msg_label: ttk.Label = ttk.Label(
            self.messages_frame, textvariable=self.latest_msg_var, foreground="green"
        )
        self.latest_msg_label.pack(side="top", anchor="w", fill="x")

        self.expand_button: ttk.Button = ttk.Button(
            self.messages_frame, text="▼", width=2, command=self.toggle_messages
        )
        self.expand_button.pack(side="left")

        self.all_messages_visible: bool = False
        self.all_msgs_text: tk.Text = tk.Text(
            self.messages_frame, height=5, state="disabled"
        )
        self.all_msgs_text.pack(side="bottom", fill="x")
        self.all_msgs_text.pack_forget()

        # Bind double-click on table cells for editing
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Populate initial table (even before any days selected)
        self.calculate()
        self.apply_theme()  # apply saved dark/light mode

    # -------------------------------
    # Dark mode functions
    # -------------------------------
    def toggle_dark_mode(self) -> None:
        self.data.dark_mode = not self.data.dark_mode
        self.data.dirty = True
        self.update_dark_mode_button()
        self.show_message(f"Dark Mode {'enabled' if self.data.dark_mode else 'disabled'} for next startup.")

    def update_dark_mode_button(self) -> None:
        self.dark_mode_btn.configure(text=f"Dark Mode: {'ON' if self.data.dark_mode else 'OFF'}")

    def apply_theme(self) -> None:
        style = ttk.Style()
        theme_name = "breeze-dark" if self.data.dark_mode else "breeze"
        style.theme_use(theme_name)

    # -------------------------------
    # Messages system
    # -------------------------------
    def show_message(self, msg: str) -> None:
        self.messages.append(msg)
        self.latest_msg_var.set(msg)
        if self.all_messages_visible:
            self.all_msgs_text.configure(state="normal")
            self.all_msgs_text.delete("1.0", "end")
            self.all_msgs_text.insert("1.0", "\n".join(self.messages))
            self.all_msgs_text.configure(state="disabled")


    def toggle_messages(self) -> None:
        self.all_messages_visible = not self.all_messages_visible
        if self.all_messages_visible:
            self.all_msgs_text.pack(side="bottom", fill="x")
            self.expand_button.configure(text="▲")
            # Update content
            self.all_msgs_text.configure(state="normal")
            self.all_msgs_text.delete("1.0", "end")
            self.all_msgs_text.insert("1.0", "\n".join(self.messages))
            self.all_msgs_text.configure(state="disabled")
        else:
            self.all_msgs_text.pack_forget()
            self.expand_button.configure(text="▼")

    # -------------------------------
    # Table editing
    # -------------------------------
    def on_tree_double_click(self, event: tk.Event) -> None:
        """Allow editing of supply items directly in the table."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        # Get current value
        item_values = list(self.tree.item(row_id, "values"))
        col_index = int(col_id.replace("#", "")) - 1
        old_value = item_values[col_index]

        # Cell bbox
        x, y, w, h = self.tree.bbox(row_id, col_id)

        # Entry widget overlay
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, old_value)
        entry.focus()

        def save_edit(event: tk.Event | None = None) -> None:
            new_value = entry.get().strip()
            entry.destroy()
            if not new_value:
                return

            item_values[col_index] = new_value
            self.tree.item(row_id, values=item_values)

            # Update back into supply_items
            item_name = item_values[0]  # first column is Item name
            try:
                coef = float(item_values[1])
            except ValueError:
                coef = 0.0
                self.show_message(f"Invalid coefficient for {item_name}, reset to 0")
            unit = item_values[3]

            self.data.supply_items[item_name] = (coef, unit)
            self.data.dirty = True
            self.show_message(f"Updated item: {item_name}")

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)

    # -------------------------------
    # Main functions
    # -------------------------------
    def calculate(self) -> None:
        """Calculate required supplies based on selected days and override input."""
        # Update sales_estimates from entries
        for day, entry in self.day_entries.items():
            try:
                self.data.sales_estimates[day] = float(entry.get().strip())
            except ValueError:
                self.show_message(f"Invalid number for {day}")
                return

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
                self.show_message("Override must be a number")
                return

        for row in self.tree.get_children():
            self.tree.delete(row)

        for item, (coef, unit) in self.data.supply_items.items():
            required: float = total_sales/1000 * coef
            self.tree.insert("", "end", values=(item, unit, coef, round(required, 3)))

        self.root.title(f"Restaurant Supply Calculator (Total Sales = {total_sales})")
        self.show_message("Calculation done")

    def add_item(self) -> None:
        """Prompt user to add a new supply item."""
        name: str | None = simpledialog.askstring("Add Item", "Item Name:")
        unit: str | None = simpledialog.askstring("Add Item", "Unit (e.g., kg, loaves):")
        if not unit:
            return
        if not name:
            return
        try:
            coef: float = float(
                simpledialog.askstring("Add Item", "UPT Coefficient:", parent=self.root)
                or "0"
            )
        except ValueError:
            self.show_message("Coefficient must be a number")
            return
        self.data.add_item(name, coef, unit)
        self.show_message(f"Item '{name}' added (unsaved changes)")

    def save(self) -> None:
        # Ensure latest entry values are stored before saving
        for day, entry in self.day_entries.items():
            try:
                self.data.sales_estimates[day] = float(entry.get().strip())
            except ValueError:
                self.show_message(f"Invalid number for {day}")
                return

        self.data.save()
        self.show_message("Supplies configuration saved successfully")

    def on_exit(self) -> None:
        if self.data.dirty:
            if messagebox.askyesno("Unsaved Changes", "Save changes before exit?"):
                self.data.save()
        self.root.destroy()


def load_custom_theme(root: tk.Tk) -> None:
    # Path to .tcl file
    
    themes_index_path = resource_path(os.path.join("theme", "pkgIndex.tcl"))
    root.tk.call("source", themes_index_path)


if __name__ == "__main__":
    root: tk.Tk = tk.Tk()
    load_custom_theme(root)
    data: SupplyData = SupplyData()
    app: SupplyApp = SupplyApp(root, data)
    root.mainloop()
