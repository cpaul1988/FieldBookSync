from pathlib import Path
import sys, hashlib

root=Path(sys.argv[1])

def rep(rel, old, new):
    p=root/rel
    s=p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'Expected patch anchor not found in {rel}: {old[:80]!r}')
    p.write_text(s.replace(old,new),encoding='utf-8',newline='')

def version_replace(rel):
    p=root/rel
    data=p.read_bytes()
    new=data.replace(b'8.1.18',b'8.1.19').replace(b'8_1_18',b'8_1_19')
    if new==data:
        raise SystemExit(f'No version marker replaced in {rel}')
    p.write_bytes(new)

version_files=[
'Install_PaddleOCR_GPU_Optional.bat','QA_REPORT.md','README.md','Reset_FieldBook_Sync_Test_Data.bat','VERSION.txt','bootstrap_windows.py',
'desktop.py','fieldbook_sync/__init__.py','fieldbook_sync/ai_reader.py','fieldbook_sync/app.py','fieldbook_sync/map_gis.py','fieldbook_sync/models.py',
'fieldbook_sync/static/app.js','fieldbook_sync/static/index.html','fieldbook_sync/static/styles.css','install_local_ai.bat','install_paddleocr_auto.bat',
'install_paddleocr_local.bat','install_qwen_local.bat','installer/README_INSTALLER_BUILD.md','installer/RELEASE_UPLOAD.txt','installer/provision_runtime.ps1',
'installer/setup_ui.ps1','run_browser.bat','run_windows.bat']
for rel in version_files:
    p=root/rel
    data=p.read_bytes()
    new=data.replace(b'8.1.18',b'8.1.19').replace(b'8_1_18',b'8_1_19')
    p.write_bytes(new)

# Native desktop shell: watch the FastAPI/runtime shutdown event so verified updates
# can close pywebview and return control to the parent launcher.
rep('desktop.py',
'''    bridge._shutdown_callback = request_native_shutdown\n\n    def on_shown() -> None:\n''',
'''    bridge._shutdown_callback = request_native_shutdown\n\n    def watch_application_shutdown() -> None:\n        # The FastAPI update endpoint requests shutdown after the installer has\n        # downloaded and been verified.  The browser-only runner already watches\n        # runtime.shutdown_event; the native pywebview shell must do the same or\n        # the UI remains stuck on "Closing for update..." and the parent launcher\n        # never regains control to start Setup.\n        runtime.shutdown_event.wait()\n        print(f"[FieldBook Sync shutdown] native_shutdown_event={time.perf_counter()-launch_started:.3f}s", flush=True)\n        server.should_exit = True\n        try:\n            window.destroy()\n        except Exception as exc:\n            print(f"[FieldBook Sync shutdown] window_destroy_failed={exc}", flush=True)\n\n    threading.Thread(\n        target=watch_application_shutdown,\n        name="FBS-native-shutdown-watch",\n        daemon=True,\n    ).start()\n\n    def on_shown() -> None:\n''')

old_notes='''RELEASE_NOTES = [\n    "Fixes the Windows Not Responding hang seen when continuing past the What's New screen.",\n    "The desktop pywebview bridge now exposes only the five intended native functions instead of recursively exposing an object that holds the native window.",\n    "Windows explicitly uses Edge WebView2, and nonessential recovery/GPU probes do not start until the main UI reports that it is ready.",\n    "The What's New Continue action now dismisses and paints the workspace before background startup tasks are staggered in.",\n    "Adds WebView shown/loaded startup timing markers so any remaining launch stall can be diagnosed from launcher logs.",\n    "Replaces browser-first bug/feature reporting with an in-app feedback wizard that creates an append-only local log, report IDs, optional privacy-safe diagnostics, and supporting-file folders.",\n    "Feedback reports can queue a text-only copy to the shared Google tracker while local evidence remains on the workstation; pending syncs are visible and retryable from Help.",\n    "Retains v8.1.17 CNA (Could Not Access) and CNL (Could Not Locate) dip-status recognition and all prior survey features.",\n]\n'''
new_notes='''RELEASE_NOTES = [\n    "Fixes the in-app updater getting stuck on Closing for update after the installer was already downloaded and verified.",\n    "The native desktop shell now watches the application shutdown event and closes itself so the parent launcher can start Setup automatically.",\n    "The update button also explicitly calls the native exit bridge after staging a verified update, providing a second independent handoff path.",\n    "Adds update-staging diagnostics so download/checksum failures can be distinguished from shutdown/handoff failures.",\n    "Retains the v8.1.18 Windows startup responsiveness fix, in-app feedback wizard, and CNA/CNL dip-status recognition.",\n]\n\n'''
rep('fieldbook_sync/app.py',old_notes,new_notes)
rep('fieldbook_sync/app.py',
'''        }, indent=2), encoding="utf-8")\n    except Exception as exc:\n''',
'''        }, indent=2), encoding="utf-8")\n        logger.info("Verified update v%s staged at %s; requesting native shutdown handoff", latest, destination)\n    except Exception as exc:\n''')

old_js="""    $('#updateInstallBtn')?.addEventListener('click',async()=>{const b=$('#updateInstallBtn');b.disabled=true;b.textContent='Downloading…';try{const r=await api('/api/update/download-install',{method:'POST',timeoutMs:0});toast(r.message||'Update installer started');b.textContent='Closing for update…';}catch(e){b.disabled=false;b.textContent=`Download & Install v${latest}`;toast(e.message,'error')}});\n"""
new_js="""    $('#updateInstallBtn')?.addEventListener('click',async()=>{const b=$('#updateInstallBtn');b.disabled=true;b.textContent='Downloading…';try{const r=await api('/api/update/download-install',{method:'POST',timeoutMs:0});toast(r.message||'Update installer started');b.textContent='Closing for update…';// v8.1.19: explicitly close the native shell after the verified handoff is written.\n      // The desktop shell also watches runtime.shutdown_event, so either mechanism can\n      // complete the launcher handoff if the other is delayed by WebView2.\n      setTimeout(()=>{try{if(window.pywebview?.api?.exit_app){window.pywebview.api.exit_app().catch?.(e=>console.warn('Update native exit failed',e));return}}catch(e){console.warn('Update native exit bridge failed',e)}fetch('/api/application/exit',{method:'POST',keepalive:true}).catch(()=>{})},75);\n    }catch(e){b.disabled=false;b.textContent=`Download & Install v${latest}`;toast(e.message,'error')}});\n"""
rep('fieldbook_sync/static/app.js',old_js,new_js)

notes='''# FieldBook Sync v8.1.19\n\n## Update Handoff Reliability Hotfix\n\n- Fixes the in-app updater getting stuck indefinitely on **Closing for update...** after the installer was already downloaded and verified.\n- The native pywebview desktop shell now watches the application shutdown event, closes the window, stops the local server, and returns control to the native launcher so Setup can start.\n- The update button also explicitly invokes the native `exit_app` bridge after the verified pending-update handoff is created. This provides a second independent shutdown path if WebView2 delays the event watcher.\n- Adds an update-staging diagnostic log entry so future handoff failures can be distinguished from download or checksum failures.\n- Preserves all v8.1.18 startup responsiveness fixes, CNA/CNL dip-status recognition, and the in-app feedback wizard.\n\n## Important upgrade note\n\nVersions 8.1.18 and earlier contain the stuck-closing bug. If an older version reaches **Closing for update...**, closing the main FieldBook Sync window manually allows the parent launcher to consume the already-staged update and start Setup. Once v8.1.19 is installed, future in-app updates should close automatically.\n'''
(root/'RELEASE_NOTES.md').write_text(notes,encoding='utf-8',newline='')
(root/'RELEASE_NOTES_v8_1_19.md').write_text(notes,encoding='utf-8',newline='')

# Reproduce the exact tested v8.1.19 launcher from the stable v8.1.18 launcher.
p=root/'FieldBookSync.exe'; data=bytearray(p.read_bytes())
patches=[
    (1552, bytes.fromhex('436873754932684b5a6c36784a6e3774657a704e')),
    (1573, bytes.fromhex('557871522d78503947334e357248625539747744')),
    (1594, bytes.fromhex('4f576e65396c6d323552504b36426b6834334f77')),
    (1615, bytes.fromhex('4f496c77775441')),
    (1623, bytes.fromhex('5f2d39536b31453741763679')),
    (1230713, bytes.fromhex('39')),
]
for off,b in patches:
    data[off:off+len(b)]=b
p.write_bytes(data)

# Verify the reconstructed payload is byte-for-byte the reviewed/tested candidate
# using the SHA-256 of its canonical per-file manifest.
lines=[]
for f in sorted(x for x in root.rglob('*') if x.is_file()):
    rel=f.relative_to(root).as_posix(); lines.append(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {rel}")
manifest=('\n'.join(lines)+'\n').encode('utf-8')
agg=hashlib.sha256(manifest).hexdigest()
if len(lines)!=124 or agg!='59ccf8f32616eb32100e45248ce1a80e236aa8adac17042d6f075d86d0aae3ad':
    raise SystemExit(f'Payload verification failed: files={len(lines)} manifest_sha256={agg}')
print(f'v8.1.19 payload verified: {len(lines)} files; manifest_sha256={agg}')
