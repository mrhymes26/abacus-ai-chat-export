# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

- **Selected export:** Backend matched selection IDs against bare `item.id`, so duplicate IDs across deployments could export far more chats than selected. Matching now uses only the canonical key `type:deployment_id_or_empty:id`, aligned with the UI (`chatSelectionKey`).

### Changed

- **Chat table:** Long lists show the first 10 rows by default; optional expand/collapse with a note that “select all” applies to the full filtered list.
- **Export panel:** Explains job flow, ZIP timing, and “all” vs “selection” modes.
- **Conversation scopes:** Long scope lists use a preview (first 10 lines) with expand to edit the full textarea.

### Documentation

- **README:** Clarifies collapsed chat list, export/ZIP behavior, and related UX notes.
