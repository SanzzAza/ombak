#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║          JEBRAY API CLIENT - WEB VERSION v1.0                ║
║                                                              ║
║  Single-file Flask app with built-in Turnstile captcha      ║
║  Run: python3 jebray_web.py                                  ║
║  Open: http://localhost:5000                                 ║
╚══════════════════════════════════════════════════════════════╝
"""

from flask import Flask, request, jsonify, render_template_string
import requests
import re
import json
import base64
import urllib3

urllib3.disable_warnings()

app = Flask(__name__)

# ═══════════════════════════════════════════════════
#  JEBRAY API CONFIG
# ═══════════════════════════════════════════════════
JEBRAY_URL = "https://jebray.com"
TURNSTILE_SITEKEY = "0x4AAAAAACkaiAH7yHzqJGyF"

# ═══════════════════════════════════════════════════
#  XOR ENCRYPTION (sama persis dengan jebray.com)
# ═══════════════════════════════════════════════════
def xor_encrypt(plaintext: str, key: str) -> str:
    encrypted = ''.join(
        chr(ord(c) ^ ord(key[i % len(key)]))
        for i, c in enumerate(plaintext)
    )
    return base64.b64encode(encrypted.encode('latin-1')).decode()

def get_keys(endpoint: str) -> tuple:
    """Get _ek and _kid from jebray page"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    session.verify = False
    
    r = session.get(f"{JEBRAY_URL}{endpoint}", timeout=15)
    
    ek = re.search(r"window\._ek\s*=\s*'([a-f0-9]+)'", r.text)
    kid = re.search(r"window\._kid\s*=\s*'([a-f0-9]+)'", r.text)
    
    if not ek or not kid:
        return None, None
    
    return ek.group(1), kid.group(1)

def call_jebray_api(endpoint: str, payload: dict) -> dict:
    """Send encrypted request to jebray"""
    try:
        ek, kid = get_keys(endpoint)
    except Exception as e:
        print(f"[ERROR] get_keys failed: {e}")
        return {"success": False, "error": f"Gagal ambil keys: {str(e)}"}
    
    if not ek:
        print("[ERROR] _ek/_kid not found in page")
        return {"success": False, "error": "Gagal ambil encryption keys dari jebray.com"}
    
    print(f"[INFO] Got keys ek={ek[:8]}...")
    payload_json = json.dumps(payload, separators=(',', ':'))
    encoded = xor_encrypt(payload_json, ek)
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"{JEBRAY_URL}{endpoint}",
        "Origin": JEBRAY_URL,
    })
    session.verify = False
    
    try:
        r = session.post(
            f"{JEBRAY_URL}{endpoint}",
            data={"data": encoded, "kid": kid},
            timeout=15
        )
        print(f"[INFO] Status: {r.status_code}, Body: {r.text[:300]}")
    except Exception as e:
        print(f"[ERROR] POST failed: {e}")
        return {"success": False, "error": f"Koneksi gagal: {str(e)}"}
    
    try:
        return r.json()
    except:
        return {"success": False, "error": f"Bukan JSON. Status:{r.status_code}. Body:{r.text[:200]}"}

# ═══════════════════════════════════════════════════
#  HTML TEMPLATE (Single Page App)
# ═══════════════════════════════════════════════════
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jebray API Client</title>
    <!-- Turnstile disabled -->
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0d0f14 0%, #1a1d24 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }
        
        .container {
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            padding: 30px 0;
        }
        
        .header h1 {
            font-size: 1.8rem;
            background: linear-gradient(90deg, #00e5a0, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .header p {
            color: #888;
            font-size: 0.9rem;
        }
        
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .tab {
            flex: 1;
            min-width: 100px;
            padding: 12px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #aaa;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
            font-size: 0.85rem;
        }
        
        .tab:hover {
            background: rgba(0,229,160,0.1);
            border-color: rgba(0,229,160,0.3);
        }
        
        .tab.active {
            background: rgba(0,229,160,0.15);
            border-color: #00e5a0;
            color: #00e5a0;
        }
        
        .card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 16px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 6px;
            color: #aaa;
            font-size: 0.85rem;
        }
        
        .form-group input {
            width: 100%;
            padding: 14px 16px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #fff;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #00e5a0;
            box-shadow: 0 0 0 3px rgba(0,229,160,0.1);
        }
        
        .form-group input::placeholder {
            color: #555;
        }
        
        .row {
            display: flex;
            gap: 12px;
        }
        
        .row .form-group {
            flex: 1;
        }
        
        .captcha-box { display: none !important; }
        
        .btn {
            width: 100%;
            padding: 16px;
            background: linear-gradient(135deg, #00e5a0, #00c896);
            border: none;
            border-radius: 12px;
            color: #000;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,229,160,0.3);
        }
        
        .btn:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .result {
            margin-top: 20px;
            display: none;
        }
        
        .result.show {
            display: block;
        }
        
        .result-card {
            background: rgba(0,229,160,0.05);
            border: 1px solid rgba(0,229,160,0.2);
            border-radius: 12px;
            padding: 20px;
        }
        
        .result-card.error {
            background: rgba(255,100,100,0.05);
            border-color: rgba(255,100,100,0.3);
        }
        
        .result-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .result-header .icon {
            font-size: 1.5rem;
        }
        
        .result-header .name {
            font-size: 1.2rem;
            font-weight: 600;
            color: #fff;
        }
        
        .result-header .id {
            font-size: 0.8rem;
            color: #888;
        }
        
        .bind-list {
            display: grid;
            gap: 8px;
        }
        
        .bind-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        
        .bind-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 700;
            color: #fff;
        }
        
        .bind-icon.mt { background: linear-gradient(135deg, #ff6b35, #f7931e); }
        .bind-icon.fb { background: linear-gradient(135deg, #1877f2, #0d65d9); }
        .bind-icon.gg { background: linear-gradient(135deg, #34a853, #0f9d58); }
        .bind-icon.tt { background: linear-gradient(135deg, #000, #333); }
        .bind-icon.ap { background: linear-gradient(135deg, #555, #333); }
        .bind-icon.gc { background: linear-gradient(135deg, #ff2d55, #ff375f); }
        .bind-icon.vk { background: linear-gradient(135deg, #4c75a3, #5181b8); }
        .bind-icon.tg { background: linear-gradient(135deg, #0088cc, #229ed9); }
        .bind-icon.wa { background: linear-gradient(135deg, #25d366, #128c7e); }
        
        .bind-info {
            flex: 1;
        }
        
        .bind-label {
            font-size: 0.75rem;
            color: #888;
        }
        
        .bind-value {
            font-size: 0.9rem;
            color: #ddd;
        }
        
        .bind-value.connected {
            color: #00e5a0;
        }
        
        .bind-value.disconnected {
            color: #666;
        }
        
        .bind-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .bind-dot.on { background: #00e5a0; box-shadow: 0 0 8px #00e5a0; }
        .bind-dot.off { background: #444; }
        
        .device-bar {
            display: flex;
            gap: 12px;
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        
        .device-chip {
            flex: 1;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            text-align: center;
        }
        
        .device-chip .label {
            font-size: 0.75rem;
            color: #888;
        }
        
        .device-chip .value {
            font-size: 1.2rem;
            font-weight: 600;
            color: #00e5a0;
        }
        
        .error-msg {
            color: #ff6b6b;
            font-size: 0.95rem;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid rgba(0,229,160,0.2);
            border-top-color: #00e5a0;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .panel { display: none; }
        .panel.active { display: block; }
        
        .suggestions {
            margin-top: 16px;
        }
        
        .suggestions h4 {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 10px;
        }
        
        .suggestion-item {
            padding: 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .suggestion-item:hover {
            background: rgba(0,229,160,0.1);
        }
        
        .suggestion-name {
            font-weight: 600;
            color: #fff;
        }
        
        .suggestion-id {
            font-size: 0.8rem;
            color: #888;
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: #555;
            font-size: 0.8rem;
        }
        
        .footer a {
            color: #00e5a0;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎮 Jebray API Client</h1>
            <p>MLBB Account Tools - Reversed API</p>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('search')">🔍 Search</div>
            <div class="tab" onclick="switchTab('find')">👤 Find Nick</div>
            <div class="tab" onclick="switchTab('bind')">🔗 Cek Bind</div>
            <div class="tab" onclick="switchTab('reset')">🔑 Reset PW</div>
        </div>
        
        <!-- SEARCH PANEL -->
        <div id="panel-search" class="panel active">
            <div class="card">
                <div class="row">
                    <div class="form-group" style="flex:2">
                        <label>Player ID</label>
                        <input type="text" id="search-pid" placeholder="e.g. 123456789" inputmode="numeric">
                    </div>
                    <div class="form-group" style="flex:1">
                        <label>Zone ID</label>
                        <input type="text" id="search-zid" placeholder="e.g. 2553" inputmode="numeric">
                    </div>
                </div>
                <div class="captcha-box">
                    <div class="cf-turnstile" data-sitekey="{{ sitekey }}" data-callback="onCaptcha" data-theme="dark"></div>
                </div>
                <button class="btn" id="search-btn" onclick="doSearch()">🔍 Search Player</button>
            </div>
            <div class="loading" id="search-loading">
                <div class="spinner"></div>
                <p>Searching player...</p>
            </div>
            <div class="result" id="search-result"></div>
        </div>
        
        <!-- FIND PANEL -->
        <div id="panel-find" class="panel">
            <div class="card">
                <div class="row">
                    <div class="form-group" style="flex:2">
                        <label>Nickname</label>
                        <input type="text" id="find-nick" placeholder="e.g. EVOS">
                    </div>
                    <div class="form-group" style="flex:1">
                        <label>Zone ID</label>
                        <input type="text" id="find-zid" placeholder="e.g. 2553" inputmode="numeric">
                    </div>
                </div>
                <div class="captcha-box">
                    <div class="cf-turnstile" data-sitekey="{{ sitekey }}" data-callback="onCaptcha" data-theme="dark"></div>
                </div>
                <button class="btn" id="find-btn" onclick="doFind()">👤 Find Player</button>
            </div>
            <div class="loading" id="find-loading">
                <div class="spinner"></div>
                <p>Finding player...</p>
            </div>
            <div class="result" id="find-result"></div>
        </div>
        
        <!-- CEK BIND PANEL -->
        <div id="panel-bind" class="panel">
            <div class="card">
                <div class="row">
                    <div class="form-group" style="flex:2">
                        <label>Player ID</label>
                        <input type="text" id="bind-pid" placeholder="e.g. 123456789" inputmode="numeric">
                    </div>
                    <div class="form-group" style="flex:1">
                        <label>Zone ID</label>
                        <input type="text" id="bind-zid" placeholder="e.g. 2553" inputmode="numeric">
                    </div>
                </div>
                <div class="captcha-box">
                    <div class="cf-turnstile" data-sitekey="{{ sitekey }}" data-callback="onCaptcha" data-theme="dark"></div>
                </div>
                <button class="btn" id="bind-btn" onclick="doBind()">🔗 Check Binding</button>
            </div>
            <div class="loading" id="bind-loading">
                <div class="spinner"></div>
                <p>Checking binding...</p>
            </div>
            <div class="result" id="bind-result"></div>
        </div>
        
        <!-- RESET PW PANEL -->
        <div id="panel-reset" class="panel">
            <div class="card">
                <div class="form-group">
                    <label>Moonton Email</label>
                    <input type="email" id="reset-email" placeholder="your@email.com">
                </div>
                <p style="color:#888; font-size:0.8rem; margin-bottom:16px;">
                    ⚠️ Reset Password menggunakan NetEase captcha yang berbeda. 
                    Fitur ini memerlukan integrasi tambahan.
                </p>
                <button class="btn" disabled>🔑 Reset Password (Coming Soon)</button>
            </div>
        </div>
        
        <div class="footer">
            <p>Powered by reversed jebray.com API</p>
            <p>Original: <a href="https://t.me/jebraytools" target="_blank">@jebraytools</a></p>
        </div>
    </div>
    
    <script>
        let captchaToken = 'bypass-localhost';
        
        function onCaptcha(token) {
            captchaToken = token;
            document.querySelectorAll('.btn').forEach(btn => {
                if (!btn.disabled || btn.textContent.includes('Coming')) return;
                btn.disabled = false;
            });
            // Enable current panel button
            const activePanel = document.querySelector('.panel.active');
            const btn = activePanel.querySelector('.btn');
            if (btn && !btn.textContent.includes('Coming')) {
                btn.disabled = false;
            }
        }
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById('panel-' + tab).classList.add('active');
            
            // Reset captcha
            if (typeof turnstile !== 'undefined') {
                turnstile.reset();
            }
            captchaToken = '';
            document.querySelectorAll('.btn').forEach(btn => {
                if (!btn.textContent.includes('Coming')) {
                    btn.disabled = true;
                }
            });
        }
        
        async function doSearch() {
            const pid = document.getElementById('search-pid').value.trim();
            const zid = document.getElementById('search-zid').value.trim();
            
            if (!pid || !zid) {
                alert('Please fill Player ID and Zone ID');
                return;
            }
            
            document.getElementById('search-loading').classList.add('show');
            document.getElementById('search-result').classList.remove('show');
            
            try {
                const r = await fetch('/api/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({player_id: pid, zone_id: zid, token: captchaToken})
                });
                const data = await r.json();
                showSearchResult(data);
            } catch(e) {
                showSearchResult({success: false, error: e.message});
            }
            
            document.getElementById('search-loading').classList.remove('show');
            resetCaptcha();
        }
        
        async function doFind() {
            const nick = document.getElementById('find-nick').value.trim();
            const zid = document.getElementById('find-zid').value.trim();
            
            if (!nick || !zid) {
                alert('Please fill Nickname and Zone ID');
                return;
            }
            
            document.getElementById('find-loading').classList.add('show');
            document.getElementById('find-result').classList.remove('show');
            
            try {
                const r = await fetch('/api/find', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({nickname: nick, zone_id: zid, token: captchaToken})
                });
                const data = await r.json();
                showFindResult(data);
            } catch(e) {
                showFindResult({success: false, error: e.message});
            }
            
            document.getElementById('find-loading').classList.remove('show');
            resetCaptcha();
        }
        
        async function doBind() {
            const pid = document.getElementById('bind-pid').value.trim();
            const zid = document.getElementById('bind-zid').value.trim();
            
            if (!pid || !zid) {
                alert('Please fill Player ID and Zone ID');
                return;
            }
            
            document.getElementById('bind-loading').classList.add('show');
            document.getElementById('bind-result').classList.remove('show');
            
            try {
                const r = await fetch('/api/cek-bind', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({player_id: pid, zone_id: zid, token: captchaToken})
                });
                const data = await r.json();
                showBindResult(data);
            } catch(e) {
                showBindResult({success: false, error: e.message});
            }
            
            document.getElementById('bind-loading').classList.remove('show');
            resetCaptcha();
        }
        
        function resetCaptcha() {
            captchaToken = 'bypass-localhost';
        }
        
        function showSearchResult(data) {
            const el = document.getElementById('search-result');
            
            if (data.success && data.redirect) {
                el.innerHTML = `
                    <div class="result-card">
                        <div class="result-header">
                            <span class="icon">✅</span>
                            <div>
                                <div class="name">Player Found!</div>
                                <div class="id">Redirect: ${data.redirect}</div>
                            </div>
                        </div>
                        <p>Player exists. Use "Cek Bind" to see full details.</p>
                    </div>
                `;
            } else {
                el.innerHTML = `
                    <div class="result-card error">
                        <div class="result-header">
                            <span class="icon">❌</span>
                            <div>
                                <div class="name">Error</div>
                            </div>
                        </div>
                        <p class="error-msg">${data.error || 'Unknown error'}</p>
                    </div>
                `;
            }
            el.classList.add('show');
        }
        
        function showFindResult(data) {
            const el = document.getElementById('find-result');
            
            if (data.success && data.redirect) {
                el.innerHTML = `
                    <div class="result-card">
                        <div class="result-header">
                            <span class="icon">✅</span>
                            <div>
                                <div class="name">Player Found!</div>
                                <div class="id">Redirect: ${data.redirect}</div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                let suggestionsHtml = '';
                if (data.suggestions && data.suggestions.length > 0) {
                    suggestionsHtml = `
                        <div class="suggestions">
                            <h4>Did you mean:</h4>
                            ${data.suggestions.map(s => `
                                <div class="suggestion-item" onclick="useSuggestion('${s.player_id}', '${s.server_id}')">
                                    <div class="suggestion-name">${s.nickname}</div>
                                    <div class="suggestion-id">ID: ${s.player_id} · Server: ${s.server_id}</div>
                                </div>
                            `).join('')}
                        </div>
                    `;
                }
                
                el.innerHTML = `
                    <div class="result-card error">
                        <div class="result-header">
                            <span class="icon">❌</span>
                            <div>
                                <div class="name">Not Found</div>
                            </div>
                        </div>
                        <p class="error-msg">${data.error || 'Player not found'}</p>
                        ${suggestionsHtml}
                    </div>
                `;
            }
            el.classList.add('show');
        }
        
        function useSuggestion(pid, zid) {
            switchTab('bind');
            document.querySelector('[onclick="switchTab(\'bind\')"]').click();
            document.getElementById('bind-pid').value = pid;
            document.getElementById('bind-zid').value = zid;
        }
        
        function showBindResult(data) {
            const el = document.getElementById('bind-result');
            
            if (data.success && data.data) {
                const d = data.data;
                const binds = [
                    {key: 'Moonton', icon: 'MT', cls: 'mt'},
                    {key: 'Facebook', icon: 'FB', cls: 'fb'},
                    {key: 'Google Play', icon: 'GG', cls: 'gg'},
                    {key: 'TikTok', icon: 'TT', cls: 'tt'},
                    {key: 'AppleID', icon: 'AP', cls: 'ap'},
                    {key: 'GAME CENTER', icon: 'GC', cls: 'gc'},
                    {key: 'VK', icon: 'VK', cls: 'vk'},
                    {key: 'Telegram', icon: 'TG', cls: 'tg'},
                    {key: 'WhatsApp', icon: 'WA', cls: 'wa'},
                ];
                
                let connected = 0;
                const bindHtml = binds.map(b => {
                    const val = d[b.key] || '(Not Connected)';
                    const isOn = val !== '(Not Connected)';
                    if (isOn) connected++;
                    return `
                        <div class="bind-item">
                            <div class="bind-icon ${b.cls}">${b.icon}</div>
                            <div class="bind-info">
                                <div class="bind-label">${b.key}</div>
                                <div class="bind-value ${isOn ? 'connected' : 'disconnected'}">${val}</div>
                            </div>
                            <div class="bind-dot ${isOn ? 'on' : 'off'}"></div>
                        </div>
                    `;
                }).join('');
                
                el.innerHTML = `
                    <div class="result-card">
                        <div class="result-header">
                            <span class="icon">🎮</span>
                            <div>
                                <div class="name">${d.nickname || 'Unknown'}</div>
                                <div class="id">ID: ${d.player_id || '-'} · Zone: ${d.server || '-'}</div>
                            </div>
                        </div>
                        <div class="bind-list">
                            ${bindHtml}
                        </div>
                        <div class="device-bar">
                            <div class="device-chip">
                                <div class="label">📱 Android</div>
                                <div class="value">${d['Device Login Android'] || 0}</div>
                            </div>
                            <div class="device-chip">
                                <div class="label">🍎 iOS</div>
                                <div class="value">${d['Device Login iOS'] || 0}</div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                el.innerHTML = `
                    <div class="result-card error">
                        <div class="result-header">
                            <span class="icon">❌</span>
                            <div>
                                <div class="name">Error</div>
                            </div>
                        </div>
                        <p class="error-msg">${data.error || 'Unknown error'}</p>
                    </div>
                `;
            }
            el.classList.add('show');
        }
    </script>
</body>
</html>
'''

# ═══════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sitekey=TURNSTILE_SITEKEY)

@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.get_json()
    player_id = data.get('player_id', '')
    zone_id = data.get('zone_id', '')
    token = data.get('token', '')
    
    result = call_jebray_api('/search', {
        'p': player_id,
        'z': zone_id,
        't': token
    })
    
    return jsonify(result)

@app.route('/api/find', methods=['POST'])
def api_find():
    data = request.get_json()
    nickname = data.get('nickname', '')
    zone_id = data.get('zone_id', '')
    token = data.get('token', '')
    
    result = call_jebray_api('/find', {
        'n': nickname,
        'z': zone_id,
        't': token
    })
    
    return jsonify(result)

@app.route('/api/cek-bind', methods=['POST'])
def api_cek_bind():
    data = request.get_json()
    player_id = data.get('player_id', '')
    zone_id = data.get('zone_id', '')
    token = data.get('token', '')
    
    result = call_jebray_api('/cek-bind', {
        'p': player_id,
        'z': zone_id,
        't': token
    })
    
    return jsonify(result)

# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║          🎮 JEBRAY API CLIENT - WEB VERSION 🎮              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Server running at: http://localhost:5000                    ║
║                                                              ║
║  Features:                                                   ║
║  ✅ Search Player (by ID)                                    ║
║  ✅ Find Player (by Nickname)                                ║
║  ✅ Cek Bind (Account Binding Status)                        ║
║  ⏳ Reset Password (NetEase captcha - coming soon)           ║
║                                                              ║
║  Press Ctrl+C to stop                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
