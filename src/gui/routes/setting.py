from flask import Blueprint, current_app, flash, render_template, redirect, request, url_for
from flask_login import login_required
from ..models import db, Config, Network, Peer, config_load_test_db,network_load_test_db,peer_load_test_db
from gui.services import runtime_sync_service

settings = Blueprint('settings', __name__, url_prefix="/settings")

RUNTIME_CONFIG_FIELDS = [
    {"key": "MODE", "label": "Mode", "type": "select", "choices": ["database", "server"], "section": "server"},
    {"key": "HOST_IP", "label": "Host IP", "type": "text", "section": "server"},
    {"key": "HOST_PORT", "label": "Host Port", "type": "text", "section": "server"},
    {"key": "BASE_IP", "label": "Base IPv4 Network", "type": "text", "section": "network"},
    {"key": "BASE_NETMASK", "label": "Base IPv4 Netmask", "type": "text", "section": "network"},
    {"key": "BASE_PORT", "label": "Base WireGuard Port", "type": "text", "section": "network"},
    {"key": "BASE_DNS", "label": "Base DNS", "type": "text", "section": "network"},
    {"key": "BASE_KEEPALIVE", "label": "Base Keepalive", "type": "text", "section": "network"},
    {"key": "ADAPTER_PREFIX", "label": "Adapter Prefix", "type": "text", "section": "network"},
    {"key": "PEER_ACTIVITY_TIMEOUT", "label": "Peer Activity Timeout (seconds)", "type": "number", "section": "network"},
    {"key": "OUTPUT_DIR", "label": "Output Directory", "type": "text", "section": "paths"},
    {"key": "LOG_DIR", "label": "Log Directory", "type": "text", "section": "paths"},
    {"key": "SUDO_PASSWORD", "label": "Sudo Password", "type": "password", "section": "security"},
]

RUNTIME_CONFIG_SECTION_METADATA = [
    {"id": "server", "title": "Server", "description": "Process mode and HTTP listener values."},
    {"id": "network", "title": "Networking", "description": "Default WireGuard network and peer behavior values."},
    {"id": "paths", "title": "Paths", "description": "Output and log directory locations for this runtime."},
    {"id": "security", "title": "Security", "description": "Sensitive values used for privileged operations."},
]


def _runtime_config_view():
    runtime_config = []
    for field in RUNTIME_CONFIG_FIELDS:
        value = current_app.config.get(field["key"], "")
        if field["type"] == "password":
            value = ""
        runtime_config.append({**field, "value": value})
    section_map = {section["id"]: {**section, "fields": []} for section in RUNTIME_CONFIG_SECTION_METADATA}
    for field in runtime_config:
        section_id = field.get("section", "server")
        if section_id in section_map:
            section_map[section_id]["fields"].append(field)
    return [section_map[section["id"]] for section in RUNTIME_CONFIG_SECTION_METADATA]


def _validate_runtime_setting(key: str, value: str):
    if key == "MODE":
        if value not in {"database", "server"}:
            return False, value, "MODE must be either 'database' or 'server'."
        return True, value, ""
    if key in {"HOST_PORT", "BASE_PORT"}:
        if not value.isdigit() or not (1 <= int(value) <= 65535):
            return False, value, f"{key} must be a number between 1 and 65535."
        return True, value, ""
    if key == "BASE_NETMASK":
        if not value.isdigit() or not (1 <= int(value) <= 32):
            return False, value, "BASE_NETMASK must be a number between 1 and 32."
        return True, value, ""
    if key == "PEER_ACTIVITY_TIMEOUT":
        if not value.isdigit() or int(value) < 0:
            return False, value, "PEER_ACTIVITY_TIMEOUT must be a non-negative integer."
        return True, int(value), ""
    return True, value, ""

@settings.route('/', methods=['GET','POST'])
@login_required
def settings_detail():
    if request.method == 'POST':
        for field in RUNTIME_CONFIG_FIELDS:
            key = field["key"]
            if key not in request.form:
                continue
            raw_value = request.form.get(key, "").strip()
            if key == "SUDO_PASSWORD" and raw_value == "":
                # Empty password field means "leave existing value unchanged".
                continue
            ok, parsed_value, error = _validate_runtime_setting(key, raw_value)
            if not ok:
                flash(error, "danger")
                return render_template("settings.html", runtime_config_sections=_runtime_config_view())
            current_app.config[key] = parsed_value
        flash("Runtime configuration updated for this process.", "success")
        return redirect(url_for("settings.settings_detail"))

    return render_template('settings.html', runtime_config_sections=_runtime_config_view())

@settings.route('/test_db')
@login_required
def test_db_entries():
    config_load_test_db()
    network_load_test_db()
    peer_load_test_db()
    message = "Database entries loaded successfully!"
    flash(message, "success")
    return redirect(url_for("settings.settings_detail"))

@settings.route('/purge_db', methods=['POST'])
@login_required
def purge_db():
    db.session.query(Config).delete()
    db.session.query(Peer).delete()
    db.session.query(Network).delete()
    db.session.commit()
    message = "Database purged successfully!"
    flash(message, "success")
    return redirect(url_for("settings.settings_detail"))


@settings.route("/resync_runtime", methods=["POST"])
@login_required
def resync_runtime():
    if current_app.config.get("MODE") != "server":
        flash("Runtime sync is only available in server mode.", "warning")
        return redirect(url_for("settings.settings_detail"))
    summary = runtime_sync_service.sync_runtime_state(current_app.config.get("SUDO_PASSWORD", ""))
    flash(summary.to_message(), "info")
    return redirect(url_for("settings.settings_detail"))