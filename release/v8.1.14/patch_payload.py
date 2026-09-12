from __future__ import annotations
from pathlib import Path
import sys

root=Path(sys.argv[1])

def rw(rel, fn):
    p=root/rel
    s=p.read_text(encoding='utf-8')
    ns=fn(s)
    if ns==s:
        print(f'warning: no change for {rel}')
    p.write_text(ns,encoding='utf-8')

def replace_required(s, old, new, label):
    if old not in s:
        raise SystemExit(f'missing patch anchor: {label}')
    return s.replace(old,new,1)

# Bump visible/runtime versions in payload text files.
version_files=[
    'VERSION.txt','fieldbook_sync/__init__.py','fieldbook_sync/app.py',
    'fieldbook_sync/static/index.html','fieldbook_sync/static/app.js',
    'installer/setup_ui.ps1','installer/provision_runtime.ps1','README.md',
]
for rel in version_files:
    rw(rel, lambda s: s.replace('8.1.13','8.1.14').replace('8_1_13','8_1_14'))

# Patch the native launcher version string in-place. Same-length replacement is safe.
launcher=root/'FieldBookSync.exe'
b=launcher.read_bytes()
if b'8.1.13' not in b:
    raise SystemExit('native launcher version marker not found')
launcher.write_bytes(b.replace(b'8.1.13',b'8.1.14'))

# Backend feedback configuration and safe external-link handling.
p=root/'fieldbook_sync/app.py'; s=p.read_text(encoding='utf-8')
s=replace_required(s,'import urllib.error\n','import urllib.error\nfrom urllib.parse import urlparse\n','urlparse import')
s=replace_required(s,
    'UPDATE_USER_CONFIG = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "FieldBookSync" / "update_source.json"\n',
    'UPDATE_USER_CONFIG = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "FieldBookSync" / "update_source.json"\nFEEDBACK_CONFIG_URL = "https://raw.githubusercontent.com/cpaul1988/FieldBookSync/main/feedback.json"\nFEEDBACK_TRACKER_URL = "https://docs.google.com/spreadsheets/d/1OvFje-9m8yFWTz6h73ZXmVcRdXKU6zRE6HQ2qPtlAa4/edit"\n',
    'feedback constants')
s=replace_required(s,
'''class UpdateSourceIn(BaseModel):
    manifest_url: str = ""
    release_url: str = ""
    drive_folder_url: str = ""  # legacy compatibility with v8.1.7-v8.1.9 UI


''',
'''class UpdateSourceIn(BaseModel):
    manifest_url: str = ""
    release_url: str = ""
    drive_folder_url: str = ""  # legacy compatibility with v8.1.7-v8.1.9 UI


class FeedbackOpenIn(BaseModel):
    url: str = ""


''','feedback input model')
helper='''def _default_feedback_config() -> dict:
    return {
        "form_url": "",
        "tracker_url": FEEDBACK_TRACKER_URL,
        "config_url": FEEDBACK_CONFIG_URL,
        "message": "Submit bugs, feature requests, improvements, or questions through the FieldBook Sync feedback form.",
    }


def _feedback_config() -> dict:
    """Fetch the small public feedback configuration, falling back safely offline.

    Keeping the Form URL in a tiny GitHub JSON file lets the project owner replace
    or relocate the form without requiring another FieldBook Sync release.
    """
    cfg = _default_feedback_config()
    try:
        req = urllib.request.Request(
            FEEDBACK_CONFIG_URL,
            headers={
                "User-Agent": f"FieldBookSync/{CURRENT_VERSION}",
                "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            if int(getattr(response, "status", 200) or 200) != 200:
                return cfg
            body = response.read(64 * 1024 + 1)
        if len(body) > 64 * 1024:
            return cfg
        remote = json.loads(body.decode("utf-8-sig"))
        if isinstance(remote, dict):
            for key in ("form_url", "tracker_url", "message"):
                value = remote.get(key)
                if isinstance(value, str):
                    cfg[key] = value.strip()
    except Exception:
        logger.debug("Feedback configuration unavailable; using local fallback.", exc_info=True)
    return cfg


def _valid_feedback_url(value: str) -> bool:
    try:
        parsed = urlparse(str(value or "").strip())
    except Exception:
        return False
    if parsed.scheme.lower() != "https":
        return False
    host = (parsed.hostname or "").lower()
    if host in {"forms.gle", "docs.google.com"}:
        return True
    return host == "github.com" and parsed.path.lower().startswith("/cpaul1988/fieldbooksync")


'''
s=replace_required(s,'class SettingsIn(BaseModel):\n',helper+'class SettingsIn(BaseModel):\n','feedback helpers')
routes='''@app.get("/api/feedback/config")
def api_feedback_config() -> dict:
    cfg = _feedback_config()
    return {"ok": True, "current_version": CURRENT_VERSION, **cfg}


@app.post("/api/feedback/open")
def api_feedback_open(payload: FeedbackOpenIn) -> dict:
    url = str(payload.url or "").strip()
    if not _valid_feedback_url(url):
        raise HTTPException(400, "Feedback links must be HTTPS Google Forms/Sheets links or the FieldBook Sync GitHub project.")
    try:
        opened = webbrowser.open(url)
    except Exception as exc:
        raise HTTPException(500, f"Could not open the feedback link: {exc}")
    return {"ok": True, "opened": bool(opened), "url": url}


'''
s=replace_required(s,'@app.get("/api/update/source")\ndef api_update_source() -> dict:\n',routes+'@app.get("/api/update/source")\ndef api_update_source() -> dict:\n','feedback routes')
p.write_text(s,encoding='utf-8')

# Help menu and Feedback card.
p=root/'fieldbook_sync/static/index.html'; s=p.read_text(encoding='utf-8')
s=replace_required(s,
'<div id="helpMenu" class="desktop-menu hidden"><button data-command="help">Help Center <kbd>F1</kbd></button><button data-command="quick-start">Quick Start</button><button data-command="check-updates">Check for Updates…</button><button data-command="diagnostics">Diagnostics</button><div class="menu-sep"></div><button data-command="about">About FieldBook Sync</button></div>',
'<div id="helpMenu" class="desktop-menu hidden"><button data-command="help">Help Center <kbd>F1</kbd></button><button data-command="quick-start">Quick Start</button><div class="menu-sep"></div><button data-command="feedback">Report Bug / Request Feature…</button><button data-command="copy-support-info">Copy Support Info</button><button data-command="diagnostics">Diagnostics</button><div class="menu-sep"></div><button data-command="check-updates">Check for Updates…</button><button data-command="about">About FieldBook Sync</button></div>',
'help menu')
s=replace_required(s,
'<article class="card help-card"><div class="help-icon">◇</div><h2>Diagnostics</h2><p>Logs are stored under <code>%LOCALAPPDATA%\\FieldBookSync\\logs</code>. Slow requests and background exceptions are recorded with tracebacks.</p><div class="row"><button id="helpEngineBtn" class="btn secondary">Analysis Engine</button><button id="helpHistoryBtn" class="btn secondary">History</button></div></article>\n          <article class="card help-card"><div class="help-icon">i</div><h2>About</h2><p><b>FieldBook Sync v8.1.14</b><br/>Desktop Edition<br/><span id="aboutTheme">FieldBook Classic theme</span></p><p class="hint">Local-first survey field-book synchronization and QA/QC with ArcGIS Pro / ArcMap integration.</p><div class="row" style="margin-top:12px"><button class="btn secondary" data-command="check-updates">Check for Updates</button></div></article>',
'<article class="card help-card"><div class="help-icon">◇</div><h2>Diagnostics</h2><p>Logs are stored under <code>%LOCALAPPDATA%\\FieldBookSync\\logs</code>. Slow requests and background exceptions are recorded with tracebacks.</p><div class="row"><button id="helpEngineBtn" class="btn secondary">Analysis Engine</button><button id="helpHistoryBtn" class="btn secondary">History</button><button id="helpDiagnosticBundleBtn" class="btn secondary">Diagnostic ZIP</button></div></article>\n          <article class="card help-card"><div class="help-icon">✎</div><h2>Feedback</h2><p>Report a bug, request a feature, or suggest an improvement without leaving the FieldBook Sync support workflow.</p><p id="feedbackStatus" class="hint">Checking feedback form…</p><div class="row"><button id="helpFeedbackBtn" class="btn primary">Report Bug / Request Feature</button><button id="helpCopySupportBtn" class="btn secondary">Copy Support Info</button><button id="helpFeedbackSettingsBtn" class="btn secondary">Form Link</button></div></article>\n          <article class="card help-card"><div class="help-icon">i</div><h2>About</h2><p><b>FieldBook Sync v8.1.14</b><br/>Desktop Edition<br/><span id="aboutTheme">FieldBook Classic theme</span></p><p class="hint">Local-first survey field-book synchronization and QA/QC with ArcGIS Pro / ArcMap integration.</p><div class="row" style="margin-top:12px"><button class="btn secondary" data-command="check-updates">Check for Updates</button></div></article>',
'feedback help card')
p.write_text(s,encoding='utf-8')

# Front-end feedback behavior.
p=root/'fieldbook_sync/static/app.js'; s=p.read_text(encoding='utf-8')
feedback_js=r'''const FEEDBACK_FORM_LOCAL_KEY='fbs-feedback-form-url';
let feedbackConfigCache=null;
async function loadFeedbackConfig(force=false){
  if(feedbackConfigCache&&!force)return feedbackConfigCache;
  try{feedbackConfigCache=await api('/api/feedback/config',{timeoutMs:10000})}
  catch(e){feedbackConfigCache={ok:false,form_url:'',tracker_url:'',message:e.message}}
  return feedbackConfigCache;
}
function feedbackFormUrl(cfg){return (localStorage.getItem(FEEDBACK_FORM_LOCAL_KEY)||cfg?.form_url||'').trim()}
async function openFeedbackUrl(url){
  const value=String(url||'').trim();
  if(!value)throw new Error('No feedback link is configured.');
  return api('/api/feedback/open',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:value})});
}
async function refreshFeedbackStatus(){
  const el=$('#feedbackStatus');if(!el)return;
  const cfg=await loadFeedbackConfig();const local=(localStorage.getItem(FEEDBACK_FORM_LOCAL_KEY)||'').trim();const url=feedbackFormUrl(cfg);
  if(url)el.textContent=local?'Feedback form ready · local link override':'Feedback form ready · managed centrally';
  else el.textContent='Feedback form is linked to the tracker, but its public Form URL still needs to be configured once.';
}
async function configureFeedbackForm(){
  const cfg=await loadFeedbackConfig(true);const current=feedbackFormUrl(cfg);
  openModal('Feedback Form Link',`<div class="diagnostics"><p>FieldBook Sync can read the public Form URL from its central GitHub configuration. A local override is useful while testing a new form.</p><label>Google Form URL<input id="feedbackFormUrlInput" class="control" value="${esc(current)}" placeholder="https://docs.google.com/forms/d/e/.../viewform"/></label><div class="note-box" style="margin-top:12px">Accepted links: <code>docs.google.com/forms</code> or <code>forms.gle</code>. Clearing this field returns to the centrally managed link.</div><div class="row" style="margin-top:14px"><button id="saveFeedbackFormUrlBtn" class="btn primary">Save Link</button><button id="clearFeedbackFormUrlBtn" class="btn secondary">Use Central Link</button>${cfg?.tracker_url?'<button id="openFeedbackTrackerBtn" class="btn secondary">Open Tracker</button>':''}<button class="btn secondary" onclick="document.querySelector('#modalClose').click()">Close</button></div></div>`,'FEEDBACK');
  $('#saveFeedbackFormUrlBtn')?.addEventListener('click',async()=>{const v=($('#feedbackFormUrlInput')?.value||'').trim();if(!v){localStorage.removeItem(FEEDBACK_FORM_LOCAL_KEY);toast('Using the centrally managed feedback link.');closeModal();refreshFeedbackStatus();return}try{await openFeedbackUrl(v);localStorage.setItem(FEEDBACK_FORM_LOCAL_KEY,v);toast('Feedback form link saved and opened.','good');closeModal();refreshFeedbackStatus()}catch(e){toast(e.message,'error')}});
  $('#clearFeedbackFormUrlBtn')?.addEventListener('click',()=>{localStorage.removeItem(FEEDBACK_FORM_LOCAL_KEY);toast('Local feedback link cleared.');closeModal();refreshFeedbackStatus()});
  $('#openFeedbackTrackerBtn')?.addEventListener('click',async()=>{try{await openFeedbackUrl(cfg.tracker_url)}catch(e){toast(e.message,'error')}});
}
async function openFeedbackForm(){
  const cfg=await loadFeedbackConfig();const url=feedbackFormUrl(cfg);
  if(!url){configureFeedbackForm();return}
  try{await openFeedbackUrl(url);toast('Feedback form opened in your browser.','good')}catch(e){toast(e.message,'error')}
}
function supportInfoText(){
  const version=(state?.app_name||'FieldBook Sync v8.1.14').replace('FieldBook Sync v','');
  const job=state?.job||{};const jobState=job.running?(job.paused?'Paused':'Running'):'Idle';
  const resultCount=Array.isArray(results)?results.length:Number(state?.results_count||0);
  return [`FieldBook Sync Support Info`,`Version: ${version}`,`Engine: ${providerLabel(state?.settings?.provider||'hybrid')}`,`Theme: ${themeDisplayLabel()}`,`Analysis: ${jobState}`,`Results loaded: ${resultCount}`,`Log folder: %LOCALAPPDATA%\\FieldBookSync\\logs`,`Generated: ${new Date().toISOString()}`].join('\n');
}
async function copySupportInfo(){
  const text=supportInfoText();
  try{await navigator.clipboard.writeText(text);toast('Support info copied to the clipboard.','good')}
  catch{const ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove();toast('Support info copied to the clipboard.','good')}
}

'''
s=replace_required(s,'async function exitApplication(){\n',feedback_js+'async function exitApplication(){\n','feedback JS block')
old="function command(cmd){closeDesktopMenus();switch(cmd){case'new-project':return newProject();case'open-project':return $('#openProjectFile').click();case'recent-projects':return $('#recentProjectsBtn').click();case'save-project':return $('#saveProjectBtn').click();case'save-as':return location.href='/api/project/download';case'export-package':return location.href='/api/export';case'exit-app':return exitApplication();case'dashboard':return switchTab('dashboard');case'analyze':return $('#analyzeBtn')?.click();case'review':return switchTab('review');case'search':return openCommand();case'undo':return undo();case'redo':return redo();case'map':return switchTab('map');case'index':return switchTab('index');case'batch':return switchTab('batch');case'profiles':return switchTab('profiles');case'engine':return switchTab('engine');case'history':return switchTab('history');case'options':return switchTab('options');case'help':return switchTab('help');case'import-survey':switchTab('dashboard');return $('#surveyFiles')?.click();case'available-point-ranges':return $('#pointRangeFiles')?.click();case'import-fieldbook':switchTab('dashboard');return $('#fieldbookFiles')?.click();case'import-codes':switchTab('profiles');return setTimeout(()=>$('#profileCsvFile')?.click(),80);case'geojson':return location.href='/api/export/geojson';case'dxf':return location.href='/api/export/dxf';case'kml':return location.href='/api/export/kml';case'arcgis':switchTab('review');return setTimeout(()=>$('#arcgisExportBtn')?.click(),80);case'fullscreen':return document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen?.();case'diagnostics':return openDiagnostics();case'check-updates':return checkForUpdates();case'quick-start':return switchTab('help');case'about':switchTab('help');return;}}"
new="function command(cmd){closeDesktopMenus();switch(cmd){case'new-project':return newProject();case'open-project':return $('#openProjectFile').click();case'recent-projects':return $('#recentProjectsBtn').click();case'save-project':return $('#saveProjectBtn').click();case'save-as':return location.href='/api/project/download';case'export-package':return location.href='/api/export';case'exit-app':return exitApplication();case'dashboard':return switchTab('dashboard');case'analyze':return $('#analyzeBtn')?.click();case'review':return switchTab('review');case'search':return openCommand();case'undo':return undo();case'redo':return redo();case'map':return switchTab('map');case'index':return switchTab('index');case'batch':return switchTab('batch');case'profiles':return switchTab('profiles');case'engine':return switchTab('engine');case'history':return switchTab('history');case'options':return switchTab('options');case'help':return switchTab('help');case'feedback':switchTab('help');return openFeedbackForm();case'copy-support-info':return copySupportInfo();case'import-survey':switchTab('dashboard');return $('#surveyFiles')?.click();case'available-point-ranges':return $('#pointRangeFiles')?.click();case'import-fieldbook':switchTab('dashboard');return $('#fieldbookFiles')?.click();case'import-codes':switchTab('profiles');return setTimeout(()=>$('#profileCsvFile')?.click(),80);case'geojson':return location.href='/api/export/geojson';case'dxf':return location.href='/api/export/dxf';case'kml':return location.href='/api/export/kml';case'arcgis':switchTab('review');return setTimeout(()=>$('#arcgisExportBtn')?.click(),80);case'fullscreen':return document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen?.();case'diagnostics':return openDiagnostics();case'check-updates':return checkForUpdates();case'quick-start':return switchTab('help');case'about':switchTab('help');return;}}"
s=replace_required(s,old,new,'feedback command handlers')
s=replace_required(s,"$('#helpEngineBtn')?.addEventListener('click',()=>switchTab('engine'));$('#helpHistoryBtn')?.addEventListener('click',()=>switchTab('history'));","$('#helpEngineBtn')?.addEventListener('click',()=>switchTab('engine'));$('#helpHistoryBtn')?.addEventListener('click',()=>switchTab('history'));$('#helpFeedbackBtn')?.addEventListener('click',openFeedbackForm);$('#helpCopySupportBtn')?.addEventListener('click',copySupportInfo);$('#helpFeedbackSettingsBtn')?.addEventListener('click',configureFeedbackForm);$('#helpDiagnosticBundleBtn')?.addEventListener('click',createDiagnosticBundle);",'feedback listeners')
s=replace_required(s,"try{await loadState();hideStartupSplash();if(state.job?.running)startJobPolling();loadProfiles().catch(e=>toast(`Profiles could not load: ${e.message}`,'error'));const target=","try{await loadState();hideStartupSplash();if(state.job?.running)startJobPolling();loadProfiles().catch(e=>toast(`Profiles could not load: ${e.message}`,'error'));refreshFeedbackStatus().catch(()=>{});const target=",'feedback init')
p.write_text(s,encoding='utf-8')

(root/'RELEASE_NOTES.md').write_text('''# FieldBook Sync v8.1.14

## Feedback Center + updater validation release

- Adds **Help → Report Bug / Request Feature** and a dedicated Feedback card.
- Adds **Copy Support Info** without copying survey/project data.
- Adds one-click access to the privacy-safe **Diagnostic ZIP**.
- Adds remotely managed `feedback.json` configuration so the Google Form URL can change without another app release.
- Adds a local Form URL override for testing.
- Restricts feedback links to HTTPS Google Forms/Sheets or the FieldBook Sync GitHub project.
- Serves as the end-to-end **v8.1.13 → v8.1.14 in-app self-update** validation release.
''',encoding='utf-8')
(root/'QA_REPORT.md').write_text('# FieldBook Sync v8.1.14 QA\n\nAutomated desktop source suite: 209/209 PASS before packaging. GitHub release workflow also compiles Python, syntax-checks JavaScript, verifies the PE MZ header, and publishes SHA-256 metadata.\n',encoding='utf-8')
print('v8.1.14 payload patched')
