from flask import Blueprint, request, redirect, session, render_template, flash, url_for
from services.dynamo_db import db
from services.sns_notifier import subscribe_user_email
from boto3.dynamodb.conditions import Attr
import uuid

bp = Blueprint('auth', __name__, template_folder='../templates')


# ---------------------------
# Signup Page (GET + POST)
# ---------------------------
@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.form
        email = data['email']

        # Check if user already exists
        existing = db['Users'].scan(
            FilterExpression=Attr("email").eq(email)
        )

        if existing['Items']:
            flash("Email already registered. Please use a different one.", "danger")
            return redirect(url_for('auth.signup'))

        user_id = str(uuid.uuid4())
        role = data['role']

        # New user item
        user = {
            'username': email,
            'user_id': user_id,
            'name': data['name'],
            'email': email,
            'password': data['password'],  # ⚠️ In production use hashed passwords!
            'role': role
        }

        # Subscribe to SNS if member
        if role == 'member':
            subscribed = subscribe_user_email(email)
            if subscribed:
                user['sns_subscribed'] = True
                flash("Subscribed to workout reminders via email. Confirm via inbox.", "info")
            else:
                user['sns_subscribed'] = False
                flash("Signup successful, but email subscription to reminders failed.", "warning")

        db['Users'].put_item(Item=user)
        flash("Signup successful! Please log in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


# ---------------------------
# Login Page (GET + POST)
# ---------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        email = data['email']
        password = data['password']

        # Lookup user by email
        response = db['Users'].scan(
            FilterExpression=Attr("email").eq(email)
        )

        if response['Items']:
            user = response['Items'][0]
            if user['password'] == password:
                user.pop('password', None)
                session['user'] = user
                flash("Login successful!", "success")

                # Role-based redirection
                role = user['role']
                if role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif role == 'trainer':
                    return redirect(url_for('trainer.dashboard'))
                elif role == 'member':
                    return redirect(url_for('member.dashboard'))
                else:
                    flash("Unknown user role. Please contact support.", "warning")
                    return redirect(url_for('auth.login'))

        flash("Invalid email or password. Try again.", "danger")
        return redirect(url_for('auth.login'))

    return render_template('login.html')


# ---------------------------
# Logout Route
# ---------------------------
@bp.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
