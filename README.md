### Biotime

BioTime 8.5 attendance integration for ERPNext/HRMS. Sync devices, employees,
and transactions, then create Employee Checkin records automatically.

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

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app biotime
```

### Setup

1. Go to BioTime Settings and enter server URL, username, and password.
2. Click Test Connection to store the token.
3. Configure auto sync interval and which entities to sync.
4. Run Full Sync or Sync Transactions from the settings page.

### Notes

- Employee mapping defaults to Employee.attendance_device_id.
- Sync jobs create BioTime Sync Log records with counts and errors.
- Scheduled sync runs every 5 minutes and respects the interval in settings.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/biotime
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
