# pos_printer.py — prints a chain log to a POS thermal printer.
#
# Usage:
# -----
#   python src/pos_printer.py               Print the most recent log.
#   python src/pos_printer.py --browse      List all saved logs and pick one to print.

import csv
import sys
from pathlib import Path

#  Printer connection type: "win32" | "usb" | "serial" | "network" 
PRINTER_CONNECTION = "win32"
# Windows print spooler: exact name from Settings → Printers & scanners.
WIN32_PRINTER_NAME = "POS CV2"
# USB: Vendor ID and Product ID from Device Manager → Hardware Ids.
USB_VID = 0x1FC9
USB_PID = 0x2016

# Serial (COM port): set port and baud rate.
SERIAL_PORT = "COM3"
SERIAL_BAUD = 9600

# Network: set IP and port.
NETWORK_HOST = "192.168.1.100"
NETWORK_PORT = 9100

#  Layout 
LINE_WIDTH   = 42        # characters per line (48 for 80 mm, 32 for 58 mm)
DIVIDER_CHAR = ":"       # character used for all divider lines
SEPARATOR    = "." * LINE_WIDTH  # dot line printed between hops


def _get_printer():
    """Return a connected python-escpos printer object."""
    try:
        from escpos import printer as ep
    except ImportError:
        sys.exit(
            "python-escpos is not installed.\n"
            "Run:  pip install python-escpos"
        )

    if PRINTER_CONNECTION == "win32":
        return ep.Win32Raw(WIN32_PRINTER_NAME)

    sys.exit(f"Unknown PRINTER_CONNECTION value: {PRINTER_CONNECTION!r}")

def _latest_log(logs_dir: Path) -> Path:
    """Return the most recently modified CSV in logs_dir."""
    csvs = sorted(logs_dir.glob("chain_*.csv"), key=lambda p: p.stat().st_mtime)
    if not csvs:
        sys.exit(f"No chain log CSVs found in {logs_dir}")
    return csvs[-1]

def _load_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def _inline_wrap(label: str, message: str, width: int) -> list[str]:
    """Put label and message on one line; overflow wraps left-aligned with no indent."""
    words   = message.split()
    result  = []
    current = label + " "

    for word in words:
        if current == label + " ":
            current += word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            result.append(current)
            current = word

    if current.strip():
        result.append(current)

    return result or [label]


def _divider() -> str:
    return DIVIDER_CHAR * LINE_WIDTH

def _build_receipt(rows: list[dict], log_filename: str) -> list[str]:
    """Return a list of text lines that make up the printed receipt."""
    lines: list[str] = []
    # Header
    title = "WHISPER CHAIN"
    lines.append(title.center(LINE_WIDTH))
    lines.append(_divider())
    lines.append(f"Hops: {len(rows)}")
    lines.append(_divider())
    lines.append("")

    rows = sorted(rows, key=lambda r: int(r["order"]))

    first_received = rows[0]["received"] if rows else ""
    lines.extend(_inline_wrap("[00] [ Original message ]:", first_received, LINE_WIDTH))

    for row in rows:
        lines.append("")
        lines.append(SEPARATOR)
        lines.append("")
        hop_num = int(row["order"]) + 1
        label = f"[{hop_num:02d}] [ {row['relay']} ]:"
        lines.extend(_inline_wrap(label, row["sent"], LINE_WIDTH))

    lines.append(_divider())
    lines.append("")
    lines.append("")   # feed before cut

    return lines

def print_receipt(csv_path: str | Path) -> None:
    """Load a chain log CSV and send it to the printer. Called from main.py."""
    csv_path = Path(csv_path)
    rows = _load_csv(csv_path)
    if not rows:
        raise ValueError(f"Log file is empty: {csv_path.name}")
    receipt_lines = _build_receipt(rows, csv_path.name)
    p = _get_printer()
    try:
        for line in receipt_lines:
            p.text(line + "\n")
        p.cut()
    finally:
        p.close()


def _browse(logs_dir: Path) -> Path | None:
    """List all chain logs and let the user pick one. Returns the chosen path or None."""
    csvs = sorted(logs_dir.glob("chain_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not csvs:
        print(f"No logs found in {logs_dir}")
        return None

    print()
    print("  Saved chain logs")
    print("  " + "-" * 40)
    for i, p in enumerate(csvs, 1):
        print(f"  [{i:>2}]  {p.name}")
    print()

    while True:
        raw = input("  Enter number to print (or q to quit): ").strip()
        if raw.lower() == "q":
            return None
        if raw.isdigit() and 1 <= int(raw) <= len(csvs):
            return csvs[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(csvs)}.")


#  Entry point 

def main() -> None:
    logs_dir = Path(__file__).resolve().parent.parent / "logs"

    if "--browse" in sys.argv:
        log_path = _browse(logs_dir)
        if log_path is None:
            sys.exit(0)
    else:
        log_path = _latest_log(logs_dir)

    print(f"Printing: {log_path.name}")
    try:
        print_receipt(log_path)
    except ValueError as e:
        sys.exit(str(e))
    print("Done.")


if __name__ == "__main__":
    main()
