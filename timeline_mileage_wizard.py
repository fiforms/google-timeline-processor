#!/usr/bin/env python3
"""Simple desktop wizard for the Google Timeline mileage report."""

from __future__ import annotations

from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit(
        "Tkinter is not available in this Python installation. "
        "Install the OS package that provides Tk support, then run the wizard again."
    ) from exc

from timeline_mileage_report import run_report


class WizardApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Timeline Mileage Wizard")
        self.geometry("760x560")
        self.minsize(720, 520)

        self.input_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.config_path = tk.StringVar()
        self.timezone = tk.StringVar(value="America/New_York")
        self.status_text = tk.StringVar(value="Ready.")
        self.report_created = False
        self.current_step = 0
        self.steps: list[ttk.Frame] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()
        self._show_step(0)

    def _build_header(self) -> None:
        header = ttk.Frame(self, padding=(18, 18, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Google Timeline Mileage Report",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Follow the steps to export Timeline data from Android and build CSV reports.",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_body(self) -> None:
        self.body = ttk.Frame(self, padding=(18, 8, 18, 8))
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)

        self.steps = [
            self._build_intro_step(),
            self._build_input_step(),
            self._build_options_step(),
            self._build_run_step(),
        ]

        for frame in self.steps:
            frame.grid(row=0, column=0, sticky="nsew")

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(18, 8, 18, 18))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)

        self.back_button = ttk.Button(footer, text="Back", command=self._go_back)
        self.back_button.grid(row=0, column=0, sticky="w")

        ttk.Label(footer, textvariable=self.status_text).grid(
            row=0, column=1, sticky="w", padx=16
        )

        self.next_button = ttk.Button(footer, text="Next", command=self._go_next)
        self.next_button.grid(row=0, column=2, sticky="e")

    def _build_intro_step(self) -> ttk.Frame:
        frame = ttk.Frame(self.body)
        frame.columnconfigure(0, weight=1)

        instructions = (
            "Before you start:\n\n"
            "1. On your Android phone, open Settings.\n"
            "2. Go to Location > Location services > Timeline.\n"
            "3. Tap Export Timeline data.\n"
            "4. Move the exported JSON file to this computer.\n\n"
            "This wizard will turn that JSON export into three CSV files:\n"
            "- a daily mileage summary\n"
            "- a trip-by-trip detail report\n"
            "- a visit list to help identify business destinations\n"
        )
        ttk.Label(frame, text="Step 1 of 4: Export From Your Phone", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )
        ttk.Label(frame, text=instructions, justify="left", wraplength=680).grid(
            row=1, column=0, sticky="nw"
        )
        return frame

    def _build_input_step(self) -> ttk.Frame:
        frame = ttk.Frame(self.body)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Step 2 of 4: Choose Timeline Export", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )
        ttk.Label(
            frame,
            text="Select either a single JSON export file or a folder containing Timeline JSON files.",
            wraplength=680,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Timeline file or folder:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.input_path).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0)
        )
        ttk.Button(frame, text="Choose File", command=self._choose_input_file).grid(
            row=3, column=2, sticky="ew", padx=(8, 0)
        )
        ttk.Button(frame, text="Choose Folder", command=self._choose_input_folder).grid(
            row=4, column=2, sticky="ew", padx=(8, 0), pady=(8, 0)
        )
        return frame

    def _build_options_step(self) -> ttk.Frame:
        frame = ttk.Frame(self.body)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Step 3 of 4: Save Location And Options", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(frame, text="Output folder:").grid(row=1, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_dir).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ttk.Button(frame, text="Browse", command=self._choose_output_dir).grid(
            row=1, column=2, sticky="ew", padx=(8, 0)
        )

        ttk.Label(frame, text="Timezone:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        timezone_box = ttk.Combobox(
            frame,
            textvariable=self.timezone,
            values=[
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "America/Phoenix",
                "UTC",
            ],
            state="normal",
        )
        timezone_box.grid(row=2, column=1, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Classification config (optional):").grid(
            row=3, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Entry(frame, textvariable=self.config_path).grid(
            row=3, column=1, sticky="ew", pady=(12, 0)
        )
        ttk.Button(frame, text="Browse", command=self._choose_config_file).grid(
            row=3, column=2, sticky="ew", padx=(8, 0), pady=(12, 0)
        )

        ttk.Label(
            frame,
            text=(
                "If you leave the classification config empty, the report still runs. "
                "You can use classification.example.json as a starting point."
            ),
            wraplength=680,
            justify="left",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(16, 0))
        return frame

    def _build_run_step(self) -> ttk.Frame:
        frame = ttk.Frame(self.body)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="Step 4 of 4: Build Report", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        self.review_text = tk.Text(frame, height=14, wrap="word", state="disabled")
        self.review_text.grid(row=1, column=0, sticky="nsew")
        frame.rowconfigure(1, weight=1)

        ttk.Button(frame, text="Create Report", command=self._run_report).grid(
            row=2, column=0, sticky="e", pady=(12, 0)
        )
        return frame

    def _show_step(self, index: int) -> None:
        self.current_step = index
        self.steps[index].tkraise()
        self.back_button.configure(state="normal" if index > 0 else "disabled")
        self.next_button.configure(
            text="Close" if index == len(self.steps) - 1 else "Next",
            command=self.destroy if index == len(self.steps) - 1 else self._go_next,
        )
        if index == len(self.steps) - 1 and not self.report_created:
            self.next_button.configure(state="disabled")
        elif index != len(self.steps) - 1:
            self.next_button.configure(state="normal")
        if index == len(self.steps) - 1:
            self._refresh_review()

    def _go_back(self) -> None:
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

    def _go_next(self) -> None:
        if self.current_step == 1 and not self.input_path.get().strip():
            messagebox.showerror("Missing file", "Choose a Timeline JSON file or folder first.")
            return
        if self.current_step == 2 and not self.output_dir.get().strip():
            messagebox.showerror("Missing folder", "Choose an output folder first.")
            return
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)

    def _choose_input_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Choose Timeline JSON export",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            self.input_path.set(chosen)

    def _choose_input_folder(self) -> None:
        chosen = filedialog.askdirectory(title="Choose folder with Timeline JSON files")
        if chosen:
            self.input_path.set(chosen)

    def _choose_output_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self.output_dir.set(chosen)

    def _choose_config_file(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Choose classification config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            self.config_path.set(chosen)

    def _refresh_review(self) -> None:
        lines = [
            "Review these settings before creating the report.\n",
            f"Timeline input: {self.input_path.get() or '(not selected)'}",
            f"Output folder: {self.output_dir.get() or '(not selected)'}",
            f"Timezone: {self.timezone.get() or '(not set)'}",
            f"Classification config: {self.config_path.get() or '(none)'}",
            "",
            "Output files:",
            "- daily_summary.csv",
            "- trip_details.csv",
            "- visit_details.csv",
        ]
        self.review_text.configure(state="normal")
        self.review_text.delete("1.0", "end")
        self.review_text.insert("1.0", "\n".join(lines))
        self.review_text.configure(state="disabled")

    def _run_report(self) -> None:
        input_value = self.input_path.get().strip()
        output_value = self.output_dir.get().strip()
        config_value = self.config_path.get().strip() or None
        timezone_value = self.timezone.get().strip() or "America/New_York"

        if not input_value:
            messagebox.showerror("Missing file", "Choose a Timeline JSON file or folder first.")
            return
        if not output_value:
            messagebox.showerror("Missing folder", "Choose an output folder first.")
            return

        try:
            self.status_text.set("Building report...")
            self.update_idletasks()
            result = run_report(
                inputs=[input_value],
                output_dir=output_value,
                timezone=timezone_value,
                config_path=config_value,
            )
        except Exception as exc:  # noqa: BLE001
            self.status_text.set("Report failed.")
            messagebox.showerror("Report failed", str(exc))
            return

        self.report_created = True
        self.status_text.set("Report created successfully.")
        self.next_button.configure(state="normal")
        message = (
            f"Processed {result['files_processed']} JSON file(s).\n\n"
            f"Days summarized: {result['days_summarized']}\n"
            f"Trips found: {result['trip_count']}\n"
            f"Visits found: {result['visit_count']}\n\n"
            f"Saved:\n"
            f"{result['daily_summary_path']}\n"
            f"{result['trip_details_path']}\n"
            f"{result['visit_details_path']}"
        )
        messagebox.showinfo("Report ready", message)


def main() -> int:
    app = WizardApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
