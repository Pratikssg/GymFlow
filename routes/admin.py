from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from services.dynamo_db import db
from boto3.dynamodb.conditions import Attr
from datetime import datetime
import uuid
import io
import csv
from openpyxl import Workbook

bp = Blueprint('admin', __name__, url_prefix='/admin')

# ---------------------------
# Admin Dashboard
# ---------------------------
@bp.route('/dashboard')
def dashboard():
    users = db['Users'].scan().get('Items', [])
    reservations = db['Reservations'].scan().get('Items', [])
    workouts = db['Workouts'].scan().get('Items', [])
    equipment = db['Equipment'].scan().get('Items', [])
    maintenance = db.get('MaintenanceLogs', {'Items': []}).get('Items', [])

    member_count = sum(1 for u in users if u.get('role') == 'member')
    trainer_count = sum(1 for u in users if u.get('role') == 'trainer')
    admin_count = sum(1 for u in users if u.get('role') == 'admin')

    stats = {
        "total_members": member_count,
        "total_trainers": trainer_count,
        "total_admins": admin_count,
        "total_reservations": len(reservations),
        "total_workouts": len(workouts),
        "equipment_count": len(equipment),
        "maintenance_count": len(maintenance)
    }

    return render_template("admin_dashboard.html", stats=stats)

# ---------------------------
# Equipment Inventory
# ---------------------------
@bp.route('/inventory')
def inventory():
    response = db['Equipment'].scan()
    equipment_list = response.get('Items', [])
    return render_template('admin_inventory.html', equipment=equipment_list)

@bp.route('/inventory/add', methods=['POST'])
def add_equipment():
    name = request.form.get('name')
    status = request.form.get('status', 'Available')
    if not name:
        flash("Equipment name is required", "warning")
        return redirect(url_for('admin.inventory'))

    item = {
        'equipment_id': str(uuid.uuid4()),
        'name': name,
        'status': status
    }
    db['Equipment'].put_item(Item=item)
    flash("Equipment added successfully", "success")
    return redirect(url_for('admin.inventory'))

@bp.route('/inventory/update/<equipment_id>', methods=['POST'])
def update_equipment(equipment_id):
    name = request.form.get('name')
    status = request.form.get('status')
    if name and status:
        db['Equipment'].update_item(
            Key={'equipment_id': equipment_id},
            UpdateExpression="SET #n = :name, #s = :status",
            ExpressionAttributeNames={'#n': 'name', '#s': 'status'},
            ExpressionAttributeValues={':name': name, ':status': status}
        )
        flash("Equipment updated successfully", "success")
    else:
        flash("Both name and status are required", "warning")
    return redirect(url_for('admin.inventory'))

@bp.route('/inventory/delete/<equipment_id>', methods=['POST'])
def delete_equipment(equipment_id):
    db['Equipment'].delete_item(Key={'equipment_id': equipment_id})
    flash("Equipment deleted successfully", "info")
    return redirect(url_for('admin.inventory'))

# ---------------------------
# Analytics
# ---------------------------
@bp.route('/analytics')
def analytics():
    reservations = db['Reservations'].scan().get('Items', [])
    total_reservations = len(reservations)

    usage = {}
    for r in reservations:
        eid = r.get('equipment_id')
        if eid:
            usage[eid] = usage.get(eid, 0) + 1

    equipment_data = db['Equipment'].scan().get('Items', [])
    equipment_map = {e['equipment_id']: e['name'] for e in equipment_data}

    usage_stats = [
        {
            "equipment_id": eid,
            "equipment_name": equipment_map.get(eid, "Unknown"),
            "count": count
        }
        for eid, count in usage.items()
    ]

    return render_template(
        "admin_analytics.html",
        usage_stats=usage_stats,
        total_reservations=total_reservations
    )

# ---------------------------
# Maintenance
# ---------------------------
@bp.route('/maintenance')
def maintenance_logs():
    response = db.get('MaintenanceLogs', {'Items': []})
    logs = response.get('Items', [])
    return render_template("admin_maintenance.html", logs=logs)

@bp.route('/maintenance/add', methods=['POST'])
def add_maintenance():
    data = request.form
    equipment_id = data.get('equipment_id')
    issue = data.get('issue_description')
    admin_id = "system"  # Replace with session user ID if using auth

    if not equipment_id or not issue:
        flash("Please fill in all fields", "warning")
        return redirect(url_for('admin.maintenance_logs'))

    record = {
        "maintenance_id": str(uuid.uuid4()),
        "equipment_id": equipment_id,
        "issue_description": issue,
        "status": "Open",
        "date_reported": datetime.utcnow().isoformat(),
        "admin_id": admin_id
    }

    db['MaintenanceLogs'].put_item(Item=record)
    flash("Issue logged successfully", "success")
    return redirect(url_for('admin.maintenance_logs'))

# ---------------------------
# Report Export
# ---------------------------
@bp.route('/reports')
def reports():
    return render_template("admin_reports.html")

@bp.route('/reports/export', methods=['POST'])
def export_report():
    report_type = request.form.get('report_type')
    format_type = request.form.get('format', 'pdf')

    table_map = {
        'reservations': ('Reservations', ['reservation_id', 'user_id', 'equipment_id', 'time_slot', 'timestamp']),
        'workouts': ('Workouts', ['workout_id', 'user_id', 'exercise', 'duration', 'timestamp']),
        'maintenance': ('MaintenanceLogs', ['maintenance_id', 'equipment_id', 'issue_description', 'status', 'date_reported']),
    }

    if report_type not in table_map:
        flash("Invalid report type selected", "danger")
        return redirect(url_for('admin.reports'))

    table_name, headers = table_map[report_type]
    items = db[table_name].scan().get('Items', [])

    filename = f"{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if format_type == 'excel':
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for item in items:
            ws.append([item.get(h, '') for h in headers])
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(output, download_name=f"{filename}.xlsx", as_attachment=True)

    elif format_type == 'pdf':
        # For simplicity, we create CSV format with .pdf extension (simulate PDF export)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for item in items:
            writer.writerow([item.get(h, '') for h in headers])
        output.seek(0)
        return send_file(io.BytesIO(output.read().encode()), download_name=f"{filename}.pdf", as_attachment=True)

    else:
        flash("Unsupported format", "danger")
        return redirect(url_for('admin.reports'))

# ---------------------------
# Role Management
# ---------------------------
@bp.route('/users')
def user_roles():
    users = db['Users'].scan().get('Items', [])
    return render_template("admin_users.html", users=users)

@bp.route('/users/role', methods=['POST'])
def update_role():
    user_id = request.form.get('user_id')
    new_role = request.form.get('new_role')

    if user_id and new_role:
        db['Users'].update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET #r = :role",
            ExpressionAttributeNames={"#r": "role"},
            ExpressionAttributeValues={":role": new_role}
        )
        flash("User role updated successfully", "success")
    else:
        flash("Missing user ID or role", "warning")

    return redirect(url_for('admin.user_roles'))
