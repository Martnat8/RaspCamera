import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from gpiozero import Button

from camera_utils import (
    get_run_dir,
    get_log_file,
    init_log,
    append_log_row,
    capture_image_gphoto2,
)

# BCM numbering
TRIGGER_GPIO = 17
ENABLE_GPIO  = 27


def main():
    run_dir = get_run_dir()
    log_file = get_log_file(run_dir)
    init_log(log_file)

    trigger = Button(TRIGGER_GPIO, pull_up=False, bounce_time=0.05)
    enable  = Button(ENABLE_GPIO,  pull_up=False)

    t0 = time.monotonic()
    idx = 0

    print("Pi trigger listener running")
    print(f"Trigger: GPIO {TRIGGER_GPIO}")
    print(f"Enable : GPIO {ENABLE_GPIO}")
    print(f"Run dir: {run_dir}")
    print(f"Log    : {log_file}")

    # Queue of pending events: (idx, elapsed, enable_state, stem)
    pending = deque()

    def on_trigger():
        nonlocal idx
        # Only queue events when enable is ON at the moment of the trigger edge
        if not enable.is_pressed:
            return

        idx += 1
        elapsed = time.monotonic() - t0
        en = int(enable.is_pressed)
        stem = f"img_{idx:06d}"
        pending.append((idx, elapsed, en, stem))

    trigger.when_pressed = on_trigger

    # One worker so camera commands never overlap
    executor = ThreadPoolExecutor(max_workers=1)
    in_flight = None  # (future, idx, elapsed, en, stem)

    try:
        while True:
            # If nothing in flight and we have pending triggers, start next capture
            if in_flight is None and pending:
                i, elapsed, en, stem = pending.popleft()
                fut = executor.submit(capture_image_gphoto2, run_dir, stem)
                in_flight = (fut, i, elapsed, en, stem)

            # If a capture finished, log it
            if in_flight is not None:
                fut, i, elapsed, en, stem = in_flight
                if fut.done():
                    ok, saved_name, msg = fut.result()
                    image_label = saved_name if ok else f"{stem}_%03n.%C"

                    append_log_row(log_file, [i, f"{elapsed:.6f}", en, image_label, int(ok), msg])
                    print(f"#{i}  t={elapsed:.3f}s  enable={en}  file={image_label}  ok={ok}  msg={msg}")

                    in_flight = None

            time.sleep(0.01)  # small idle to reduce CPU

    except KeyboardInterrupt:
        print("\nStopping (Ctrl+C).")
    finally:
        executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
