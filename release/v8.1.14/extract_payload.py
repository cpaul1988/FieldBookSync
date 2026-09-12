from __future__ import annotations
import io, struct, sys, zipfile
from pathlib import Path

src=Path(sys.argv[1]); out=Path(sys.argv[2]); data=src.read_bytes()
starts=[]; pos=0
while True:
    i=data.find(b'PK\x03\x04',pos)
    if i<0: break
    starts.append(i); pos=i+1
ends=[]; pos=0
while True:
    i=data.find(b'PK\x05\x06',pos)
    if i<0: break
    ends.append(i); pos=i+1
for start in starts:
    for eocd in reversed(ends):
        if eocd<=start or eocd+22>len(data):
            continue
        comment_len=struct.unpack_from('<H',data,eocd+20)[0]
        end=eocd+22+comment_len
        try:
            blob=data[start:end]
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                names=set(z.namelist())
                if 'fieldbook_sync/app.py' not in names or 'installer/setup_ui.ps1' not in names:
                    continue
                out.mkdir(parents=True,exist_ok=True)
                z.extractall(out)
                print(f'Extracted {len(names)} payload files from offset {start}.')
                raise SystemExit(0)
        except (zipfile.BadZipFile,ValueError):
            pass
raise SystemExit('Could not locate the embedded FieldBook Sync payload ZIP.')
