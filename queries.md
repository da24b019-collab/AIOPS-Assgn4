# PromQL queries used in the Grafana dashboard

All queries below were written with the help of an AI assistant (Claude).
Each row lists the prompt used and the query. Explanations are underneath.

| # | Panel | Prompt given to the AI | Query |
|---|---|---|---|
| 1 | Application Health | "PromQL to show whether the captioning app is up" | `up{job="captioner_app"}` |
| 2 | System Exporter Health | "PromQL to show whether node_exporter is up" | `up{job="node"}` |
| 3 | Model Loaded | "Show whether the model gauge is loaded" | `captioner_model_loaded` |
| 4 | Images Captioned (15 min) | "PromQL for total successful images in the last 15 minutes" | `sum(increase(captioner_images_processed_total{status="success"}[15m]))` |
| 5 | Failure Rate | "PromQL for the share of images that failed in the last 5 minutes" | `sum(rate(captioner_images_processed_total{status="failure"}[5m])) / sum(rate(captioner_images_processed_total[5m]))` |
| 6 | Active Requests (tile) | "PromQL for current number of active requests" | `sum(captioner_active_requests)` |
| 7 | Throughput | "PromQL for images captioned per minute, split by mode" | `sum by (mode) (rate(captioner_images_processed_total{status="success"}[1m])) * 60` |
| 8 | Latency (average) | "PromQL for average inference latency from a histogram" | `sum(rate(captioner_inference_duration_seconds_sum[1m])) / sum(rate(captioner_inference_duration_seconds_count[1m]))` |
| 9 | Latency (95th percentile) | "PromQL for 95th percentile inference latency from a histogram" | `histogram_quantile(0.95, sum by (le) (rate(captioner_inference_duration_seconds_bucket[1m])))` |
| 10 | Latency heatmap | "PromQL to draw a heatmap of a histogram's buckets per minute" | `sum by (le) (increase(captioner_inference_duration_seconds_bucket[1m]))` |
| 11 | End-to-end request time | "PromQL for average request time from a Summary, split by mode" | `sum by (mode) (rate(captioner_request_duration_seconds_sum[5m])) / sum by (mode) (rate(captioner_request_duration_seconds_count[5m]))` |
| 12 | Requests by client | "PromQL table of requests per client IP and session, last 15 minutes" | `sum by (client_ip, session_id, mode) (increase(captioner_requests_total[15m]))` |
| 13 | Active Requests (chart) | "PromQL for active requests split by mode" | `sum by (mode) (captioner_active_requests)` |
| 14 | Skipped ZIP files | "PromQL for skipped ZIP files per reason in the last 5 minutes" | `sum by (reason) (increase(captioner_zip_skipped_files_total[5m]))` |
| 15 | Errors | "PromQL for total errors in the last 5 minutes" | `sum(increase(captioner_errors_total[5m]))` |
| 16 | Average image size | "PromQL for average uploaded image size from a histogram" | `sum(rate(captioner_image_size_bytes_sum[5m])) / sum(rate(captioner_image_size_bytes_count[5m]))` |
| 17 | Average caption length | "PromQL for average caption length from a Summary" | `sum(rate(captioner_caption_length_words_sum[5m])) / sum(rate(captioner_caption_length_words_count[5m]))` |
| 18 | Correlation (bulk throughput) | "PromQL for bulk-only throughput per minute" | `sum(rate(captioner_images_processed_total{mode="bulk",status="success"}[1m])) * 60` |
| 19 | CPU usage | "PromQL for overall CPU usage percent from node_exporter" | `100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)` |
| 20 | System RAM | "PromQL for used system memory from node_exporter" | `node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes` |
| 21 | App RAM | Written by hand from the gauge defined in `metrics.py` | `captioner_process_memory_bytes` |
| 22 | Disk usage | "PromQL for disk usage percent of root filesystem from node_exporter" | `100 - (node_filesystem_avail_bytes{mountpoint="/", fstype!~"tmpfs\|overlay"} / node_filesystem_size_bytes{mountpoint="/", fstype!~"tmpfs\|overlay"} * 100)` |
| 23 | Bulk upload annotation | "Annotation marking each bulk upload on the charts" | `sum(increase(captioner_requests_total{mode="bulk"}[15s])) > 0` |

## How each query works

- `rate(counter[1m])`: how fast a counter grew per second, averaged over the last minute. `* 60` gives per minute.
- `increase(counter[5m])`: how much a counter grew over the last 5 minutes.
- `sum by (label)`: adds up all series and keeps one line per label value, hiding other labels such as `session_id`.
- Average from a histogram or Summary: `_sum` is the total (seconds, bytes or words), `_count` is the number of observations. `rate(_sum) / rate(_count)` is the average per observation.
- `histogram_quantile(0.95, ...)`: uses the cumulative bucket counts (`le` = "less than or equal") to estimate the value that 95% of observations were below. Precision depends on the bucket boundaries chosen in `metrics.py`.
- CPU: node_exporter counts the seconds each core spent idle. `rate` of idle seconds is the idle fraction, `avg` merges the cores, and `100 - idle%` gives busy %.
- Memory: total memory minus available memory is the memory in use.
- Disk: available bytes divided by total bytes is the free fraction. `100 - free%` is the used %.
- Failure rate: failed images per second divided by all images per second.
- Regex `fstype!~"tmpfs|overlay"` (query 22): "filesystem type does not match tmpfs or overlay", which leaves only the real disk.
