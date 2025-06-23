from flask import Blueprint, request, session, render_template, redirect, url_for, flash
from services.dynamo_db import db
from boto3.dynamodb.conditions import Attr
import uuid

bp = Blueprint('trainer', __name__, url_prefix='/trainer')


# ---------------------------
# Dashboard Page (Trainer Home)
# ---------------------------
@bp.route('/dashboard')
def dashboard():
    if 'user' not in session or session['user']['role'] != 'trainer':
        flash("Access denied: Trainer login required", "danger")
        return redirect(url_for('auth.login'))

    # Fetch all members
    members_response = db['Users'].scan(
        FilterExpression=Attr("role").eq("member")
    )
    members = members_response.get('Items', [])

    # Fetch all equipment
    equipment_response = db['Equipment'].scan()
    equipment = equipment_response.get('Items', [])

    # Fetch assigned workouts
    workouts_response = db['Workouts'].scan()
    workouts = workouts_response.get('Items', [])

    # Build member and equipment maps
    member_map = {m['user_id']: m for m in members}
    equipment_map = {e['equipment_id']: e for e in equipment}

    assigned = []
    for w in workouts:
        uid = w.get('user_id')
        eid = w.get('equipment_id')
        assigned.append({
            'user_id': uid,
            'name': member_map.get(uid, {}).get('name'),
            'email': member_map.get(uid, {}).get('email'),
            'equipment_id': eid,
            'equipment_name': equipment_map.get(eid, {}).get('name', 'N/A'),
            'exercises': w.get('exercises'),
            'assigned_by': w.get('assigned_by')
        })

    return render_template('trainer_dashboard.html',
                           trainer=session['user'],
                           members=members,
                           equipment=equipment,
                           assigned=assigned)


# ---------------------------
# Assign Workout to Member
# ---------------------------
@bp.route('/assign', methods=['POST'])
def assign_workout():
    if 'user' not in session or session['user']['role'] != 'trainer':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    data = request.form

    user_id = data.get('user_id')
    equipment_id = data.get('equipment_id')
    exercises = data.get('exercises')

    if not user_id or not equipment_id or not exercises:
        flash("All fields are required.", "warning")
        return redirect(url_for('trainer.dashboard'))

    workout = {
        'workout_id': str(uuid.uuid4()),
        'user_id': user_id,
        'equipment_id': equipment_id,
        'exercises': exercises,
        'assigned_by': session['user']['user_id']
    }

    db['Workouts'].put_item(Item=workout)
    flash("Workout assigned successfully.", "success")
    return redirect(url_for('trainer.dashboard'))


# ---------------------------
# View Member Workout History
# ---------------------------
@bp.route('/member-history/<user_id>')
def member_history(user_id):
    if 'user' not in session or session['user']['role'] != 'trainer':
        flash("Access denied.", "danger")
        return redirect(url_for('auth.login'))

    # Fetch member info
    user_info = db['Users'].scan(
        FilterExpression=Attr("user_id").eq(user_id)
    ).get('Items', [{}])[0]

    # Fetch workouts
    workouts = db['Workouts'].scan(
        FilterExpression=Attr("user_id").eq(user_id)
    ).get('Items', [])

    return render_template("trainer_member_history.html", member=user_info, workouts=workouts)


# ---------------------------
# Send Message to Member
# ---------------------------
@bp.route('/message/send', methods=['POST'])
def send_message():
    if 'user' not in session or session['user']['role'] != 'trainer':
        flash("Unauthorized access", "danger")
        return redirect(url_for('auth.login'))

    data = request.form
    receiver_id = data.get('user_id')
    message = data.get('message')

    if not receiver_id or not message:
        flash("All fields are required.", "warning")
        return redirect(url_for('trainer.dashboard'))

    msg = {
        'message_id': str(uuid.uuid4()),
        'sender_id': session['user']['user_id'],
        'receiver_id': receiver_id,
        'message': message,
        'timestamp': str(uuid.uuid1())
    }

    db['TrainerMessages'].put_item(Item=msg)
    flash("Message sent successfully.", "success")
    return redirect(url_for('trainer.dashboard'))
