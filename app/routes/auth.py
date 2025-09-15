from flask import Blueprint, render_template, request, redirect, session, flash
from app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils import admin_required, logger
from app.models import db,Contact,Booking
from flask import abort,url_for


auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        try:
            email = request.form["email"].strip()
            password = request.form["password"].strip()

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, password):
                session["user_id"] = user.id
                session["user_email"] = user.email
                flash("Login successful", "success")
                return redirect("/admin")
            else:
                error = "Invalid email or password"

        except Exception as e:
            logger.error(f"Login error: {e}")
            error = "An error occurred during login. Please try again."

    return render_template("login.html", error=error)

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/login")

@auth_bp.route("/update_password", methods=["GET", "POST"])
def update_password():
    error = None
    success = None

    if request.method == "POST":
        try:
            email = request.form["email"].strip()
            current_password = request.form["current_password"].strip()
            new_password = request.form["new_password"].strip()
            confirm_password = request.form["confirm_password"].strip()

            user = User.query.filter_by(email=email).first()

            if not user:
                error = "Email not found."
            elif not check_password_hash(user.password, current_password):
                error = "Current password is incorrect."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            else:
                user.password = generate_password_hash(new_password)
                db.session.commit()
                success = "Password updated successfully"
                flash(success, "success")
                return redirect("/login")

        except Exception as e:
            logger.error(f"Password update error: {e}")
            error = "An error occurred while updating your password. Please try again."

    return render_template("update_password.html", error=error, success=success)

#DELETE ROUTE
@auth_bp.route('/delete/<string:record_type>/<int:id>', methods=["GET", "POST"])
def delete(record_type, id):
    if record_type == "contact":
        record = Contact.query.get_or_404(id)
    elif record_type == "booking":
        record = Booking.query.get_or_404(id)
    else:
        abort(404)
    if request.method == "POST":
        db.session.delete(record)
        db.session.commit()
        flash(f"{record_type.capitalize()} deleted successfully!", "success")
        return redirect(url_for('auth.admin'))  # Blueprint name . route name
    return render_template("delete_contact.html", record=record, type=record_type)



@auth_bp.route("/admin")
@admin_required
def admin():
    try:
        all_contacts = Contact.query.all()
        all_booking = Booking.query.all()
        return render_template("admin.html", contacts=all_contacts, booking=all_booking)
    except Exception as e:
        logger.error(f"Admin page error: {e}")
        flash("An error occurred while loading the admin page.", "danger")
        return redirect("/")
