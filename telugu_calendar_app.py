#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Telugu calendar app using Tkinter.
Shows the Gregorian calendar with Telugu month and day names.
"""

import calendar
import datetime
import tkinter as tk
from tkinter import ttk


TELUGU_MONTHS = [
    "జనవరి",
    "ఫిబ్రవరి",
    "మార్చి",
    "ఏప్రిల్",
    "మే",
    "జూన్",
    "జూలై",
    "ఆగస్టు",
    "సెప్టెంబర్",
    "అక్టోబర్",
    "నవంబర్",
    "డిసెంబర్",
]

TELUGU_DAYS = ["ఆది", "సోమ", "మంగళ", "బుధ", "గురు", "శుక్ర", "శని"]

SELECTED_BG = "#cde7ff"
TODAY_BG = "#c7f7c4"


class TeluguCalendarApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.calendar = calendar.Calendar(firstweekday=6)  # Sunday first
        self.today = datetime.date.today()
        self.current_year = self.today.year
        self.current_month = self.today.month
        self.day_buttons = {}
        self.selected_button = None

        self.root.title("తెలుగు క్యాలెండర్")
        self.root.configure(padx=12, pady=12)

        self._build_header()
        self._build_day_headers()
        self._build_grid()
        self._build_footer()
        self.render_calendar()
        self.set_status("ఈ రోజు", self.today)

    def _build_header(self) -> None:
        header = ttk.Frame(self.root)
        header.pack(fill="x")

        prev_button = ttk.Button(header, text="◀", command=lambda: self.change_month(-1))
        prev_button.pack(side="left")

        self.month_label = ttk.Label(header, text="", anchor="center", font=("Arial", 16, "bold"))
        self.month_label.pack(side="left", expand=True, padx=10)

        next_button = ttk.Button(header, text="▶", command=lambda: self.change_month(1))
        next_button.pack(side="right")

    def _build_day_headers(self) -> None:
        day_header = ttk.Frame(self.root)
        day_header.pack(fill="x", pady=(10, 0))
        for day_name in TELUGU_DAYS:
            label = ttk.Label(day_header, text=day_name, anchor="center", width=6)
            label.pack(side="left", expand=True)

    def _build_grid(self) -> None:
        self.grid_frame = ttk.Frame(self.root)
        self.grid_frame.pack(pady=6)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self.root)
        footer.pack(fill="x", pady=(6, 0))

        today_button = ttk.Button(footer, text="ఈ రోజు", command=self.go_today)
        today_button.pack(side="left")

        self.status_label = ttk.Label(footer, text="", anchor="center")
        self.status_label.pack(side="left", expand=True, padx=10)

    def format_telugu_date(self, date_value: datetime.date) -> str:
        day_name = TELUGU_DAYS[(date_value.weekday() + 1) % 7]
        return f"{day_name} | {date_value.day} {TELUGU_MONTHS[date_value.month - 1]} {date_value.year}"

    def set_status(self, label: str, date_value: datetime.date) -> None:
        self.status_label.config(text=f"{label}: {self.format_telugu_date(date_value)}")

    def change_month(self, delta: int) -> None:
        month = self.current_month + delta
        year = self.current_year
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        self.set_month(year, month)

    def set_month(self, year: int, month: int) -> None:
        self.current_year = year
        self.current_month = month
        self.render_calendar()

    def render_calendar(self) -> None:
        self.month_label.config(text=f"{TELUGU_MONTHS[self.current_month - 1]} {self.current_year}")

        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.day_buttons = {}
        self.selected_button = None

        month_days = self.calendar.monthdayscalendar(self.current_year, self.current_month)
        for row_index, week in enumerate(month_days):
            for col_index, day in enumerate(week):
                if day == 0:
                    spacer = ttk.Label(self.grid_frame, text="", width=6)
                    spacer.grid(row=row_index, column=col_index, padx=2, pady=2)
                    continue

                button = tk.Button(
                    self.grid_frame,
                    text=str(day),
                    width=4,
                )
                button.grid(row=row_index, column=col_index, padx=2, pady=2)

                if (
                    self.current_year == self.today.year
                    and self.current_month == self.today.month
                    and day == self.today.day
                ):
                    button.config(bg=TODAY_BG)

                button.default_bg = button.cget("bg")
                button.config(command=lambda d=day, b=button: self.select_day(d, b))
                self.day_buttons[day] = button

    def highlight_button(self, button: tk.Button) -> None:
        if self.selected_button and self.selected_button is not button:
            self.selected_button.config(bg=self.selected_button.default_bg, relief=tk.RAISED)
        self.selected_button = button
        button.config(bg=SELECTED_BG, relief=tk.SUNKEN)

    def select_day(self, day: int, button: tk.Button) -> None:
        self.highlight_button(button)
        selected = datetime.date(self.current_year, self.current_month, day)
        self.set_status("ఎంచుకున్న తేదీ", selected)

    def go_today(self) -> None:
        self.set_month(self.today.year, self.today.month)
        button = self.day_buttons.get(self.today.day)
        if button:
            self.highlight_button(button)
        self.set_status("ఈ రోజు", self.today)


def main() -> None:
    root = tk.Tk()
    TeluguCalendarApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
