# FieldBook Sync

FieldBook Sync is a local-first Windows application for survey field-book OCR, review, mapping, QA/QC, and export.

## Current release line

- Desktop installer: Windows x64
- Publisher: Clever Bird Development
- Project files: `.fbs`
- Local AI: PaddleOCR + Ollama/Qwen
- GIS/CAD workflows: ArcGIS Pro integration, KML/KMZ/Shapefile/File GDB import, map/network review

## Updates

FieldBook Sync uses this repository as its stable update source.

The application checks:

`https://raw.githubusercontent.com/cpaul1988/FieldBookSync/main/update.json`

Installers are intended to be published as GitHub Release assets. The update manifest records the latest version, installer URL, SHA-256 checksum, release notes, and update channel.

## Release safety

The updater verifies the downloaded installer before launching it. Release manifests should only be updated after the final installer SHA-256 is known.

## Maintainer

Clever Bird Development
