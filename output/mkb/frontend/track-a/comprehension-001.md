BR-FRONTEND-011: Navbar Brand Text and Legacy Tag (NEEDS_VALIDATION)
Legacy navbar shows "📝 Note List" (brand) and "Legacy v1.0" (subdued tag with CSS class .legacy-tag coloured #888).
Type: TRANSFORMATION
Source: index.php:79-80
Implementation: Render Navbar component with brand text "📝 Note List". The "Legacy v1.0" tag requires product owner decision on whether to remove, retain, or replace with a new version indicator in the migrated React app.
NEEDS_VALIDATION: Confirm whether the "Legacy v1.0" tag should be removed in the migrated React app, retained as-is, or replaced with a version indicator.