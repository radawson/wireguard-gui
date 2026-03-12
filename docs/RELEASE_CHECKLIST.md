# Release Checklist

- [ ] Update changelog and release notes.
- [ ] Run test suite (`pytest`).
- [ ] Run DB validation script on a production DB copy.
- [ ] Run DB backfill script on a production DB copy.
- [ ] Build frontend CSS (`npm run build:css`).
- [ ] Verify smoke test flows (login, dashboard, network CRUD, peer CRUD, wizard).
- [ ] Confirm docs are updated (`INSTALLATION`, `UPGRADE`, `CONFIGURATION`, `OPERATIONS`).
