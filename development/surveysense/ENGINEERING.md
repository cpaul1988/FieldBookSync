# Engineering decisions

## Ground design

Source coordinates are first converted to one selected target grid. Source and target must have the same static geodetic datum realization. The tool rejects dynamic frames, datum ensembles, compound/bound CRSs and unsupported target axis layouts. FIPS zone identifiers are not treated as EPSG codes. There is no hardcoded list of “33 zones.”

At each sample, PROJ supplies the target projection's meridional and parallel scales. The preview requires them to agree within the stated numerical conformality checks. Their mean is the local grid scale, k.

For explicit ellipsoid height h in metres, the preview uses the Gaussian mean radius R = sqrt(M N), with M and N computed from the target ellipsoid at the sample latitude. The approximate local elevation factor is R/(R+h); the conventional local combined factor is CF = k R/(R+h), which multiplies ground distance to obtain grid distance. This is a local differential approximation, not a rigorous terrain-following line reduction.

For a grid-to-ground multiplier s, local residual distortion is (s CF - 1) × 10^6 ppm. The initial fit is s = 2/(min(CF)+max(CF)), which balances the extreme signed residuals and minimizes their maximum absolute value for the supplied samples. Sampling density is not a substitute for control validation; no claim is made about unsampled locations.

Ground coordinates keep the selected target-grid origin fixed and apply scale and counterclockwise rotation to coordinate differences about that origin. The target CRS alone does not describe the resulting project ground system; the exported parameters must accompany its coordinates.

The user's two supplied values, 1.0000878 and 1.0000712, are not directly averaged as factors from different zone grids. The numerical unit test using these values applies only after factors describe the same target grid. Missouri East/Central conversion has a separate test with declared NAD83 CRSs.

Primary references: [PROJ/pyproj projection factors](https://pyproj4.github.io/pyproj/stable/api/proj.html#pyproj.Proj.get_factors), [pyproj coordinate transformations](https://pyproj4.github.io/pyproj/stable/api/transformer.html), [NGS SPCS2022 example coordinates/distortion](https://beta.ngs.noaa.gov/SPCS/coordinates.shtml), [Esri ground-to-grid concepts](https://pro.arcgis.com/en/pro-app/3.3/help/editing/introduction-to-ground-to-grid.htm). The NGS beta site is not treated as an authoritative production transformation engine.

## Dip calculations and completion

A pipe invert is derived from a confirmed rim reference minus an actual measured vertical dip, with explicit conversion between metres, international feet (0.3048 m) and US survey feet (1200/3937 m). It does not reconstruct an unmeasured depth. Negative, missing and non-finite dip values remain flagged. Missing rim references block an invert. Operator review and calculation validity remain distinct.

The pickup map labels a structure complete only when its recorded pipe measurements have valid derived inverts, its dip status is YES, and operator review/QC permit completion. A PointID-only YES does not clear missing-dip work. A structure with unobserved pipes may still need additional field work; the software can evaluate only recorded observations.

GIS matching uses WGS84 ellipsoidal distance in metres. ECEF chord buckets bound candidate searches without longitude wrap or polar degree-distance assumptions. A candidate must be unique in both directions within the operator's tolerance. Duplicate asset identities, multiple candidates, and matching IDs outside tolerance stay visible as review cases. Unlocated records remain in the CSV checklist even though a map pin cannot be generated.

This workflow is supplemental structure matching. It does not yet use GIS pipe topology or calculated grades to change the existing AI connection graph.

## Spatial attributes and exports

The existing import drivers continue to define supported file formats. Within the values they return, the new codec preserves JSON-native nested data and uses `$surveysense_type`/`value` envelopes for exact long integers, Decimal values, temporal values, UUIDs, binary data, non-finite floats and tuples. Literal source objects containing the tag are escaped to prevent misinterpretation. Unknown Python types cause an explicit conversion error. The codec is not a native geodatabase driver or a guarantee that every output format can retain every source field.

Shapefile DBF field types/width/decimal places are retained. Observed type inventories explicitly distinguish null and missing fields without inventing source nullability/domain constraints. The attribute archive excludes display geometry and records not imported because of existing driver/feature limits. A re-import is necessary to preserve values previously stringified by older versions.

The field-book PDF uses source-page images and separate per-source notes. It does not infer annotation locations or modify original observations. Report generation fails if a referenced page is missing or outside the project page directory.

Delivery audit events are recorded after the artifact is built and checked. If project-state persistence fails, the event and partial artifact are removed and the request fails. Events have artifact/source hashes and settings; they are separate from undo/redo. They are not a tamper-proof external ledger or the future control-adjustment version history.

## External dependencies

[Trimble Connect documents a cloud API](https://developer.trimble.com/docs/connect/), but the actual crew service, app registration and account access are required before its import path can be implemented and verified. [Leica Infinity lists cloud/service integrations](https://leica-geosystems.com/products/gnss-systems/software/leica-infinity/capabilities/services); that page does not establish a public third-party API for every Leica collector workflow.

The authoritative control-averaging workbook, three-wire level workbook and professional report template were not available during this work. Their methods, tolerances, reporting and sample outputs must define those implementations. No spreadsheet mathematics or professional certification was invented.
