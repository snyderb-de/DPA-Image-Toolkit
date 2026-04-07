"""
Shared dependency sidebar UI for toolkit panels.
"""

from __future__ import annotations

import customtkinter as ctk

from .styles import RADIUS, get_font


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
        row.grid(row=index, column=0, sticky="ew", padx=14, pady=(12 if index == 0 else 0, 10))
        row.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(
            row,
            text="",
            font=get_font("small"),
            text_color=theme["fg_primary"],
            anchor="w",
            justify="left",
            wraplength=220,
        )
        label.grid(row=0, column=0, sticky="w")

        detail = ctk.CTkLabel(
            row,
            text="",
            font=get_font("micro"),
            text_color=theme["fg_tertiary"],
            anchor="w",
            justify="left",
            wraplength=220,
        )
        detail.grid(row=1, column=0, sticky="w", pady=(4, 0))
        dependency_rows.append((label, detail))

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
        ctk.CTkLabel(
            support_card,
            text=f"•  {line}",
            font=get_font("small"),
            text_color=theme["fg_secondary"],
            justify="left",
            wraplength=240,
            anchor="w",
        ).pack(anchor="w", padx=14, pady=(0, 8))

    refresh_dependency_sidebar(dependency_rows, statuses)
    return side_panel, dependency_rows


def refresh_dependency_sidebar(dependency_rows, statuses: list[dict]):
    for (label_widget, detail_widget), status in zip(dependency_rows, statuses):
        emoji = "✅" if status["ok"] else "❌"
        label_widget.configure(text=f"{emoji}  {status['label']}")
        detail_widget.configure(text=status["detail"])
