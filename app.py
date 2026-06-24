# app.py
from flask import Flask, request, jsonify
from datetime import datetime, timezone, timedelta
from orbit_model import predict_passes

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Satellite Pass Predictor</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #eef2f5;
            background-image: radial-gradient(circle at 20% 50%, rgba(30,144,255,0.03) 0%, transparent 50%),
                              radial-gradient(circle at 80% 20%, rgba(100,149,237,0.02) 0%, transparent 50%);
            color: #2c3e50;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 1.5em;
        }
        .container {
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
            padding: 2.2em 2.5em;
            max-width: 780px;
            width: 100%;
        }
        h1 {
            font-weight: 600;
            font-size: 2em;
            margin-bottom: 0.25em;
            color: #1a3a5c;
            letter-spacing: -0.5px;
        }
        .subtitle {
            font-size: 0.95em;
            color: #5a6c7d;
            margin-bottom: 2em;
            border-left: 3px solid #1e90ff;
            padding-left: 12px;
        }
        form {
            background: #f8fafc;
            padding: 1.5em;
            border-radius: 12px;
            margin-bottom: 2.2em;
            border: 1px solid #e9eef3;
        }
        .form-row {
            display: flex;
            gap: 1.2em;
            margin-bottom: 1.2em;
            flex-wrap: wrap;
        }
        .form-group {
            flex: 1 1 45%;
            min-width: 220px;
        }
        label {
            display: block;
            font-size: 0.85em;
            font-weight: 500;
            color: #2c3e50;
            margin-bottom: 0.3em;
        }
        input {
            width: 100%;
            padding: 0.7em 0.9em;
            border: 1px solid #d0dae4;
            border-radius: 7px;
            font-size: 0.95em;
            transition: all 0.2s ease;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }
        input:focus {
            outline: none;
            border-color: #1e90ff;
            box-shadow: 0 0 0 3px rgba(30,144,255,0.12);
        }
        button {
            background: linear-gradient(135deg, #1e90ff 0%, #1873cc 100%);
            color: white;
            border: none;
            padding: 0.8em 2.2em;
            font-size: 1em;
            border-radius: 7px;
            cursor: pointer;
            font-weight: 600;
            letter-spacing: 0.3px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 10px rgba(30,144,255,0.3);
            margin-top: 0.3em;
            position: relative;
        }
        button:hover {
            background: linear-gradient(135deg, #1a7de0 0%, #1565b8 100%);
            box-shadow: 0 6px 14px rgba(30,144,255,0.4);
            transform: translateY(-1px);
        }
        button:active {
            transform: translateY(0);
            box-shadow: 0 3px 8px rgba(30,144,255,0.3);
        }
        button:disabled {
            opacity: 0.7;
            cursor: not-allowed;
            transform: none;
        }
        .spinner {
            display: inline-block;
            width: 1em;
            height: 1em;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
            margin-right: 0.4em;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .error-msg {
            background: #fff0f0;
            border: 1px solid #ffc0c0;
            color: #c03030;
            padding: 0.8em 1em;
            border-radius: 6px;
            margin-bottom: 1.5em;
            font-size: 0.9em;
        }

        #result-section {
            animation: fadeSlideIn 0.4s ease;
        }
        @keyframes fadeSlideIn {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            margin-bottom: 2em;
            border: 1px solid #edf1f6;
        }
        th {
            background: #1a3a5c;
            color: #ffffff;
            font-weight: 500;
            font-size: 0.9em;
            padding: 0.8em;
            text-align: center;
        }
        td {
            padding: 0.75em 0.5em;
            text-align: center;
            border-bottom: 1px solid #eef2f6;
            font-size: 0.95em;
        }
        tr.pass-row {
            cursor: pointer;
            background: #ffffff;
            transition: background 0.15s;
        }
        tr.pass-row:nth-child(even) { background: #fafcfd; }
        tr.pass-row:hover { background: #e8f1fe; }
        tr.selected { background: #d4e6fa !important; font-weight: 500; }
        .no-data { color: #888; font-style: italic; padding: 1.5em; }

        #chart-container {
            text-align: center;
            background: #0b1622;
            border-radius: 14px;
            padding: 1.8em 1em;
            box-shadow: inset 0 0 40px rgba(0,0,0,0.4);
        }
        #chart-title {
            color: #cddbe9;
            margin-bottom: 0.8em;
            font-weight: 500;
        }
        canvas {
            display: block;
            margin: 0 auto;
            background: #0f1a2b;
            border-radius: 50%;
            box-shadow: 0 0 30px rgba(0, 160, 255, 0.2);
        }
        .footer-note {
            font-size: 0.8em;
            color: #7a8a99;
            text-align: center;
            margin-top: 1.8em;
            letter-spacing: 0.3px;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🛰️ Ground Station Pass Predictor</h1>
    <p class="subtitle">See when a satellite will cross your sky — simplified circular orbit model</p>

    <div id="error-box" class="error-msg" style="display:none;"></div>

    <form id="pass-form">
        <div class="form-row">
            <div class="form-group">
                <label>📍 Station Latitude (°N)</label>
                <input name="lat" type="number" step="any" required value="51.5" min="-90" max="90">
            </div>
            <div class="form-group">
                <label>📍 Station Longitude (°E)</label>
                <input name="lon" type="number" step="any" required value="-0.1" min="-180" max="180">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>🛸 Satellite Altitude (km)</label>
                <input name="alt" type="number" step="any" required value="400" min="160" max="2000000">
            </div>
            <div class="form-group">
                <label>📐 Inclination (°)</label>
                <input name="inc" type="number" step="any" required value="51.6" min="0" max="180">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>⏱️ Start Time (UTC)</label>
                <input name="start_time" type="datetime-local" required value="2026-06-24T12:00">
            </div>
            <div class="form-group">
                <label>⏱️ End Time (UTC)</label>
                <input name="end_time" type="datetime-local" required value="2026-06-24T14:00">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>🔄 Initial Mean Anomaly (°)</label>
                <input name="M0" type="number" step="any" value="45" min="0" max="360">
            </div>
            <div class="form-group" style="display: flex; align-items: flex-end;">
                <button type="submit" id="submit-btn">🔍 Predict Passes</button>
            </div>
        </div>
    </form>

    <div id="result-section" style="display:none;">
        <h2 style="margin-bottom:0.5em; font-weight: 500;">📋 Predicted Passes</h2>
        <table id="pass-table">
            <thead>
                <tr>
                    <th>Rise (UTC)</th>
                    <th>Set (UTC)</th>
                    <th>Max Elevation (°)</th>
                    <th>Duration (s)</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
        <div id="chart-container">
            <h3 id="chart-title">Click a pass to view its sky chart</h3>
            <canvas id="sky-chart" width="400" height="400" style="display:none;"></canvas>
        </div>
    </div>
    <div class="footer-note">Simplified circular orbit · v1.0 · Built for learning</div>
</div>

<script>
    const form = document.getElementById('pass-form');
    const errorBox = document.getElementById('error-box');
    const resultSection = document.getElementById('result-section');
    const tableBody = document.querySelector('#pass-table tbody');
    const chartTitle = document.getElementById('chart-title');
    const canvas = document.getElementById('sky-chart');
    const ctx = canvas.getContext('2d');
    const submitBtn = document.getElementById('submit-btn');

    let currentPasses = [];
    let currentChartTrack = [];

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Basic client-side check (duplicates server validation for faster feedback)
        const lat = parseFloat(form.lat.value);
        const lon = parseFloat(form.lon.value);
        const alt = parseFloat(form.alt.value);
        const inc = parseFloat(form.inc.value);
        const M0 = parseFloat(form.M0.value || 0);
        if (isNaN(lat) || lat < -90 || lat > 90) { showError('Latitude must be between -90 and 90.'); return; }
        if (isNaN(lon) || lon < -180 || lon > 180) { showError('Longitude must be between -180 and 180.'); return; }
        if (isNaN(alt) || alt < 160) { showError('Altitude must be at least 160 km.'); return; }
        if (isNaN(inc) || inc < 0 || inc > 180) { showError('Inclination must be between 0 and 180.'); return; }
        if (isNaN(M0) || M0 < 0 || M0 > 360) { showError('Mean anomaly must be between 0 and 360.'); return; }
        if (!form.start_time.value || !form.end_time.value) {
            showError('Please select both start and end times.'); return;
        }
        const start = new Date(form.start_time.value);
        const end = new Date(form.end_time.value);
        if (end <= start) {
            showError('End time must be after start time.'); return;
        }
        const diffDays = (end - start) / (1000 * 60 * 60 * 24);
        if (diffDays > 7) {
            showError('Time range cannot exceed 7 days.'); return;
        }

        // Hide previous error, show loading state
        errorBox.style.display = 'none';
        resultSection.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span> Predicting...';

        const data = new FormData(form);
        try {
            const response = await fetch('/predict', { method: 'POST', body: data });
            const json = await response.json();
            if (json.error) {
                showError('Server error: ' + json.error);
                return;
            }
            currentPasses = json.passes;
            currentChartTrack = json.chart_track;

            tableBody.innerHTML = '';
            if (currentPasses.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" class="no-data">No passes found in this time window.</td></tr>';
                chartTitle.textContent = 'No passes to display';
                canvas.style.display = 'none';
            } else {
                currentPasses.forEach((pass, index) => {
                    const row = document.createElement('tr');
                    row.className = 'pass-row';
                    row.innerHTML = `
                        <td>${formatTime(pass.rise_utc)}</td>
                        <td>${formatTime(pass.set_utc)}</td>
                        <td>${pass.max_el.toFixed(1)}</td>
                        <td>${Math.round(pass.duration_sec)}</td>
                    `;
                    row.addEventListener('click', () => selectPass(index));
                    tableBody.appendChild(row);
                });
                selectPass(0);
            }
            resultSection.style.display = 'block';
        } catch (err) {
            showError('Network or server error. Please try again.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '🔍 Predict Passes';
        }
    });

    function showError(msg) {
        errorBox.textContent = '⚠️ ' + msg;
        errorBox.style.display = 'block';
        resultSection.style.display = 'none';
    }

    function selectPass(index) {
        document.querySelectorAll('.pass-row').forEach((row, i) => {
            row.classList.toggle('selected', i === index);
        });
        if (currentPasses.length > 0 && index < currentPasses.length) {
            const pass = currentPasses[index];
            chartTitle.textContent = `Sky chart for pass rising at ${formatTime(pass.rise_utc)}`;
            drawChart(currentChartTrack, pass.rise_utc, pass.set_utc);
        }
    }

    function formatTime(isoStr) {
        const date = new Date(isoStr);
        return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' });
    }

    function drawChart(track, riseIso, setIso) {
        if (!track || track.length === 0) {
            canvas.style.display = 'none';
            return;
        }
        canvas.style.display = 'block';
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const w = canvas.width, h = canvas.height;
        const cx = w/2, cy = h/2;
        const maxR = 180;

        ctx.strokeStyle = '#2d4b6e';
        ctx.lineWidth = 1;
        [0, 30, 60].forEach(el => {
            const r = maxR * (1 - el/90);
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, 2 * Math.PI);
            ctx.stroke();
            if (el > 0) {
                ctx.fillStyle = '#a0c0e0';
                ctx.font = '10px sans-serif';
                ctx.fillText(el + '°', cx + 3, cy - r - 3);
            }
        });

        const dirs = [
            { label: 'N', az: 0 },
            { label: 'E', az: 90 },
            { label: 'S', az: 180 },
            { label: 'W', az: 270 }
        ];
        ctx.strokeStyle = '#2d4b6e';
        ctx.fillStyle = '#c0d4ec';
        ctx.font = 'bold 13px sans-serif';
        dirs.forEach(d => {
            const angRad = (d.az - 90) * Math.PI / 180;
            const x = cx + maxR * Math.cos(angRad);
            const y = cy + maxR * Math.sin(angRad);
            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.fillText(d.label, x + 5 * Math.cos(angRad), y + 5 * Math.sin(angRad));
        });

        ctx.strokeStyle = '#5a7da8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, maxR, 0, 2 * Math.PI);
        ctx.stroke();

        if (track.length > 1) {
            ctx.beginPath();
            ctx.strokeStyle = '#ffcc00';
            ctx.lineWidth = 2.5;
            ctx.shadowColor = 'rgba(255,204,0,0.6)';
            ctx.shadowBlur = 6;
            let first = true;
            track.forEach(pt => {
                const { x, y } = azElToCanvas(pt.az, pt.el, cx, cy, maxR);
                if (first) { ctx.moveTo(x, y); first = false; }
                else { ctx.lineTo(x, y); }
            });
            ctx.stroke();
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;

            ctx.fillStyle = '#ffcc00';
            track.forEach(pt => {
                const { x, y } = azElToCanvas(pt.az, pt.el, cx, cy, maxR);
                ctx.beginPath();
                ctx.arc(x, y, 3.5, 0, 2 * Math.PI);
                ctx.fill();
            });

            ctx.fillStyle = '#ffffff';
            ctx.font = '9px monospace';
            ctx.shadowColor = 'rgba(0,0,0,0.7)';
            ctx.shadowBlur = 3;
            track.forEach((pt, i) => {
                if (i % 4 === 0) {
                    const { x, y } = azElToCanvas(pt.az, pt.el, cx, cy, maxR);
                    const t = new Date(pt.time).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC' });
                    ctx.fillText(t, x + 7, y - 5);
                }
            });
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
        }
    }

    function azElToCanvas(azDeg, elDeg, cx, cy, maxR) {
        const screenAngleDeg = 90 - azDeg;
        const angleRad = screenAngleDeg * Math.PI / 180;
        const r = maxR * (1 - elDeg / 90);
        const x = cx + r * Math.cos(angleRad);
        const y = cy - r * Math.sin(angleRad);
        return { x, y };
    }
</script>
</body>
</html>
"""

# ----- Helper: input validation -----
def validate_input(data):
    errors = []
    try:
        lat = float(data.get('lat', ''))
        if lat < -90 or lat > 90:
            errors.append('Latitude must be between -90 and 90.')
    except ValueError:
        errors.append('Latitude must be a number.')

    try:
        lon = float(data.get('lon', ''))
        if lon < -180 or lon > 180:
            errors.append('Longitude must be between -180 and 180.')
    except ValueError:
        errors.append('Longitude must be a number.')

    try:
        alt = float(data.get('alt', ''))
        if alt < 160:
            errors.append('Altitude must be at least 160 km.')
    except ValueError:
        errors.append('Altitude must be a number.')

    try:
        inc = float(data.get('inc', ''))
        if inc < 0 or inc > 180:
            errors.append('Inclination must be between 0 and 180.')
    except ValueError:
        errors.append('Inclination must be a number.')

    try:
        M0 = float(data.get('M0', 0))
        if M0 < 0 or M0 > 360:
            errors.append('Mean anomaly must be between 0 and 360.')
    except ValueError:
        errors.append('Mean anomaly must be a number.')

    start_str = data.get('start_time', '')
    end_str = data.get('end_time', '')
    try:
        start_time = datetime.fromisoformat(start_str)
        end_time = datetime.fromisoformat(end_str)
    except ValueError:
        return None, None, None, None, None, None, ['Invalid date/time format. Use YYYY-MM-DDTHH:MM.']

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    if end_time <= start_time:
        errors.append('End time must be after start time.')
    if (end_time - start_time) > timedelta(days=7):
        errors.append('Time range cannot exceed 7 days.')

    if errors:
        return None, None, None, None, None, None, errors
    return lat, lon, alt, inc, start_time, end_time, M0

# ----- Routes -----
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/predict', methods=['POST'])
def predict():
    lat, lon, alt, inc, start_time, end_time, M0 = validate_input(request.form)
    if lat is None:
        return jsonify({'error': '; '.join(start_time)})  # start_time holds errors list
    # Actually handle it properly:
    validation = validate_input(request.form)
    if validation[0] is None:
        errors = validation[-1]
        return jsonify({'error': '; '.join(errors)}), 400

    lat, lon, alt, inc, start_time, end_time, M0 = validation[:7]

    result = predict_passes(
        station_lat=lat,
        station_lon=lon,
        alt_km=alt,
        inc_deg=inc,
        start_utc=start_time,
        end_utc=end_time,
        M0_deg=M0
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)