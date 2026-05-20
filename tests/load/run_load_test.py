"""
Автоматический нагрузочный тест с обнаружением bottleneck.
Останавливается при error rate > 5% или median latency > 20s.
Запускает Locust программно и генерирует HTML-отчёт с динамическим анализом.
"""

import subprocess
import time
import os
from datetime import datetime
from pathlib import Path


HOST = "http://localhost:8000"
MAX_USERS = 200
START_USERS = 1
RUN_TIME = 60
REPORT_DIR = Path("tests/load/reports") / datetime.now().strftime("%Y%m%d_%H%M%S")
ERROR_THRESHOLD = 5.0
LATENCY_THRESHOLD = 20000  # 20 секунд в миллисекундах


def run_locust(users: int, spawn_rate: int, run_time: int, prefix: str) -> dict:
    """Запустить Locust и вернуть результаты"""
    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--host", HOST,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", f"{run_time}s",
        "--headless",
        "--csv", prefix,
        "--html", f"{prefix}.html",
    ]
    
    print(f"\n{'='*60}")
    print(f" Running: {users} users | spawn: {spawn_rate}/s | duration: {run_time}s")
    print(f"{'='*60}")
    
    subprocess.run(cmd, check=False)
    time.sleep(2)
    
    stats_csv = f"{prefix}_stats.csv"
    if not os.path.exists(stats_csv):
        return {"users": users, "requests": 0, "fails": 0, "error_rate": 0,
                "avg_latency": 0, "median_latency": 0, "rps": 0}
    
    import csv
    with open(stats_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Type") == "Aggregated" or row.get("Name") == "Aggregated":
                total_req = int(row.get("Request Count", 0) or row.get("# requests", 0) or 0)
                total_fail = int(row.get("Failure Count", 0) or row.get("# fails", 0) or 0)
                avg_lat = float(row.get("Average Response Time", 0) or row.get("Average (ms)", 0) or 0)
                med_lat = float(row.get("Median Response Time", 0) or row.get("Median (ms)", 0) or 0)
                rps = float(row.get("Requests/s", 0) or row.get("Current RPS", 0) or 0)
                error_rate = (total_fail / total_req * 100) if total_req > 0 else 0
                
                return {
                    "users": users,
                    "requests": total_req,
                    "fails": total_fail,
                    "error_rate": round(error_rate, 2),
                    "avg_latency": round(avg_lat),
                    "median_latency": round(med_lat),
                    "rps": round(rps, 2),
                }
    
    return {"users": users, "requests": 0, "fails": 0, "error_rate": 0,
            "avg_latency": 0, "median_latency": 0, "rps": 0}


def analyze_bottleneck(results: list, bottleneck_users: int, bottleneck_result: dict) -> dict:
    """
    Анализирует результаты и определяет реальную причину bottleneck.
    Возвращает словарь с component, cause, evidence.
    """
    prev_result = None
    for i, r in enumerate(results):
        if r["users"] == bottleneck_users and i > 0:
            prev_result = results[i-1]
            break
    
    analysis = {
        "component": "Unknown",
        "cause": "Threshold reached",
        "evidence": f"Bottleneck at {bottleneck_users} users",
        "recommendations": []
    }
    
    if bottleneck_result["requests"] == 0:
        analysis["component"] = "System Unresponsive"
        analysis["cause"] = "Service stopped accepting connections"
        analysis["evidence"] = f"No requests completed at {bottleneck_users} users"
        analysis["recommendations"] = [
            "Check service logs for crashes",
            "Verify connection limits (ulimit, nginx)",
            "Review timeout configurations"
        ]
        return analysis
    
    if bottleneck_result["error_rate"] > ERROR_THRESHOLD:
        analysis["component"] = "API / LLM Timeout"
        analysis["cause"] = "Requests timing out before completion"
        analysis["evidence"] = f"Error rate {bottleneck_result['error_rate']}% > {ERROR_THRESHOLD}%"
        
        if bottleneck_result["median_latency"] > LATENCY_THRESHOLD:
            analysis["cause"] = "Queue buildup causing timeouts"
            analysis["evidence"] += f" with median latency {bottleneck_result['median_latency']}ms"
        
        analysis["recommendations"] = [
            "Increase LLM timeout (currently 30s → 120s)",
            "Add semaphore for concurrent requests",
            "Enable continuous batching in vLLM",
            "Consider horizontal scaling of vLLM"
        ]
        return analysis
    
    if bottleneck_result["median_latency"] > LATENCY_THRESHOLD:
        if prev_result and bottleneck_result["median_latency"] > prev_result["median_latency"] * 2:
            analysis["component"] = "Latency Explosion (vLLM Queue)"
            analysis["cause"] = "Non-linear queue growth - GPU saturated"
            analysis["evidence"] = f"Latency exploded from {prev_result['median_latency']}ms to {bottleneck_result['median_latency']}ms"
        else:
            analysis["component"] = "vLLM Processing Bottleneck"
            analysis["cause"] = "Sequential processing creates queue"
            analysis["evidence"] = f"Median latency {bottleneck_result['median_latency']}ms exceeds {LATENCY_THRESHOLD}ms threshold"
        
        analysis["recommendations"] = [
            f"Increase --max-num-seqs in vLLM (current 4 → 16)",
            "Enable --enable-prefix-caching",
            "Reduce --max-tokens (current 2500 → 1000)",
            "Add second vLLM instance behind load balancer"
        ]
        return analysis
    
    if prev_result and bottleneck_result["rps"] < prev_result["rps"] * 0.5:
        analysis["component"] = "Throughput Collapse"
        analysis["cause"] = "System reached saturation point"
        analysis["evidence"] = f"RPS dropped from {prev_result['rps']} to {bottleneck_result['rps']}"
        analysis["recommendations"] = [
            "Monitor GPU utilization",
            "Check database connection pool (current pool_size=5)",
            "Review API worker count"
        ]
        return analysis
    
    return analysis


def generate_report(results: list, bottleneck_users: int, report_dir: Path):
    """Генерировать HTML-отчёт с графиками и динамическим анализом"""
    
    labels = [r["users"] for r in results]
    error_data = [r["error_rate"] for r in results]
    latency_data = [r["median_latency"] for r in results]
    rps_data = [r["rps"] for r in results]
    
    bottleneck_result = None
    for r in results:
        if r["users"] == bottleneck_users:
            bottleneck_result = r
            break
    if not bottleneck_result and results:
        bottleneck_result = results[-1]
    
    analysis = analyze_bottleneck(results, bottleneck_users, bottleneck_result)
    
    recs_html = "\n".join([f"<li>{rec}</li>" for rec in analysis["recommendations"]])
    if not recs_html:
        recs_html = "<li>Run additional profiling to identify exact bottleneck</li>"
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Load Test Bottleneck Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:Segoe UI,Arial,sans-serif; background:#0d1117; color:#c9d1d9; padding:30px; }}
h1 {{ color:#58a6ff; font-size:26px; margin-bottom:5px; }}
.subtitle {{ color:#8b949e; font-size:13px; margin-bottom:25px; }}
.bottleneck {{ background:#da3633; color:white; padding:18px 22px; border-radius:10px; margin:18px 0; font-size:16px; border-left:5px solid #ff7b72; }}
.bottleneck strong {{ font-size:20px; }}
h2 {{ color:#58a6ff; margin:25px 0 12px; font-size:18px; }}
h3 {{ color:#c9d1d9; margin:15px 0 8px; font-size:16px; }}
table {{ width:100%; border-collapse:collapse; margin:12px 0; background:#161b22; border-radius:8px; overflow:hidden; }}
th {{ background:#21262d; color:#58a6ff; padding:10px 14px; text-align:left; }}
td {{ padding:9px 14px; border-bottom:1px solid #21262d; }}
tr:hover {{ background:#1c2128; }}
.green {{ color:#3fb950; font-weight:bold; }}
.yellow {{ color:#d2991d; font-weight:bold; }}
.red {{ color:#f85149; font-weight:bold; }}
.chart-box {{ background:#161b22; border-radius:8px; padding:18px; margin:12px 0; }}
.metrics {{ display:flex; gap:12px; flex-wrap:wrap; margin:18px 0; }}
.metric {{ background:#161b22; border-radius:8px; padding:16px 20px; text-align:center; min-width:130px; flex:1; }}
.metric .val {{ font-size:28px; font-weight:bold; color:#58a6ff; }}
.metric .val.danger {{ color:#f85149; }}
.metric .lbl {{ font-size:11px; color:#8b949e; margin-top:4px; text-transform:uppercase; }}
.recs {{ background:#161b22; border-radius:8px; padding:18px 25px; margin:12px 0; }}
.recs li {{ margin:7px 0; }}
.evidence {{ background:#21262d; border-radius:8px; padding:12px 20px; margin:10px 0; font-family:monospace; font-size:13px; }}
.footer {{ margin-top:35px; padding-top:12px; border-top:1px solid #21262d; color:#484f58; font-size:11px; }}
a {{ color:#58a6ff; }}
</style>
</head>
<body>

<h1>Load Test Report</h1>
<p class="subtitle">Target: {HOST} | Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

<div class="bottleneck">
Bottleneck at <strong>{bottleneck_users} users</strong><br>
<span style="opacity:0.85">Stop condition: error rate > {ERROR_THRESHOLD}% OR median latency > {LATENCY_THRESHOLD/1000:.0f}s</span>
</div>

<div class="metrics">
{generate_metric_cards(results, bottleneck_users)}
</div>

<h2>Performance Charts</h2>
<div class="chart-box"><h3>Error Rate (%)</h3><canvas id="errorChart"></canvas></div>
<div class="chart-box"><h3>Median Latency (ms)</h3><canvas id="latencyChart"></canvas></div>
<div class="chart-box"><h3>Requests Per Second</h3><canvas id="rpsChart"></canvas></div>

<h2>Results Table</h2>
<table>
<thead>
<th>Level</th><th>Users</th><th>Requests</th><th>Failures</th><th>Error Rate</th><th>Avg Latency</th><th>Median Latency</th><th>RPS</th><th>Status</th>
</thead>
<tbody>
{generate_table_rows(results)}
</tbody>
</table>

<h2>Bottleneck Analysis</h2>
<div class="recs">
<h3>Component: {analysis['component']}</h3>
<p><strong>Cause:</strong> {analysis['cause']}</p>
<div class="evidence"><strong>Evidence:</strong> {analysis['evidence']}</div>
</div>

<h2>Recommendations</h2>
<div class="recs">
<ol>
{recs_html}
</ol>
</div>

<h2>Per-Level Reports</h2>
<ul>
{generate_report_links(results, report_dir)}
</ul>

<div class="footer">Generated by run_load_test.py | {datetime.now().isoformat()}</div>

<script>
{generate_charts_js(labels, error_data, latency_data, rps_data)}
</script>
</body>
</html>"""
    
    report_path = report_dir / "bottleneck_report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"\nReport saved: {report_path}")
    return report_path


def generate_metric_cards(results, bottleneck):
    """Метрики bottleneck"""
    for r in results:
        if r["users"] == bottleneck:
            return f"""
<div class="metric"><div class="val danger">{r['users']}</div><div class="lbl">Users</div></div>
<div class="metric"><div class="val danger">{r['error_rate']}%</div><div class="lbl">Error Rate</div></div>
<div class="metric"><div class="val danger">{r['median_latency']} ms</div><div class="lbl">Median Latency</div></div>
<div class="metric"><div class="val">{r['rps']}</div><div class="lbl">RPS</div></div>"""
    return ""


def generate_table_rows(results):
    rows = ""
    for i, r in enumerate(results, 1):
        if r["requests"] == 0:
            status = '<span class="red">No response</span>'
        elif r["error_rate"] == 0:
            status = '<span class="green">Stable</span>'
        elif r["error_rate"] <= 5:
            status = '<span class="yellow">Warning</span>'
        else:
            status = '<span class="red">Critical</span>'
        rows += f"<tr><td>{i}</td><td>{r['users']}</td><td>{r['requests']}</td><td>{r['fails']}</td><td>{r['error_rate']}%</td><td>{r['avg_latency']}</td><td>{r['median_latency']}</td><td>{r['rps']}</td><td>{status}</td></tr>\n"
    return rows


def generate_report_links(results, report_dir):
    links = ""
    for i, r in enumerate(results, 1):
        links += f"<li><a href='level_{i}_users_{r['users']}.html'>Level {i}: {r['users']} users</a></li>\n"
    return links


def generate_charts_js(labels, error_data, latency_data, rps_data):
    return f"""
new Chart(document.getElementById('errorChart'), {{
    type: 'bar',
    data: {{
        labels: {labels},
        datasets: [{{
            label: 'Error Rate (%)',
            data: {error_data},
            backgroundColor: ctx => ctx.raw > 5 ? '#f85149' : ctx.raw > 0 ? '#d2991d' : '#3fb950',
            borderRadius: 5
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
        scales: {{
            y: {{ beginAtZero: true, max: 100, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
            x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ display: false }} }}
        }}
    }}
}});

new Chart(document.getElementById('latencyChart'), {{
    type: 'line',
    data: {{
        labels: {labels},
        datasets: [{{
            label: 'Median Latency (ms)',
            data: {latency_data},
            borderColor: '#58a6ff',
            backgroundColor: 'rgba(88,166,255,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 6
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
        scales: {{
            y: {{ beginAtZero: true, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
            x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ display: false }} }}
        }}
    }}
}});

new Chart(document.getElementById('rpsChart'), {{
    type: 'bar',
    data: {{
        labels: {labels},
        datasets: [{{
            label: 'RPS',
            data: {rps_data},
            backgroundColor: '#3fb950',
            borderRadius: 5
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#c9d1d9' }} }} }},
        scales: {{
            y: {{ beginAtZero: true, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
            x: {{ ticks: {{ color: '#8b949e' }}, grid: {{ display: false }} }}
        }}
    }}
}});
"""


def main():
    print("=" * 60)
    print(" AUTOMATED LOAD TEST WITH BOTTLENECK DETECTION")
    print("=" * 60)
    print(f"Host: {HOST}")
    print(f"Stop: error > {ERROR_THRESHOLD}% OR latency > {LATENCY_THRESHOLD}ms")
    print("=" * 60)
    
    os.makedirs(REPORT_DIR, exist_ok=True)
    
    results = []
    users = START_USERS
    level = 0
    bottleneck_users = users
    
    while users <= MAX_USERS:
        level += 1
        spawn_rate = max(1, users // 2)
        prefix = str(REPORT_DIR / f"level_{level}_users_{users}")
        
        result = run_locust(users, spawn_rate, RUN_TIME, prefix)
        result["level"] = level
        results.append(result)
        
        print(f"\n>> Level {level}: {users}u | reqs={result['requests']} | errors={result['error_rate']}% | median={result['median_latency']}ms | rps={result['rps']}")
        
        if result["requests"] == 0:
            print(f">> BOTTLENECK: No requests completed at {users} users!")
            bottleneck_users = users
            break
        elif result["error_rate"] > ERROR_THRESHOLD:
            print(f">> BOTTLENECK: Error rate {result['error_rate']}% > {ERROR_THRESHOLD}% at {users} users!")
            bottleneck_users = users
            break
        elif result["median_latency"] > LATENCY_THRESHOLD:
            print(f">> BOTTLENECK: Median latency {result['median_latency']}ms > {LATENCY_THRESHOLD}ms at {users} users!")
            bottleneck_users = users
            break
        else:
            print(f">> STABLE at {users} users")
        
        users *= 2
        time.sleep(5)
    
    print("\n" + "=" * 60)
    print(" GENERATING REPORT")
    print("=" * 60)
    
    report_path = generate_report(results, bottleneck_users, REPORT_DIR)
    
    print(f"\nBottleneck: {bottleneck_users} users")
    print(f"Report: {report_path}")
    
    import webbrowser
    webbrowser.open(str(report_path))


if __name__ == "__main__":
    main()