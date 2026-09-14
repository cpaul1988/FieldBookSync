"""Regenerate the source patch from a pristine v8.1.14 payload and edited copy."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--baseline",type=Path,required=True)
parser.add_argument("--working",type=Path,required=True)
args=parser.parse_args()
package=Path(__file__).resolve().parent
allowed={".py",".js",".cjs",".html",".css",".ps1",".go",".bat",".cmd",".txt",".md"}
paths={p.relative_to(root).as_posix() for root in (args.baseline,args.working) for p in root.rglob("*")
       if p.is_file() and p.suffix.lower() in allowed and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts}
def data(root,relative):
    p=root/relative
    return p.read_bytes() if p.is_file() else None
def sha(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None
changes={r:{"before":sha(data(args.baseline,r)),"after":sha(data(args.working,r))}
         for r in sorted(paths) if data(args.baseline,r)!=data(args.working,r)}
with tempfile.TemporaryDirectory(prefix="surveysense-diff-") as temporary:
    work=Path(temporary)
    subprocess.run(["git","init","--quiet",str(work)],check=True)
    for relative in changes:
        original=data(args.baseline,relative)
        if original is not None:
            target=work/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(original)
    subprocess.run(["git","-c","core.autocrlf=false","add","."],cwd=work,check=True)
    subprocess.run(["git","-c","user.name=SurveySense Patch Builder","-c","user.email=surveysense@localhost",
                    "commit","--quiet","-m","Verified v8.1.14 source baseline"],cwd=work,check=True)
    for relative in changes:
        updated=data(args.working,relative)
        target=work/relative
        if updated is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(updated)
    subprocess.run(["git","-c","core.autocrlf=false","add","-A"],cwd=work,check=True)
    patch=subprocess.check_output(["git","-c","core.autocrlf=false","diff","--cached","--binary","HEAD"],cwd=work)
    (package/"surveysense.patch").write_bytes(patch)
(package/"source_hashes.json").write_text(json.dumps({"baseline":"FieldBook Sync v8.1.14", "files":changes},indent=2)+"\n",encoding="utf-8")
print(f"Generated patch for {len(changes)} text files ({len(patch):,} bytes)")
