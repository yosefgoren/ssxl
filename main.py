# supply_app.py
from __future__ import annotations
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict
import sys
import jsonschema  # requires `pip install jsonschema`

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

SUPPLIES_FILE: str = "./supplies.json"
SCHEMA_FILE: str = resource_path(os.path.join("schema", "config_schema.json"))
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def find_day_idx(day: str) -> int:
    return DAYS.index(day)


# -------------------------------
# Data Manager
# -------------------------------
class SupplyData:
    # Type alias for clarity
    SalesEstimates = list[float]  # Monday..Sunday
    SupplyItems = dict[str, tuple[float, str, float, str]]  # coef, unit, inventory, supplier
    DarkMode = bool
    ConfigTuple = tuple[SalesEstimates, SupplyItems, DarkMode]

    def __init__(self, path: str = SUPPLIES_FILE) -> None:
        self.path: str = path
        self.sales_estimates: SupplyData.SalesEstimates = [0.0] * 7
        self.supply_items: SupplyData.SupplyItems = {}
        self.dark_mode: SupplyData.DarkMode = True
        self.dirty: bool = False

        self.load()

    def load(self) -> None:
        """Load configuration from JSON, validate against schema."""
        if not os.path.exists(self.path):
            # create default file
            self.save()
            return

        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load schema
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Validate structure
        jsonschema.validate(instance=data, schema=schema)

        # Destructure into fields
        self.sales_estimates, self.supply_items, self.dark_mode = data  # type: ignore

    def save(self) -> None:
        """Save configuration as JSON tuple."""
        config: SupplyData.ConfigTuple = (
            self.sales_estimates,
            self.supply_items,
            self.dark_mode,
        )
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        self.dirty = False

    def add_item(self, name: str) -> None:
        # coef, unit, inventory (default 0), supplier (default "")
        self.supply_items[name] = (0.0, "", 0.0, "")
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
        self.dark_mode_btn.pack(side='right', padx=10, pady=5)
        self.update_dark_mode_button()

        # --- Frames
        self.days_frame: ttk.LabelFrame = ttk.LabelFrame(root, text="Select Days")
        self.days_frame.pack(padx=10, pady=10, fill="x")

        self.day_vars: Dict[str, tk.BooleanVar] = {}
        self.day_entries: Dict[str, ttk.Entry] = {}

        for idx, day in enumerate(DAYS):
            row: ttk.Frame = ttk.Frame(self.days_frame)
            row.pack(fill="x", pady=2)

            var: tk.BooleanVar = tk.BooleanVar()
            cb: ttk.Checkbutton = ttk.Checkbutton(row, text=day, variable=var)
            cb.pack(side="left")

            entry: ttk.Entry = ttk.Entry(row, width=8)
            entry.insert(0, str(self.data.sales_estimates[idx]))
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

        # Treeview: include Inventory column (before Required)
        self.tree: ttk.Treeview = ttk.Treeview(
            root,
            columns=("Item", "Unit", "UPT Coefficient", "Inventory", "Supplier", "Required"),
            show="headings",
        )
        self.tree.heading("Item", text="Item")
        self.tree.heading("Unit", text="Unit")
        self.tree.heading("UPT Coefficient", text="UPT Coefficient")
        self.tree.heading("Inventory", text="Inventory")
        self.tree.heading("Supplier", text="Supplier")
        self.tree.heading("Required", text="Required")

        self.tree.column("Item", width=150, anchor="w")
        self.tree.column("Unit", width=100, anchor="center")
        self.tree.column("UPT Coefficient", width=100, anchor="center")
        self.tree.column("Inventory", width=100, anchor="center")
        self.tree.column("Supplier", width=150, anchor="w")
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

        # Bind double-click on table cells for editing
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # Make UI reactive:
        # - Recalculate when any day checkbox toggles
        for day, var in self.day_vars.items():
            var.trace_add("write", lambda *args: self.schedule_recalculate())

        # - Recalculate when day entries change (use key release and focus out)
        for entry in self.day_entries.values():
            entry.bind("<KeyRelease>", lambda e: self.schedule_recalculate())
            entry.bind("<FocusOut>", lambda e: self.schedule_recalculate())

        # - Recalculate when override entry changes
        self.override_entry.bind("<KeyRelease>", lambda e: self.schedule_recalculate())
        self.override_entry.bind("<FocusOut>", lambda e: self.schedule_recalculate())

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

        style.configure("Treeview", rowheight=28)  # was ~18 by default

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
            if not new_value and col_index != 4:  # allow empty supplier
                return

            item_values[col_index] = new_value
            self.tree.item(row_id, values=item_values)

            # Update back into supply_items
            item_name = item_values[0]
            try:
                coef = float(item_values[2])
            except ValueError:
                coef = 0.0
                self.show_message(f"Invalid coefficient for {item_name}, reset to 0")

            try:
                inventory = float(item_values[3])
            except ValueError:
                inventory = 0.0
                self.show_message(f"Invalid inventory for {item_name}, reset to 0")

            unit = item_values[1]
            supplier = item_values[4]

            self.data.supply_items[item_name] = (coef, unit, inventory, supplier)
            self.data.dirty = True
            self.show_message(f"Updated item: {item_name}")

            # Recalculate because the item was edited
            self.schedule_recalculate()

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
                self.data.sales_estimates[find_day_idx(day)] = float(entry.get().strip())
            except ValueError:
                self.show_message(f"Invalid number for {day}")
                return

        # Sum sales estimates for selected days
        total_sales: float = sum(
            self.data.sales_estimates[find_day_idx(day)]
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

        for item, (coef, unit, inventory, supplier) in self.data.supply_items.items():
            required: float = (total_sales/1000)*coef - inventory
            if required < 0:
                required = 0.0
            self.tree.insert(
                "", "end",
                values=(item, unit, coef, inventory, supplier, round(required, 3))
            )

        self.root.title(f"Restaurant Supply Calculator (Total Sales = {total_sales})")
        self.show_message("Calculation done")

    def schedule_recalculate(self, delay_ms: int = 150) -> None:
        """Schedule a single recalculation shortly after the last event."""
        # cancel previous if exists
        if hasattr(self, "_recalc_after_id") and self._recalc_after_id is not None:
            try:
                self.root.after_cancel(self._recalc_after_id)
            except Exception:
                pass
        self._recalc_after_id = self.root.after(delay_ms, self.calculate)

    def add_item(self) -> None:
        """Prompt user to add a new supply item."""
        name: str | None = simpledialog.askstring("Add Item", "Item Name:")
        self.data.add_item(name)
        self.schedule_recalculate()
        self.show_message(f"Item '{name}' added (unsaved changes)")

    def save(self) -> None:
        # Ensure latest entry values are stored before saving
        for day, entry in self.day_entries.items():
            try:
                self.data.sales_estimates[find_day_idx(day)] = float(entry.get().strip())
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
    got_bad_config_foramt = False
    try:
        data: SupplyData = SupplyData()
        app: SupplyApp = SupplyApp(root, data)
        root.mainloop()
    except jsonschema.ValidationError:
        got_bad_config_foramt = True
    
    if got_bad_config_foramt:
        raise RuntimeError(f"Configuration file {SUPPLIES_FILE} has an invalid format. Delete it or move it eleswhere so a new one can be created.")
