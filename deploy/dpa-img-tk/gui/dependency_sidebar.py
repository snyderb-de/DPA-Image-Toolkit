"""
Shared dependency sidebar UI for toolkit panels.
"""

from __future__ import annotations

import customtkinter as ctk
import tkinter as tk

from .styles import RADIUS, get_font

STATUS_ICON_SIZE = 20


def build_dependency_sidebar(
    parent,
    theme: dict,
    heading: str,
    statuses: list[dict],
    support_lines: tuple[str, ...] | list[str],
    width: int = 300,
):
    """
    Build a right-side dependency status panel and return its status row widgets.
    """
    side_panel = ctk.CTkFrame(
        parent,
        fg_color=theme["bg_secondary"],
        corner_radius=RADIUS["xl"],
        border_width=1,
        border_color=theme["border_subtle"],
        width=width,
    )
    side_panel.grid_propagate(False)

    side_inner = ctk.CTkFrame(side_panel, fg_color="transparent")
    side_inner.pack(fill="both", expand=True, padx=20, pady=20)
    side_inner.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        side_inner,
        text="DEPENDENCY CHECK",
        font=get_font("eyebrow"),
        text_color=theme["fg_tertiary"],
        anchor="w",
    ).grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        side_inner,
        text=heading,
        font=get_font("normal"),
        text_color=theme["fg_primary"],
        anchor="w",
        justify="left",
        wraplength=240,
    ).grid(row=1, column=0, sticky="w", pady=(6, 12))

    dep_frame = ctk.CTkFrame(
        side_inner,
        fg_color=theme["bg_glass"],
        corner_radius=RADIUS["lg"],
        border_width=1,
        border_color=theme["border_subtle"],
    )
    dep_frame.grid(row=2, column=0, sticky="ew")
    dep_frame.grid_columnconfigure(0, weight=1)

    dependency_rows = []
    for index, _status in enumerate(statuses):
        row = ctk.CTkFrame(dep_frame, fg_color="transparent")
        row.grid(row=index, column=0, sticky="ew", padx=14, pady=(10 if index == 0 else 4, 8))
        row.grid_columnconfigure(1, weight=1)

        icon = create_status_icon_canvas(
            row,
            background=theme["bg_glass"],
        )
        icon.grid(row=0, column=0, sticky="nw", padx=(0, 6), pady=(1, 0))

        label = ctk.CTkLabel(
            row,
            text="",
            font=get_font("small"),
            text_color=theme["fg_primary"],
            anchor="w",
            justify="left",
            wraplength=220,
        )
        label.grid(row=0, column=1, sticky="w")

        detail = ctk.CTkLabel(
            row,
            text="",
            font=get_font("micro"),
            text_color=theme["fg_tertiary"],
            anchor="w",
            justify="left",
            wraplength=220,
        )
        detail.grid(row=1, column=1, sticky="w", pady=(2, 0))
        dependency_rows.append((icon, label, detail))

    support_card = ctk.CTkFrame(
        side_inner,
        fg_color=theme["accent_dim"],
        corner_radius=RADIUS["lg"],
        border_width=0,
    )
    support_card.grid(row=3, column=0, sticky="ew", pady=(16, 0))

    ctk.CTkLabel(
        support_card,
        text="WHAT THIS MEANS",
        font=get_font("eyebrow"),
        text_color=theme["fg_tertiary"],
        anchor="w",
    ).pack(anchor="w", padx=14, pady=(14, 2))

    for line in support_lines:
        line_row = ctk.CTkFrame(support_card, fg_color="transparent")
        line_row.pack(fill="x", padx=14, pady=(0, 6), anchor="w")
        line_row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            line_row,
            text="•",
            font=get_font("small"),
            text_color=theme["fg_secondary"],
            anchor="n",
            width=10,
        ).grid(row=0, column=0, sticky="nw")

        leading_emoji, body = _split_leading_emoji(line)
        if leading_emoji:
            icon = create_status_icon_canvas(
                line_row,
                background=theme["accent_dim"],
            )
            draw_status_icon(icon, leading_emoji == "✅")
            icon.grid(row=0, column=1, sticky="nw", padx=(4, 6), pady=(1, 0))

        ctk.CTkLabel(
            line_row,
            text=body,
            font=get_font("small"),
            text_color=theme["fg_secondary"],
            justify="left",
            wraplength=190 if leading_emoji else 228,
            anchor="w",
        ).grid(row=0, column=2 if leading_emoji else 1, sticky="w")

    refresh_dependency_sidebar(dependency_rows, statuses)
    return side_panel, dependency_rows


def refresh_dependency_sidebar(dependency_rows, statuses: list[dict]):
    for (icon_widget, label_widget, detail_widget), status in zip(dependency_rows, statuses):
        draw_status_icon(icon_widget, status["ok"])
        label_widget.configure(text=status["label"])
        detail_widget.configure(text=status["detail"])


def _split_leading_emoji(text: str) -> tuple[str | None, str]:
    if text.startswith("✅ "):
        return "✅", text[2:].lstrip()
    if text.startswith("❌ "):
        return "❌", text[2:].lstrip()
    return None, text


def create_status_icon_canvas(parent, background: str):
    canvas = tk.Canvas(
        parent,
        width=STATUS_ICON_SIZE,
        height=STATUS_ICON_SIZE,
        bg=background,
        highlightthickness=0,
        bd=0,
        relief="flat",
    )
    return canvas


def draw_status_icon(canvas: tk.Canvas, ok: bool):
    canvas.delete("all")

    if ok:
        canvas.create_rectangle(
            2, 2, STATUS_ICON_SIZE - 2, STATUS_ICON_SIZE - 2,
            fill="#10B81A",
            outline="#0A9813",
            width=1,
        )
        canvas.create_line(
            6, 11,
            9, 15,
            16, 6,
            fill="#FFFFFF",
            width=3,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
        )
    else:
        canvas.create_line(
            5, 5,
            17, 17,
            fill="#FF1E1E",
            width=3,
            capstyle=tk.ROUND,
        )
        canvas.create_line(
            17, 5,
            5, 17,
            fill="#FF1E1E",
            width=3,
            capstyle=tk.ROUND,
        )
