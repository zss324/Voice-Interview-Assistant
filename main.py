import sys

import asyncio  # noqa: E402

import qasync  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.client.gui import MainWindow  # noqa: E402


async def _main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()

    close_event = asyncio.Event()
    window.closed.connect(close_event.set)

    await close_event.wait()
    await window.shutdown()


def main() -> None:
    qasync.run(_main())


if __name__ == "__main__":
    if "--check-audio" in sys.argv:
        from src.modules.local_speech import check_audio_pipeline

        print(f"AUDIO_OK: {check_audio_pipeline()}", flush=True)
    else:
        main()
