"""
app.py -- Streamlit user interface for the image captioning app.

Run with:   streamlit run app.py
Metrics at: http://localhost:8000/metrics   (separate port from the UI on 8501)
"""

import time
import uuid

import streamlit as st
from PIL import Image

import captioner
import metrics

st.set_page_config(page_title="Image Captioner", page_icon="🖼️")


# ---------------------------------------------------------------------------
# One-time setup. st.cache_resource runs the function ONCE and remembers the
# result, even though Streamlit re-runs this whole script on every click.
# ---------------------------------------------------------------------------
@st.cache_resource
def start_metrics_once():
    metrics.start_metrics_server()
    metrics.APP_INFO.info({"model": captioner.MODEL_NAME, "device": "cpu", "version": "1.0"})
    return True


@st.cache_resource(show_spinner="Loading model (first run downloads ~1 GB)...")
def get_model():
    return captioner.load_model()


start_metrics_once()
processor, model = get_model()


# ---------------------------------------------------------------------------
# Client metadata used as Prometheus labels
# ---------------------------------------------------------------------------
def get_client_labels():
    """Return (client_ip, session_id) for the current browser tab."""
    # session_state survives reruns, so one browser tab keeps one session id
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = uuid.uuid4().hex[:8]  # short id keeps labels small

    # Behind a proxy the real IP is in X-Forwarded-For; locally it is missing.
    headers = st.context.headers
    forwarded = headers.get("X-Forwarded-For", "")
    client_ip = forwarded.split(",")[0].strip() if forwarded else "localhost"
    return client_ip, st.session_state["session_id"]


# ---------------------------------------------------------------------------
# Captioning ONE image with all per-image metrics recorded
# ---------------------------------------------------------------------------
def caption_with_metrics(image, mode, client_ip, session_id):
    """Caption an image; record latency, caption length and success/failure."""
    start = time.perf_counter()
    try:
        caption = captioner.generate_caption(processor, model, image)
    except Exception as error:
        metrics.ERRORS.labels(mode=mode, error_type=type(error).__name__).inc()
        metrics.IMAGES_PROCESSED.labels(mode, "failure", client_ip, session_id).inc()
        return None

    # Histogram: put this latency into the right bucket
    metrics.INFERENCE_SECONDS.labels(mode=mode).observe(time.perf_counter() - start)
    # Summary: records caption length (_sum and _count)
    metrics.CAPTION_LENGTH_WORDS.observe(len(caption.split()))
    # Counter: one more successful image
    metrics.IMAGES_PROCESSED.labels(mode, "success", client_ip, session_id).inc()
    metrics.update_memory_gauge()  # Gauge: refresh RAM reading
    return caption


# ---------------------------------------------------------------------------
# User interface
# ---------------------------------------------------------------------------
st.title("🖼️ CPU Image Captioner")
st.caption(f"Model: {captioner.MODEL_NAME} · running on CPU")

client_ip, session_id = get_client_labels()
single_tab, bulk_tab = st.tabs(["Single image", "Bulk (ZIP)"])

# ----- SINGLE MODE ---------------------------------------------------------
with single_tab:
    uploaded = st.file_uploader("Upload one image", type=["jpg", "jpeg", "png", "webp"])
    if uploaded and st.button("Generate caption", key="single_btn"):
        mode = "single"
        metrics.REQUESTS.labels(mode, client_ip, session_id).inc()
        metrics.UPLOAD_BYTES.labels(mode).inc(uploaded.size)
        metrics.IMAGE_SIZE_BYTES.observe(uploaded.size)

        # track_inprogress() -> gauge +1 on entry, -1 on exit (even on error)
        # .time()            -> summary records how long the block took
        with metrics.ACTIVE_REQUESTS.labels(mode).track_inprogress(), \
                metrics.REQUEST_SECONDS.labels(mode).time():
            caption = None
            try:
                image = Image.open(uploaded)
                image.load()  # forces a full decode, so a broken file fails here
            except Exception as error:  # the file is not a valid image
                metrics.ERRORS.labels(mode=mode, error_type=type(error).__name__).inc()
                metrics.IMAGES_PROCESSED.labels(mode, "failure", client_ip, session_id).inc()
                image = None

            if image is not None:
                with st.spinner("Thinking..."):
                    caption = caption_with_metrics(image, mode, client_ip, session_id)

        if image is None:
            st.error("This file is not a valid image.")
        else:
            st.image(image, use_container_width=True)
            if caption:
                st.success(caption)
            else:
                st.error("Could not caption this image.")

# ----- BULK MODE -----------------------------------------------------------
with bulk_tab:
    zip_file = st.file_uploader("Upload a ZIP of images", type=["zip"])
    st.caption(f"Max {captioner.MAX_IMAGES_PER_ZIP} images, {captioner.MAX_FILE_BYTES // 1024 // 1024} MB each.")

    if zip_file and st.button("Caption all images", key="bulk_btn"):
        mode = "bulk"
        metrics.REQUESTS.labels(mode, client_ip, session_id).inc()
        metrics.UPLOAD_BYTES.labels(mode).inc(zip_file.size)
        batch_start = time.perf_counter()

        with metrics.ACTIVE_REQUESTS.labels(mode).track_inprogress(), \
                metrics.REQUEST_SECONDS.labels(mode).time():
            try:
                images = captioner.read_images_from_zip(zip_file.getvalue())
            except Exception as error:  # e.g. not a valid ZIP
                metrics.ERRORS.labels(mode=mode, error_type=type(error).__name__).inc()
                st.error("This is not a valid ZIP file.")
                images = []

            metrics.LAST_BATCH_SIZE.set(len(images))
            if not images and zip_file:
                st.warning("No usable images found in the ZIP.")

            progress = st.progress(0.0)
            results = []
            for i, (name, image) in enumerate(images, start=1):
                caption = caption_with_metrics(image, mode, client_ip, session_id)
                results.append((name, image, caption))
                progress.progress(i / len(images))  # live progress bar

        if images:
            metrics.BULK_BATCH_SECONDS.observe(time.perf_counter() - batch_start)

        for name, image, caption in results:
            col_img, col_text = st.columns([1, 2])
            col_img.image(image, use_container_width=True)
            col_text.markdown(f"**{name}**")
            col_text.write(caption if caption else "⚠️ failed")
