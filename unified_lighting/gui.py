from __future__ import annotations

import asyncio
import logging
import threading
import tkinter as tk
from tkinter import colorchooser

from .config import AppConfig, ConfigError, load_config
from .controller import build_devices, close_all, connect_all, run_screen_sync, set_color_all, set_power_all
from .devices.base import LightDevice

logger = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    def __init__(self, widget: tk.Text):
        super().__init__()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.widget.after(0, self._append, msg)

    def _append(self, msg: str) -> None:
        self.widget.configure(state="normal")
        self.widget.insert("end", msg + "\n")
        self.widget.see("end")
        self.widget.configure(state="disabled")


class App(tk.Tk):
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__()
        self.title("LigthingControl")
        self.geometry("420x420")
        self.resizable(False, False)

        self.config_path = config_path
        self.config: AppConfig | None = None
        self.devices: list[LightDevice] = []
        self.ambilight_running = False
        self.ambilight_stop_event: asyncio.Event | None = None

        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.loop_thread.start()

        self._build_ui()
        self._setup_logging()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._submit(self._startup())

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _submit(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def _setup_logging(self) -> None:
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    def _build_ui(self) -> None:
        frame = tk.Frame(self, padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        power_frame = tk.LabelFrame(frame, text="Питание", padx=8, pady=8)
        power_frame.pack(fill="x", pady=4)
        tk.Button(power_frame, text="Включить", command=self.on_power_on).pack(
            side="left", expand=True, fill="x", padx=4
        )
        tk.Button(power_frame, text="Выключить", command=self.on_power_off).pack(
            side="left", expand=True, fill="x", padx=4
        )

        color_frame = tk.LabelFrame(frame, text="Цвет", padx=8, pady=8)
        color_frame.pack(fill="x", pady=4)
        tk.Button(color_frame, text="Выбрать цвет...", command=self.on_pick_color).pack(fill="x")

        ambilight_frame = tk.LabelFrame(frame, text="Динамическая подсветка", padx=8, pady=8)
        ambilight_frame.pack(fill="x", pady=4)
        self.ambilight_button = tk.Button(
            ambilight_frame, text="Запустить Ambilight", command=self.on_toggle_ambilight
        )
        self.ambilight_button.pack(fill="x")

        log_frame = tk.LabelFrame(frame, text="Журнал", padx=8, pady=8)
        log_frame.pack(fill="both", expand=True, pady=4)
        self.log_text = tk.Text(log_frame, height=12, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    async def _startup(self) -> None:
        try:
            self.config = load_config(self.config_path)
        except ConfigError as exc:
            logger.error("Ошибка конфигурации: %s", exc)
            return
        self.devices = build_devices(self.config)
        await connect_all(self.devices)
        logger.info("Готово. Устройства: %s", ", ".join(d.name for d in self.devices) or "нет включённых")

    def on_power_on(self) -> None:
        self._submit(set_power_all(self.devices, True))

    def on_power_off(self) -> None:
        self._submit(set_power_all(self.devices, False))

    def on_pick_color(self) -> None:
        _, hex_color = colorchooser.askcolor(title="Выберите цвет")
        if hex_color is None:
            return
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        self._submit(set_color_all(self.devices, (r, g, b)))

    def on_toggle_ambilight(self) -> None:
        if not self.ambilight_running:
            self.ambilight_running = True
            self.ambilight_stop_event = asyncio.Event()
            self.ambilight_button.config(text="Остановить Ambilight")
            self._submit(self._run_ambilight())
        else:
            self.ambilight_running = False
            self.ambilight_button.config(text="Запустить Ambilight")
            self._submit(self._signal_ambilight_stop())

    async def _signal_ambilight_stop(self) -> None:
        if self.ambilight_stop_event is not None:
            self.ambilight_stop_event.set()

    async def _run_ambilight(self) -> None:
        assert self.config is not None and self.ambilight_stop_event is not None
        try:
            await run_screen_sync(self.config, self.devices, self.ambilight_stop_event)
        except Exception:
            logger.exception("Ambilight остановлен из-за ошибки")
        finally:
            self.after(0, self._reset_ambilight_button)

    def _reset_ambilight_button(self) -> None:
        self.ambilight_running = False
        self.ambilight_button.config(text="Запустить Ambilight")

    def _on_close(self) -> None:
        async def _shutdown() -> None:
            if self.ambilight_stop_event is not None:
                self.ambilight_stop_event.set()
                await asyncio.sleep(0.2)
            await close_all(self.devices)

        try:
            self._submit(_shutdown()).result(timeout=5)
        except Exception:
            logger.exception("Ошибка при завершении работы")
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
