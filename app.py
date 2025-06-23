from flask import Flask, render_template, request, redirect, flash, url_for
from routes import auth, member, trainer, admin
from flask_login import LoginManager, current_user
from models import user  # Replace with your actual User model class (e.g., User)

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # 🔐 Replace with a secure key in production

# ---------------------------
# Flask-Login Setup
# ---------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Blueprint endpoint for login

@login_manager.user_loader
def load_user(user_id):
    return user.query.get(int(user_id))  # Adjust based on your ORM (e.g., SQLAlchemy)

# ---------------------------
# Register Blueprints
# ---------------------------
app.register_blueprint(auth.bp, url_prefix='/auth')
app.register_blueprint(member.bp, url_prefix='/member')
app.register_blueprint(trainer.bp, url_prefix='/trainer')
app.register_blueprint(admin.bp, url_prefix='/admin')

# ---------------------------
# Landing Page (Home)
# ---------------------------
@app.route('/')
def landing():
    return render_template('index.html', current_user=current_user)

# ---------------------------
# Contact Form Handling
# ---------------------------
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # TODO: Save this info in DB or send via email/SNS
        print(f"[CONTACT FORM] Name: {name}, Email: {email}, Message: {message}")
        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('landing'))
    else:
        # Prevent GET access to /contact, redirect to home
        return redirect(url_for('landing'))

# ---------------------------
# Dashboard Page (Authenticated Users)
# ---------------------------
@app.route('/dashboard')
def dashboard():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html', current_user=current_user)

# ---------------------------
# Main Entry Point
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)
