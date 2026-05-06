# APTRANSCO branding assets

The PDF report generator (`src/sfra_full/reports/pdf.py`) auto-includes
the first matching letterhead asset from this folder, in this order:

    aptransco_logo.png
    aptransco_logo.jpg
    aptransco_logo.jpeg
    aptransco_logo.svg

If you have an official high-resolution PNG/JPG of the APTRANSCO logo,
drop it here as `aptransco_logo.png` (or `.jpg`) — it will take
precedence over the SVG recreation that ships in this folder.

The committed `aptransco_logo.svg` is a vector recreation of the public
AP TRANSCO ISO 27001-2022 logo (transmission tower + lightning bolts +
"AP TRANSCO / ISO 27001 - 2022" badge) suitable for development and
internal builds. Replace with the official asset for substation
production deployments.

Logo files larger than 750 KB are blocked by the pre-commit
`check-added-large-files` hook — keep the asset under that limit or
override the hook in `.pre-commit-config.yaml` for that one file.
