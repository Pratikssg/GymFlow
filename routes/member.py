# routes/member.py

from flask import Blueprint, request, session, jsonify, render_template, redirect, url_for, flash
from services.dynamo_db import db
from services.sns_notifier import notify
from boto3.dynamodb.conditions import Attr
import uuid
from datetime import datetime

bp = Blueprint('member', __name__, url_prefix='/member')


# ---------------------------
# Member Dashboard
# ---------------------------
@bp.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user or user.get('role') != 'member':
        flash("Access denied. Please log in as a member.", "warning")
        return redirect(url_for('auth.login'))

    return render_template('member_dashboard.html', user=user)


# ---------------------------
# Reserve Equipment Endpoint
# ---------------------------
@bp.route('/reserve', methods=['POST'])
def reserve_equipment():
    user = session.get('user')
    if not user:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        equipment_id = data.get('equipment_id')
        time_slot = data.get('time_slot')

        if not equipment_id or not time_slot:
            return jsonify({"message": "Missing equipment or time slot"}), 400

        # ✅ Efficient fetch of equipment using get_item (assuming equipment_id is the primary key)
        equipment_response = db['Equipment'].get_item(Key={'equipment_id': equipment_id})
        equipment_name = equipment_response.get('Item', {}).get('name', 'Unknown Equipment')

        # Save reservation
        reservation = {
            'reservation_id': str(uuid.uuid4()),
            'user_id': user['user_id'],
            'equipment_id': equipment_id,
            'time_slot': time_slot,
            'timestamp': datetime.utcnow().isoformat()
        }

        db['Reservations'].put_item(Item=reservation)

        # Notify via email
        message = (
            f"Hello {user['name']},\n\n"
            f"✅ Your equipment has been reserved.\n"
            f"🏋️ Equipment: {equipment_name}\n"
            f"⏰ Time Slot: {time_slot}\n"
            f"📅 Date: {datetime.utcnow().date()}\n\n"
            "Thank you for using GymFlow!"
        )
        notify('reservation', message, subject='GymFlow: Reservation Confirmation')

        return jsonify({"message": "Reservation Confirmed"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ---------------------------
# Workout Tracking Endpoint
# ---------------------------
@bp.route('/track', methods=['POST'])
def track_workout():
    user = session.get('user')
    if not user:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        exercises = data.get('exercises')
        notes = data.get('notes', '')

        if not exercises:
            return jsonify({"message": "Exercises field is required"}), 400

        workout = {
            'workout_id': str(uuid.uuid4()),
            'user_id': user['user_id'],
            'exercises': exercises,
            'date': datetime.utcnow().date().isoformat(),
            'notes': notes
        }

        db['Workouts'].put_item(Item=workout)
        return jsonify({"message": "Workout Logged"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500
