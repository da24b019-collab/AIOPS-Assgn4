"""
metrics.py -- every Prometheus metric of the app lives in this one file.

Why a separate file?
Streamlit re-runs app.py from top to bottom on EVERY click. If we defined the
metrics inside app.py, Prometheus would complain "Duplicated timeseries".
A module that is imported is loaded only ONCE per process, so metrics defined
here are created exactly once.

Four metric types used (know the difference for the viva!):
  Counter   -> only goes UP (total images processed, total errors)
  Gauge     -> goes UP and DOWN (active requests, memory in use)
  Histogram -> counts observations into buckets (latency distribution)
  Summary   -> keeps only <name>_sum and <name>_count (cheap average)
"""

import os

import psutil
from prometheus_client import Counter, Gauge, Histogram, Info, Summary, start_http_server

METRICS_PORT = 8000  # Prometheus will scrape http://localhost:8000/metrics

# ---------------------------------------------------------------------------
# 1. COUNTERS  (name gets an automatic "_total" suffix)
# ---------------------------------------------------------------------------
# Labels: mode = single|bulk, status = success|failure
#         client_ip / session_id = custom client metadata (requirement 5)
IMAGES_PROCESSED = Counter(
    "captioner_images_processed_total",
    "Total images captioned, split by mode, outcome and client",
    ["mode", "status", "client_ip", "session_id"],
)

REQUESTS = Counter(
    "captioner_requests_total",
    "Total user requests (one upload click = one request)",
    ["mode", "client_ip", "session_id"],
)

ERRORS = Counter(
    "captioner_errors_total",
    "Total errors, split by mode and error type",
    ["mode", "error_type"],
)

UPLOAD_BYTES = Counter(
    "captioner_upload_bytes_total",
    "Total bytes uploaded by users",
    ["mode"],
)

SKIPPED_FILES = Counter(
    "captioner_zip_skipped_files_total",
    "Files inside ZIPs that were ignored (not an image, too big, over limit)",
    ["reason"],
)

# ---------------------------------------------------------------------------
# 2. GAUGES
# ---------------------------------------------------------------------------
ACTIVE_REQUESTS = Gauge(
    "captioner_active_requests",
    "Requests being processed right now",
    ["mode"],
)

PROCESS_MEMORY = Gauge(
    "captioner_process_memory_bytes",
    "Resident memory (RAM) used by this Python process, incl. the model",
)

MODEL_LOADED = Gauge(
    "captioner_model_loaded",
    "1 if the captioning model is loaded in memory, else 0",
)

LAST_BATCH_SIZE = Gauge(
    "captioner_last_bulk_batch_size",
    "Number of images in the most recent bulk upload",
)

# ---------------------------------------------------------------------------
# 3. HISTOGRAMS  (the buckets decide how precise our percentiles can be)
# ---------------------------------------------------------------------------
# CPU captioning takes ~1-10 s per image, so buckets cover 0.25 s .. 60 s.
INFERENCE_SECONDS = Histogram(
    "captioner_inference_duration_seconds",
    "Time the model needs to caption ONE image",
    ["mode"],
    buckets=(0.25, 0.5, 1, 2, 3, 5, 8, 12, 20, 30, 60),
)

BULK_BATCH_SECONDS = Histogram(
    "captioner_bulk_batch_duration_seconds",
    "Time to process a whole ZIP",
    buckets=(5, 10, 30, 60, 120, 300, 600),
)

IMAGE_SIZE_BYTES = Histogram(
    "captioner_image_size_bytes",
    "Size of each uploaded image",
    buckets=(10_000, 50_000, 100_000, 500_000, 1_000_000, 5_000_000, 10_000_000),
)

# ---------------------------------------------------------------------------
# 4. SUMMARIES  (exposes <name>_sum and <name>_count, no buckets)
# ---------------------------------------------------------------------------
# average = rate(_sum) / rate(_count)
REQUEST_SECONDS = Summary(
    "captioner_request_duration_seconds",
    "End-to-end time of a user request (UI click to result)",
    ["mode"],
)

CAPTION_LENGTH_WORDS = Summary(
    "captioner_caption_length_words",
    "Number of words in each generated caption",
)

# ---------------------------------------------------------------------------
# Static information about the app (shows up as a label-only metric = 1)
# ---------------------------------------------------------------------------
APP_INFO = Info("captioner_app", "Static information about this application")


def update_memory_gauge():
    """Read this process's RAM usage and store it in the gauge."""
    PROCESS_MEMORY.set(psutil.Process(os.getpid()).memory_info().rss)


def start_metrics_server():
    """Open the /metrics endpoint on a SEPARATE port (assignment requirement)."""
    start_http_server(METRICS_PORT)
