# Image Captioning App with Prometheus + Grafana Monitoring

A Streamlit app that captions images on the CPU (BLIP model) in single and bulk (ZIP) mode.
It exposes Prometheus metrics on port 8000, and a Grafana dashboard shows app health,
throughput, latency, reliability and system resources (CPU, RAM, disk).

## Files
| File | Purpose |
|---|---|
| `app.py` | Streamlit UI (single + bulk mode) |
| `captioner.py` | Model loading, captioning, ZIP reading |
| `metrics.py` | All Prometheus metrics (Counter, Gauge, Histogram, Summary) |
| `prometheus.yml` | Prometheus scrape config (app :8000, node_exporter :9100) |
| `dashboard.json` | Exported Grafana dashboard (19 panels) |
| `queries.md` | Every PromQL query with the AI prompt used and an explanation |
| `AI_DISCLOSURE.md` | What the AI assistant helped with |
| `requirements.txt` | Python dependencies |

## Run
1. `python3 -m venv venv && source venv/bin/activate`
2. `pip install torch --index-url https://download.pytorch.org/whl/cpu`
3. `pip install -r requirements.txt`
4. `streamlit run app.py` (UI on :8501, metrics on :8000/metrics)
5. Start `node_exporter` (:9100), then `./prometheus --config.file=prometheus.yml` (:9090)
6. Start Grafana (:3000) and add a Prometheus data source (the URL of your Prometheus).
7. Import the dashboard: Dashboards > New > Import > upload `dashboard.json` > pick your Prometheus data source.

## Metrics
- Counters: images processed, requests, errors, upload bytes, skipped ZIP files
- Gauges: active requests, process memory, model loaded, last bulk batch size
- Histograms: inference time, bulk batch time, image size
- Summaries: request duration, caption length
- Custom labels: mode, status, client_ip, session_id, error_type, reason

## Dashboard layout
1. Health overview: app status, exporter status, model loaded, images captioned, failure rate, active requests
2. Throughput and latency: throughput, latency (average and p95), latency heatmap, end-to-end request time
3. Workload, clients and reliability: requests by client, active requests, errors and skipped files, image size, caption length
4. System resources: bulk throughput vs CPU (correlation), CPU, memory, disk

The dashboard follows the 7 commandments of plotting: colour-blind-safe palette, line styles that differ in print,
named axes, explicit units and linear scale, legends, short titles and a description on every panel.
