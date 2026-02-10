# Oracle Physical Standby Builder

End-to-end solution to create Oracle Physical Standby databases via RMAN Duplicate, with a Flask web UI, GitHub Actions CI/CD pipeline, and Ansible playbooks.

## Supported Scenarios

| Scenario | Primary | Standby | Storage | RMAN Method |
|---|---|---|---|---|
| Single → Single | SI | SI | ASM/FS | Active/Backup |
| RAC → RAC | RAC | RAC | ASM | Active/Backup |
| RAC → Single | RAC | SI | ASM/FS | Active/Backup |
| CDB Multitenant | CDB | CDB | ASM/FS | Active/Backup |
| Cross-storage | ASM | FS (or vice versa) | Mixed | Active/Backup |

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Flask Web UI │────▶│  GitHub Actions   │────▶│  Ansible Playbooks  │
│  (Form Input) │     │  (Orchestrator)   │     │  (Executor on DBs)  │
└──────────────┘     │                  │     └─────────────────────┘
                     │  4 Approval Gates │           │
                     │  Email at each    │     ┌─────┴──────┐
                     │  stage            │     │            │
                     └──────────────────┘   Primary    Standby
```

## Pipeline Stages

1. **Pre-Flight Checks** — SSH, Oracle Home, disk, archivelog, version
2. **📧 Notify** → Email/Slack pre-check results
3. **🔐 Gate 1** → Approval required
4. **Configure Primary** — Force logging, SRL, DG params, TNS, password file
5. **📧 Notify** → Email/Slack primary configured
6. **🔐 Gate 2** → Approval required
7. **Prepare Standby** — Dirs, init.ora, orapwd, TNS, static listener, NOMOUNT
8. **🔐 Gate 3** → Approval required
9. **RMAN Duplicate** — Active or Backup-based duplication
10. **📧 Notify** → Email/Slack RMAN result
11. **Post-Config** — Temp files, DG params, MRP, open PDBs
12. **🔐 Gate 4** → Approval required
13. **Validation** — Role, MRP, gap, switchover, DG status
14. **📧 Final Report** → Complete status email

## Quick Start

### 1. Run the Flask UI

```bash
cd app
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

### 2. Configure GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions:

| Secret | Description |
|---|---|
| `ORACLE_SYS_PASSWORD` | SYS password for both databases |
| `SSH_PRIVATE_KEY_PATH` | Path to SSH key on self-hosted runner |
| `SMTP_SERVER` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `SMTP_FROM` | Sender email address |
| `SLACK_WEBHOOK` | Slack webhook URL (optional) |

### 3. Configure GitHub Environments (Approval Gates)

Create these environments in Settings → Environments:
- `preflight-approval` — with required reviewers
- `primary-approval` — with required reviewers
- `rman-approval` — with required reviewers
- `golive-approval` — with required reviewers

### 4. Setup Self-Hosted Runner

The runner must have:
- SSH access to both primary and standby servers
- Ansible installed (`pip install ansible`)
- Network access to Oracle listener ports

```bash
# On the runner machine
pip install ansible
# Clone this repo and register as GitHub Actions runner
```

### 5. Deploy

1. Fill in the form in the Flask UI
2. Click "Deploy Standby"
3. GitHub Actions workflow triggers
4. Approve each gate as prompted
5. Receive email notifications at each stage

## Environment Variables (Flask)

```bash
export GITHUB_TOKEN="ghp_xxxxx"          # GitHub PAT with repo scope
export GITHUB_REPO="your-org/oracle-standby"  # owner/repo
```

## File Structure

```
├── app/
│   ├── app.py                  # Flask application
│   ├── templates/index.html    # Web UI
│   └── requirements.txt
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/hosts.yml
│   ├── group_vars/all.yml
│   └── playbooks/
│       ├── 01_preflight.yml        # Pre-flight checks
│       ├── 02_configure_primary.yml # Configure primary for DG
│       ├── 03_prepare_standby.yml   # Prepare standby + NOMOUNT
│       ├── 04_rman_duplicate.yml    # RMAN duplicate (all methods)
│       ├── 05_post_config.yml       # Post-config + start MRP
│       └── 06_validation.yml        # Full validation
└── .github/workflows/
    └── create-standby.yml      # GitHub Actions pipeline
```
