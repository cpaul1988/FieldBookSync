# Development verification

Verified locally on 2026-09-12 with Python 3.12 and Node 24.

- **46 Python checks:** per-pipe calculations, exact unit conventions, invalid/missing measurements, PDF source evidence and path validation, old/new project behavior, raw PointID capture before code filtering, actual API exports, artifact checksums, failed-autosave rollback, GIS ambiguity/identity/distance matching, antimeridian handling, KMZ integrity, common-grid ground calculations, Missouri zone conversion, origin/rotation, incompatible datum rejection and spatial attribute preservation.
- **4 DOM integration checks against the actual local API:** pipe CSV download, GIS field selection and pickup KMZ download, interactive ground residual plot and design download, and visible failure for incomplete CSV values. These test DOM behavior through jsdom; they are not native WebView screenshots.
- JavaScript syntax checks pass for the main application and both new UI modules.
- The generated synthetic field-book PDF's summary and per-page dip-note pages were rendered and visually inspected. Its embedded source image is checked by the PDF test.
- The updater regression test simulates the desktop lifecycle and proves a backend shutdown request destroys the native window and reaches finalization. A real Windows self-update/restart was not run in this environment.

The source reconstruction script additionally checks the exact v8.1.14 installer size and SHA-256, validates the embedded ZIP, checks each changed source file before applying the patch, and verifies every resulting changed-file hash.

Before a stable release: run the complete Windows install/update/reopen flow, review packaging and native branding, validate the PDF/KMZ and ground design with representative user project files and known control, and complete the input-dependent features in the development README. No installer or stable release was published by this task.
