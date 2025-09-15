from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for, abort
from app.models import Contact, Booking, db
from app.utils import logger
import socket
import requests

misc_bp = Blueprint('misc', __name__)

@misc_bp.route("/network_test")
def network_test():
    results = {}

    # Test DNS resolution
    try:
        razorpay_ip = socket.gethostbyname('api.razorpay.com')
        results['dns'] = f"Success: {razorpay_ip}"
    except socket.gaierror as e:
        results['dns'] = f"Failed: {e}"

    # Test HTTP connection
    try:
        response = requests.get('https://api.razorpay.com', timeout=10)
        results['http'] = f"Success: Status {response.status_code}"
    except requests.exceptions.RequestException as e:
        results['http'] = f"Failed: {e}"

    # Test Razorpay API connectivity (without auth)
    try:
        test_response = requests.get('https://api.razorpay.com/v1/orders', timeout=10)
        results['razorpay'] = f"Connectivity: Status {test_response.status_code}"
    except requests.exceptions.RequestException as e:
        results['razorpay'] = f"Failed: {e}"

    return jsonify(results)

@misc_bp.route("/health")
def health_check():
    try:
        db.session.execute("SELECT 1")
        db_status = "OK"
    except Exception as e:
        db_status = f"Error: {str(e)}"

    from os import environ
    razorpay_configured = bool(environ.get("KEY_ID") and environ.get("KEY_SECRET"))

    return jsonify({
        "status": "healthy",
        "database": db_status,
        "razorpay_configured": razorpay_configured
    })

@misc_bp.route('/delete/<string:record_type>/<int:id>', methods=["GET", "POST"])
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
        return redirect(url_for('auth.admin'))  # Assuming 'auth.admin' is your admin page blueprint route

    return render_template("delete_contact.html", record=record, type=record_type)
