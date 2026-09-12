# SurveySense development

This branch contains working source changes against the **verified, published FieldBook Sync v8.1.14 installer**. It is a development snapshot, not a published update or a completed implementation of every requested feature.

The production update manifest and v8.1.14 release remain on the existing release workflow. New source is reconstructed from the installer plus a reviewable Git patch, because the repository currently stores release reconstruction scripts rather than a complete source checkout.

## Implemented in this snapshot

- **SurveySense branding:** window, startup screen, product labels, new exports, native launcher source and installer header. Existing storage paths, `.fbs` associations, theme preferences and updater identity remain compatible.
- **Updater shutdown:** the desktop host now watches the backend shutdown event. The previous desktop entry point did not consume that event, which explains the window remaining on “Closing for update…”.
- **Available point ranges:** captures all numeric IDs before profile filtering and exports from the active project. Older projects must re-import their raw point files or use the existing raw-file utility.
- **Pipe calculations:** explicit elevation/dip units, confirmed rim reference, per-pipe inverts, raw measurements, evidence citations and unresolved-QC flags. Missing depths are never inferred from an elevation.
- **Field-book review PDF:** source-page images, a pipe calculation summary and separate source-linked note pages. This is not the user's final professional survey-report template or a signature/seal operation.
- **Sewer pickup KMZ:** selected supplemental GIS structure points, unique matches within an explicit metre tolerance, four completion categories, embedded icons, full checklist and export manifest. Duplicate, displaced and competing matches remain review items. Completion covers the recorded pipes, not unobserved pipes.
- **Multi-zone ground preview:** converts sample coordinates from compatible source CRSs into one target grid; calculates local target-grid combined factors using explicit ellipsoid heights; fits a minimax ground multiplier; provides an interactive residual plot and design archive. Static matching datum realizations only. Ground coordinates are exported with origin, rotation, CRS and multiplier, without overwriting active survey points.
- **Spatial attributes:** preserves nested data, null versus empty, booleans, exact large integers, decimals, dates/times, UUIDs and binary values returned by supported import drivers. Tagged JSON prevents precision/type loss. DBF field definitions and observed attribute types are retained; an attribute archive is available. This does not add every spatial file driver or recover values already discarded by an older importer.
- **Delivery audit:** verified export checksums, source fingerprints, parameters, timestamps and export IDs persist with project state independently of undo/redo. This is not yet historical versioning for the requested control-adjustment engines.

## Build and review

Requires Python 3.12+, Git, and the application dependencies. No downloaded installer is executed.

```sh
python development/surveysense/build_source.py --out build/surveysense-source
# Or add: --installer /path/to/FieldBookSync_Setup_8.1.14.exe
python -m pip install -r build/surveysense-source/requirements.txt pytest httpx
```

Run from the reconstructed directory with a disposable `LOCALAPPDATA` directory while reviewing. Existing builds can discard newly added project fields when they resave a project.

```sh
cd build/surveysense-source
python -m pytest tests -q
npm install --no-save --no-audit --no-fund jsdom@30.0.1
python tests/run_ui_tests.py
python desktop.py
```

On Windows, set `LOCALAPPDATA` to the chosen test-data directory in the shell before starting `desktop.py`. For a browser preview, run `python run_browser.py` from the configured environment. The native GUI also requires WebView2 on Windows.

`build_source.py` removes the baseline's old `FieldBookSync.exe`. Rebuild the launcher from `installer/app_launcher.go` before assembling a development installer. A launcher compile check is included in CI; the full Windows installer/update/restart flow still needs a Windows test session. No stable release is triggered by this development workflow.

## Feature completion and inputs

| Tracker | Request | Current state / next input |
|---|---|---|
| FBS-0003 | Trimble / Leica cloud sync | Not implemented; needs exact collector/cloud services, approved API access and representative vendor exports. |
| FBS-0004 | Structure and per-pipe photos | Not implemented; needs representative filenames, photo metadata and field linkage examples. |
| FBS-0005 | Distortion visualization | Sampled interactive plot implemented; authoritative zone polygons and full project validation remain. |
| FBS-0006 | Historical control QC audit | Delivery provenance implemented; control engine revisioning remains with the workbook-based methods. |
| FBS-0007 | Stakeholder email | Not implemented; needs sender/provider/recipient configuration and finalized-report workflow. No email was sent. |
| FBS-0008 | SurveySense rename | Source and active product labels updated; Windows packaging verification remains. |
| FBS-0009 | Available point ranges | Implemented and tested. |
| FBS-0010 | Dip-derived pipe inverts | Implemented and tested with explicit units/reference. |
| FBS-0011 | Field-book dip PDF | Review copy implemented and inspected; validate with a representative project book. |
| FBS-0012 | GIS-assisted connection QA | Conservative GIS structure matching implemented for pickup; pipe topology, grade-based ranking and AI integration remain. Needs a linked field/GIS example. |
| FBS-0013 | Spatial field support | Attribute preservation and schema archive implemented for values available from current drivers; full geometry Z/M, domains/subtypes, native attachments and additional drivers remain. |
| FBS-0014 | Cross-zone ground system | Static same-datum design preview and coordinate export implemented; epoch-aware/new-frame transformations remain. Needs project limits, height basis, control and tolerance validation. |
| FBS-0015 | Pickup/completion KMZ | Implemented and tested; validate source mappings/tolerance with a project sample. |
| FBS-0016 | Control averaging | Needs the user's existing workbook, formulas and known-good results. |
| FBS-0017 | Three-wire level QC | Needs the existing workbook, sample level-book pages and approved tolerances. |
| FBS-0018 | Traverse adjustment | Needs constrained open/closed examples and approved method. Unconstrained open traverses must not be forced closed. |
| FBS-0019 | OPUS / RTK / VRS control | Needs representative observations/reports, datum/epoch/geoid metadata and averaging workbook. |
| FBS-0020 | Professional report PDF | Needs the established report template and completed control outputs. Signature/seal remains a human action. |

The centrally configured feedback form also still needs its Google Forms responder URL; the existing `feedback.json` value was blank during inspection.

## Verification

See `QA.md` and `ENGINEERING.md`. The synthetic test fixtures contain no user project observations, photos, account credentials or proprietary spreadsheet contents.
