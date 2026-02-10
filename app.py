#!/usr/bin/env python3
"""
Oracle Physical Standby Builder - Flask Application
Collects parameters via web UI and triggers GitHub Actions pipeline.
"""
import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "your-org/oracle-standby")  # owner/repo
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/dispatches"

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Main form page."""
    return render_template("index.html")


@app.route("/api/trigger", methods=["POST"])
def trigger_pipeline():
    """Receive form data and trigger GitHub Actions workflow."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Validate required fields
    required = {
        "primary_host": "Primary Host",
        "primary_sid": "Primary SID",
        "primary_db_unique_name": "Primary DB Unique Name",
        "primary_oracle_home": "Primary Oracle Home",
        "standby_host": "Standby Host",
        "standby_sid": "Standby SID",
        "standby_db_unique_name": "Standby DB Unique Name",
        "standby_oracle_home": "Standby Oracle Home",
    }
    missing = [v for k, v in required.items() if not data.get(k)]
    if missing:
        return jsonify({"error": f"Missing: {', '.join(missing)}"}), 400

    # Build the GitHub dispatch payload
    payload = {
        "event_type": "create-physical-standby",
        "client_payload": {
            "timestamp": datetime.utcnow().isoformat(),
            "primary": {
                "host": data["primary_host"],
                "ssh_port": data.get("primary_ssh_port", "22"),
                "sid": data["primary_sid"],
                "db_unique_name": data["primary_db_unique_name"],
                "listener_port": data.get("primary_listener_port", "1521"),
                "oracle_home": data["primary_oracle_home"],
                "oracle_base": data.get("primary_oracle_base", "/u01/app/oracle"),
                "oracle_version": data.get("oracle_version", "19c"),
                "db_role": data.get("primary_db_role", "single"),
                "is_cdb": data.get("is_cdb", False),
                "pdb_list": data.get("pdb_list", ""),
                "storage_type": data.get("primary_storage", "asm"),
                "asm_dg_data": data.get("primary_asm_data", "+DATA"),
                "asm_dg_fra": data.get("primary_asm_fra", "+FRA"),
                "data_dir": data.get("primary_data_dir", ""),
                "ssh_user": data.get("primary_ssh_user", "oracle"),
            },
            "standby": {
                "host": data["standby_host"],
                "ssh_port": data.get("standby_ssh_port", "22"),
                "sid": data["standby_sid"],
                "db_unique_name": data["standby_db_unique_name"],
                "listener_port": data.get("standby_listener_port", "1521"),
                "oracle_home": data["standby_oracle_home"],
                "oracle_base": data.get("standby_oracle_base", "/u01/app/oracle"),
                "db_role": data.get("standby_db_role", "single"),
                "storage_type": data.get("standby_storage", "asm"),
                "asm_dg_data": data.get("standby_asm_data", "+DATA"),
                "asm_dg_fra": data.get("standby_asm_fra", "+FRA"),
                "data_dir": data.get("standby_data_dir", ""),
                "fra_dir": data.get("standby_fra_dir", ""),
                "ssh_user": data.get("standby_ssh_user", "oracle"),
            },
            "rman": {
                "method": data.get("rman_method", "active_duplicate"),
                "parallelism": int(data.get("rman_parallelism", 4)),
                "compression": data.get("rman_compression", "NONE"),
                "section_size_mb": data.get("rman_section_size", ""),
                "backup_location": data.get("rman_backup_location", ""),
                "backup_tag": data.get("rman_backup_tag", ""),
                "db_file_name_convert": data.get("db_file_name_convert", ""),
                "log_file_name_convert": data.get("log_file_name_convert", ""),
                "nofilenamecheck": data.get("nofilenamecheck", True),
                "additional_commands": data.get("rman_additional", ""),
            },
            "network": {
                "redo_transport": data.get("redo_transport", "ASYNC"),
                "standby_redo_groups": int(data.get("standby_redo_groups", 4)),
                "standby_redo_size_mb": int(data.get("standby_redo_size", 200)),
                "net_timeout": int(data.get("net_timeout", 30)),
            },
            "options": {
                "force_logging": data.get("force_logging", True),
                "flashback": data.get("flashback", True),
                "archivelog_check": data.get("archivelog_check", True),
                "standby_file_mgmt": data.get("standby_file_mgmt", True),
                "start_mrp": data.get("start_mrp", True),
                "open_readonly": data.get("open_readonly", False),
                "real_time_apply": data.get("real_time_apply", False),
                "protection_mode": data.get("protection_mode", "MAX_PERFORMANCE"),
            },
            "notifications": {
                "email_to": data.get("email_to", ""),
                "smtp_server": data.get("smtp_server", ""),
                "slack_webhook": data.get("slack_webhook", ""),
            },
            "approvals": {
                "gate_precheck": data.get("gate_precheck", True),
                "gate_primary": data.get("gate_primary", True),
                "gate_rman": data.get("gate_rman", True),
                "gate_golive": data.get("gate_golive", True),
            },
        },
    }

    # Trigger GitHub Actions
    if not GITHUB_TOKEN:
        # Demo mode - just return success
        return jsonify({
            "success": True,
            "message": "Demo mode - pipeline payload generated",
            "run_url": f"https://github.com/{GITHUB_REPO}/actions",
            "payload": payload,
        })

    try:
        resp = requests.post(
            GITHUB_API,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {GITHUB_TOKEN}",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code == 204:
            return jsonify({
                "success": True,
                "message": "Pipeline triggered successfully!",
                "run_url": f"https://github.com/{GITHUB_REPO}/actions",
            })
        else:
            return jsonify({
                "error": f"GitHub API returned {resp.status_code}: {resp.text}"
            }), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate", methods=["POST"])
def validate_config():
    """Quick validation of the configuration before triggering."""
    data = request.get_json()
    warnings = []
    errors = []

    # Cross-field validations
    if data.get("primary_sid") == data.get("standby_sid"):
        if data.get("primary_host") == data.get("standby_host"):
            errors.append("Primary and Standby cannot have the same SID on the same host")

    if data.get("primary_db_unique_name") == data.get("standby_db_unique_name"):
        errors.append("DB_UNIQUE_NAME must be different between primary and standby")

    method = data.get("rman_method", "")
    if "backup" in method and not data.get("rman_backup_location"):
        errors.append("Backup location is required for backup-based duplicate")

    if data.get("standby_storage") == "filesystem" and not data.get("standby_data_dir"):
        errors.append("Standby data directory is required for filesystem storage")

    if data.get("is_cdb") and not data.get("pdb_list"):
        warnings.append("No PDB names specified — PDBs won't be opened on standby automatically")

    if data.get("rman_method") == "active_duplicate":
        warnings.append("Active duplicate requires network bandwidth — ensure sufficient bandwidth between primary and standby")

    if data.get("primary_storage") != data.get("standby_storage"):
        if not data.get("db_file_name_convert"):
            warnings.append("Different storage types detected — DB_FILE_NAME_CONVERT is recommended")

    return jsonify({"errors": errors, "warnings": warnings})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
