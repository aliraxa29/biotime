# Biotime

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Security Policy](https://img.shields.io/badge/security-policy-blue.svg)](./SECURITY.md)
[![Code of Conduct](https://img.shields.io/badge/code%20of%20conduct-active-brightgreen)](./CODE_OF_CONDUCT.md)
[![Contributing](https://img.shields.io/badge/contributions-welcome-orange.svg)](./CONTRIBUTING.md)

**BioTime 8.5** attendance integration for ERPNext/HRMS. Sync devices, employees, and transactions, then create Employee Checkin records automatically.

### Features

- Two token types supported: JWT and General auth tokens
- Full entity sync: devices, employees, departments, areas, positions
- Transaction log sync with punch state to IN/OUT mapping
- Automatic Employee Checkin creation in HRMS
- Employee mapping using Employee.attendance_device_id
- Sync audit trail with detailed logs
- Admin tools to test connection, run full sync, or sync single entities
- Workspace with stats, shortcuts, and charts

### DocTypes

- BioTime Settings (single)
- BioTime Device
- BioTime Employee
- BioTime Department
- BioTime Area
- BioTime Position
- BioTime Transaction Log
- BioTime Sync Log

### Workspace Widgets

- Number cards: devices, mapped employees, unmapped employees, today transactions
- Charts: checkins this month, sync activity by status
- Shortcuts and link cards for quick navigation


---

## Installation

Install using [Frappe Bench](https://github.com/frappe/bench):

```bash
cd /path/to/your/bench
bench get-app https://github.com/yourorg/biotime.git
bench install-app biotime
```


## Setup

1. Go to **BioTime Settings** and enter server URL, username, and password.
2. Click **Test Connection** to store the token.
3. Configure auto sync interval and which entities to sync.
4. Run **Full Sync** or **Sync Transactions** from the settings page.


## Notes

- Employee mapping defaults to `Employee.attendance_device_id`.
- Sync jobs create **BioTime Sync Log** records with counts and errors.
- Scheduled sync runs every 5 minutes and respects the interval in settings.


## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).

This app uses `pre-commit` for code formatting and linting. To set up:

```bash
cd apps/biotime
pre-commit install
```

Pre-commit checks:
- ruff
- eslint
- prettier
- pyupgrade


## Security

Please review our [SECURITY.md](./SECURITY.md) for reporting vulnerabilities and supported versions.

## Code of Conduct

All contributors and participants are expected to follow our [Code of Conduct](./CODE_OF_CONDUCT.md).

## CI

This app uses GitHub Actions for CI:
- Installs this app and runs unit tests on every push to `main` or `develop`.
- Linters: [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules), [pip-audit](https://pypi.org/project/pip-audit/).



## License

This project is licensed under the [MIT License](./LICENSE).
