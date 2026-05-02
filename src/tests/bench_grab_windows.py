"""Quick benchmark for Windows grab performance.

This script measures the performance of the Windows GDI grab implementation
using CreateDIBSection.

Run with: python -m tests.bench_grab_windows
         python -m tests.bench_grab_windows timing
         python -m tests.bench_grab_windows raw
         python -m tests.bench_grab_windows threads --mode same
         python -m tests.bench_grab_windows dc
"""

from __future__ import annotations

import argparse
import sys
import threading
from time import perf_counter
from typing import TYPE_CHECKING, Any

import mss

if TYPE_CHECKING:
    from collections.abc import Callable

    from mss.models import Monitor

ITERATIONS = 500
WARMUP_ITERATIONS = 10
THREADS = 2


def _print_result(label: str, iterations: int, elapsed: float) -> tuple[float, float]:
    avg_ms = elapsed / iterations * 1000
    fps = iterations / elapsed
    print(f"{label}: {avg_ms:.2f}ms ({fps:.1f} FPS)")
    return avg_ms, fps


def _run_loop(iterations: int, func: Callable[[], object]) -> float:
    start = perf_counter()
    for _ in range(iterations):
        func()
    return perf_counter() - start


def _primary_monitor(sct: mss.MSS) -> Monitor:
    return sct.monitors[1]


def _create_dib(gdi: Any, memdc: Any, bmi: Any) -> Any:
    import ctypes  # noqa: PLC0415

    from mss.windows import gdi as wingdi  # noqa: PLC0415

    dib_bits = wingdi.LPVOID()
    return gdi.CreateDIBSection(
        memdc,
        bmi,
        wingdi.DIB_RGB_COLORS,
        ctypes.byref(dib_bits),
        None,
        0,
    )


def _start_and_join(threads: list[threading.Thread], start_delay: float) -> None:
    for index, thread in enumerate(threads):
        thread.start()
        if start_delay and index < len(threads) - 1:
            threading.Event().wait(start_delay)
    for thread in threads:
        thread.join()


def _region_from_monitor(monitor: Monitor, width: int | None, height: int | None) -> Monitor:
    return {
        "left": monitor["left"],
        "top": monitor["top"],
        "width": monitor["width"] if width is None else width,
        "height": monitor["height"] if height is None else height,
    }


def benchmark_grab(iterations: int = ITERATIONS, warmup_iterations: int = WARMUP_ITERATIONS) -> tuple[float, float]:
    """Benchmark the grab operation on the primary monitor.

    Returns (avg_ms, fps) for comparison.
    """
    with mss.MSS() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        width, height = monitor["width"], monitor["height"]

        print(f"Platform: {sys.platform}")
        print(f"Region: {width}x{height}")
        print(f"Iterations: {iterations}")
        print()

        # Warmup - let any JIT/caching settle
        for _ in range(warmup_iterations):
            sct.grab(monitor)

        # Benchmark
        elapsed = _run_loop(iterations, lambda: sct.grab(monitor))

        avg_ms, fps = _print_result("Avg per grab", iterations, elapsed)

        print(f"Total time: {elapsed:.3f}s")

        return avg_ms, fps


def benchmark_grab_varying_sizes(
    iterations: int = ITERATIONS,
    warmup_iterations: int = WARMUP_ITERATIONS,
) -> None:
    """Benchmark grab at different region sizes to see scaling behavior."""
    sizes = [
        (100, 100),
        (640, 480),
        (1280, 720),
        (1920, 1080),
    ]

    print("\nVarying size benchmark:")
    print("-" * 50)

    with mss.MSS() as sct:
        for width, height in sizes:
            monitor = {"top": 0, "left": 0, "width": width, "height": height}

            # Warmup
            for _ in range(warmup_iterations):
                sct.grab(monitor)

            # Benchmark
            elapsed = _run_loop(iterations, lambda monitor=monitor: sct.grab(monitor))
            _print_result(f"  {width}x{height}", iterations, elapsed)


def benchmark_raw_bitblt(iterations: int = ITERATIONS) -> None:
    """Benchmark raw BitBlt to isolate GDI performance from Python overhead."""
    if sys.platform != "win32":
        print("Raw BitBlt benchmark is only available on Windows.")
        return

    import ctypes  # noqa: PLC0415
    from ctypes.wintypes import BOOL, DWORD, HDC, INT  # noqa: PLC0415

    import mss.windows  # noqa: PLC0415

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    # Get function references (names match Windows API)
    bitblt = gdi32.BitBlt
    bitblt.argtypes = [HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD]
    bitblt.restype = BOOL

    gdiflush = gdi32.GdiFlush
    gdiflush.argtypes = []
    gdiflush.restype = BOOL

    srccopy = 0x00CC0020
    captureblt = 0x40000000

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        width, height = monitor["width"], monitor["height"]
        left, top = monitor["left"], monitor["top"]

        # Acquire DCs directly for raw benchmarking (the impl no longer
        # holds them as instance state — they are per-grab now).
        srcdc = user32.GetWindowDC(0)
        memdc = gdi32.CreateCompatibleDC(srcdc)

        print(f"Raw BitBlt benchmark ({width}x{height})")
        print("=" * 50)

        try:
            # Test with CAPTUREBLT
            start = perf_counter()
            for _ in range(ITERATIONS):
                bitblt(memdc, 0, 0, width, height, srcdc, left, top, srccopy | captureblt)
                gdiflush()
            elapsed = perf_counter() - start
            print(f"With CAPTUREBLT:    {elapsed / ITERATIONS * 1000:.2f}ms ({ITERATIONS / elapsed:.1f} FPS)")

            # Test without CAPTUREBLT
            start = perf_counter()
            for _ in range(ITERATIONS):
                bitblt(memdc, 0, 0, width, height, srcdc, left, top, srccopy)
                gdiflush()
            elapsed = perf_counter() - start
            print(f"Without CAPTUREBLT: {elapsed / ITERATIONS * 1000:.2f}ms ({ITERATIONS / elapsed:.1f} FPS)")
        finally:
            gdi32.DeleteDC(memdc)
            user32.ReleaseDC(0, srcdc)


def benchmark_raw_dc_allocation(
    *,
    iterations: int = ITERATIONS,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Compare raw BitBlt with cached DCs against per-iteration DC allocation."""
    if sys.platform != "win32":
        print("Raw DC allocation benchmark is only available on Windows.")
        return

    import mss.windows  # noqa: PLC0415

    with mss.MSS() as sct:
        region = _region_from_monitor(_primary_monitor(sct), width, height)
        width, height = region["width"], region["height"]
        left, top = region["left"], region["top"]

        # Force region setup so the current backend has a DIB selected into its cached memory DC.
        sct.grab(region)

        assert isinstance(sct._impl, mss.windows.gdi.MSSImplGdi)
        impl = sct._impl

        gdi = impl.gdi32
        user32 = impl.user32

        print(f"Raw DC allocation benchmark ({width}x{height})")
        print("=" * 50)

        setup_srcdc = user32.GetWindowDC(0)
        setup_memdc = gdi.CreateCompatibleDC(setup_srcdc)

        cached_dib = _create_dib(gdi, setup_memdc, impl._bmi)
        fresh_dib = _create_dib(gdi, setup_memdc, impl._bmi)
        cached_srcdc = user32.GetWindowDC(0)
        cached_memdc = gdi.CreateCompatibleDC(cached_srcdc)
        old_cached_obj = gdi.SelectObject(cached_memdc, cached_dib)

        try:
            def cached_dc() -> None:
                gdi.BitBlt(
                    cached_memdc,
                    0,
                    0,
                    width,
                    height,
                    cached_srcdc,
                    left,
                    top,
                    0x00CC0020 | 0x40000000,
                )
                gdi.GdiFlush()

            def fresh_dc() -> None:
                srcdc = user32.GetWindowDC(0)
                memdc = gdi.CreateCompatibleDC(srcdc)
                old_obj = gdi.SelectObject(memdc, fresh_dib)
                try:
                    gdi.BitBlt(memdc, 0, 0, width, height, srcdc, left, top, 0x00CC0020 | 0x40000000)
                    gdi.GdiFlush()
                finally:
                    gdi.SelectObject(memdc, old_obj)
                    gdi.DeleteDC(memdc)
                    user32.ReleaseDC(0, srcdc)

            _print_result("Cached DC raw BitBlt", iterations, _run_loop(iterations, cached_dc))
            _print_result("Fresh DC raw BitBlt ", iterations, _run_loop(iterations, fresh_dc))
        finally:
            gdi.SelectObject(cached_memdc, old_cached_obj)
            gdi.DeleteDC(cached_memdc)
            user32.ReleaseDC(0, cached_srcdc)
            gdi.DeleteObject(cached_dib)
            gdi.DeleteObject(fresh_dib)
            gdi.DeleteDC(setup_memdc)
            user32.ReleaseDC(0, setup_srcdc)


def benchmark_threaded_grab(
    *,
    iterations: int = ITERATIONS,
    thread_count: int = THREADS,
    mode: str = "same",
    start_delay: float = 0.0,
    warmup_iterations: int = WARMUP_ITERATIONS,
) -> None:
    """Benchmark grab from multiple Python threads.

    ``mode="same"`` shares one MSS object across all threads.  This is the
    thread-safety case that currently exposes DC lifetime problems on Windows.
    ``mode="separate"`` gives each thread its own MSS object.
    """
    if mode not in {"same", "separate"}:
        msg = f"Unknown threaded benchmark mode: {mode!r}"
        raise ValueError(msg)

    print(f"Threaded grab benchmark ({mode} MSS object, {thread_count} threads)")
    print(f"Iterations per thread: {iterations}")
    print(f"Start delay: {start_delay:.3f}s")
    print("=" * 50)

    errors: list[BaseException] = []
    per_thread_elapsed: list[float] = []

    def run_many(sct: mss.MSS, monitor: Monitor) -> None:
        for _ in range(warmup_iterations):
            sct.grab(monitor)
        elapsed = _run_loop(iterations, lambda: sct.grab(monitor))
        per_thread_elapsed.append(elapsed)

    def worker_with_shared_sct(sct: mss.MSS, monitor: Monitor) -> None:
        try:
            run_many(sct, monitor)
        except BaseException as exc:  # noqa: BLE001 - benchmarks need to report worker-thread failures.
            errors.append(exc)

    def worker_with_separate_sct() -> None:
        try:
            with mss.MSS() as sct:
                run_many(sct, _primary_monitor(sct))
        except BaseException as exc:  # noqa: BLE001 - benchmarks need to report worker-thread failures.
            errors.append(exc)

    start = perf_counter()
    if mode == "same":
        with mss.MSS() as sct:
            monitor = _primary_monitor(sct)
            threads = [
                threading.Thread(target=worker_with_shared_sct, args=(sct, monitor), name=f"grab-{index}")
                for index in range(thread_count)
            ]
            _start_and_join(threads, start_delay)
    else:
        threads = [
            threading.Thread(target=worker_with_separate_sct, name=f"grab-{index}") for index in range(thread_count)
        ]
        _start_and_join(threads, start_delay)

    wall_elapsed = perf_counter() - start
    total_iterations = iterations * thread_count

    if errors:
        print(f"Failed after {wall_elapsed:.3f}s with {len(errors)} worker error(s).")
        print(f"First error: {type(errors[0]).__name__}: {errors[0]}")
        raise errors[0]

    _print_result("Wall-clock average", total_iterations, wall_elapsed)
    if per_thread_elapsed:
        slowest = max(per_thread_elapsed)
        fastest = min(per_thread_elapsed)
        print(f"Per-thread elapsed: fastest={fastest:.3f}s slowest={slowest:.3f}s")


def analyze_frame_timing(warmup_iterations: int = WARMUP_ITERATIONS) -> None:
    """Analyze individual frame timing to detect VSync/DWM patterns."""
    num_samples = 200

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        width, height = monitor["width"], monitor["height"]

        print("Frame timing analysis")
        print(f"Region: {width}x{height}")
        print(f"Samples: {num_samples}")
        print("=" * 50)

        # Warmup
        for _ in range(warmup_iterations):
            sct.grab(monitor)

        # Collect individual frame times
        times: list[float] = []
        prev = perf_counter()
        for _ in range(num_samples):
            sct.grab(monitor)
            now = perf_counter()
            times.append((now - prev) * 1000)  # Convert to ms
            prev = now

        # Analyze the distribution
        times.sort()
        min_t = times[0]
        max_t = times[-1]
        avg_t = sum(times) / len(times)
        median_t = times[len(times) // 2]

        # Calculate percentiles
        p5 = times[int(len(times) * 0.05)]
        p95 = times[int(len(times) * 0.95)]

        print("\nTiming distribution:")
        print(f"  Min:    {min_t:.2f}ms")
        print(f"  5th %:  {p5:.2f}ms")
        print(f"  Median: {median_t:.2f}ms")
        print(f"  Avg:    {avg_t:.2f}ms")
        print(f"  95th %: {p95:.2f}ms")
        print(f"  Max:    {max_t:.2f}ms")

        # Check for VSync patterns
        print("\nVSync pattern analysis:")
        print("  60 Hz (16.67ms): ", end="")
        near_60hz = sum(1 for t in times if 15 < t < 18)
        print(f"{near_60hz}/{num_samples} samples ({near_60hz / num_samples * 100:.0f}%)")

        print("  30 Hz (33.33ms): ", end="")
        near_30hz = sum(1 for t in times if 31 < t < 36)
        print(f"{near_30hz}/{num_samples} samples ({near_30hz / num_samples * 100:.0f}%)")

        print("  < 10ms (fast):   ", end="")
        fast = sum(1 for t in times if t < 10)
        print(f"{fast}/{num_samples} samples ({fast / num_samples * 100:.0f}%)")

        # Histogram buckets
        print("\nHistogram (ms):")
        buckets = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 100]
        for i in range(len(buckets) - 1):
            lo, hi = buckets[i], buckets[i + 1]
            count = sum(1 for t in times if lo <= t < hi)
            bar = "#" * (count * 40 // num_samples)
            print(f"  {lo:3d}-{hi:3d}: {bar} ({count})")
        # Overflow bucket
        count = sum(1 for t in times if t >= buckets[-1])
        if count > 0:
            bar = "#" * (count * 40 // num_samples)
            print(f"  {buckets[-1]:3d}+  : {bar} ({count})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=["all", "grab", "sizes", "raw", "dc", "threads", "timing"],
        default="all",
    )
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    parser.add_argument("--warmup", type=int, default=WARMUP_ITERATIONS)
    parser.add_argument("--threads", type=int, default=THREADS)
    parser.add_argument("--mode", choices=["same", "separate"], default="same")
    parser.add_argument("--start-delay", type=float, default=0.0)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args(argv)

    if args.command in {"all", "grab"}:
        benchmark_grab(args.iterations, args.warmup)
    if args.command in {"all", "sizes"}:
        benchmark_grab_varying_sizes(args.iterations, args.warmup)
    if args.command == "raw":
        benchmark_raw_bitblt(args.iterations)
    if args.command == "dc":
        benchmark_raw_dc_allocation(iterations=args.iterations, width=args.width, height=args.height)
    if args.command == "threads":
        benchmark_threaded_grab(
            iterations=args.iterations,
            thread_count=args.threads,
            mode=args.mode,
            start_delay=args.start_delay,
            warmup_iterations=args.warmup,
        )
    if args.command == "timing":
        analyze_frame_timing(args.warmup)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
