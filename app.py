from flask import Flask, render_template, request, redirect, session, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from requests.exceptions import ConnectionError, RequestException
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import time
import razorpay
import razorpay.errors  # Important for exception handling
import logging
import requests
import socket
from functools import wraps
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("KEY_ID from environment:", os.environ.get("KEY_ID"))
print("KEY_SECRET from environment:", os.environ.get("KEY_SECRET"))

# Initialize Razorpay client with retry configuration
try:
    key_id = os.environ.get("KEY_ID")
    key_secret = os.environ.get("KEY_SECRET")
    
    if not key_id or not key_secret:
        logger.error("Razorpay credentials not found in environment variables")
        # Create a dummy client to prevent crashes (for development only)
        class DummyRazorpayClient:
            class DummyOrder:
                def create(self, data):
                    logger.warning("Using dummy Razorpay client - payment functionality disabled")
                    return {"id": "dummy_order_id", "amount": data["amount"], "currency": data["currency"]}
            
            class DummyUtility:
                def verify_payment_signature(self, params):
                    logger.warning("Signature verification skipped - using dummy client")

            def __init__(self):
                self.order = self.DummyOrder()
                self.utility = self.DummyUtility()
        
        razorpay_client = DummyRazorpayClient()
    else:
        # Create session with retry configuration
        session = requests.Session()
        for adapter in session.adapters.values():
            adapter.max_retries = 3
        
        razorpay_client = razorpay.Client(auth=(key_id, key_secret))
        # Use our custom session with retry settings
        razorpay_client.session = session
        
except Exception as e:
    logger.error(f"Failed to initialize Razorpay client: {e}")
    raise

# Create an instance of the Flask class
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "fallback_secret"

# Database URL fix for PostgreSQL
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
print("Active DB URL:", db_url)

# Replace these with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Connection pool and pre-ping
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}

db = SQLAlchemy(app)

# Define models
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100))
    Email = db.Column(db.String(120))
    Number = db.Column(db.String(20))
    Message = db.Column(db.Text)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hashed Password

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    paid = db.Column(db.Boolean, default=False)
    razorpay_order_id = db.Column(db.String(100))  # Store Razorpay order ID

# Create database tables
with app.app_context():
    db.create_all()

# Helper function for admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/plans")
def plan():
    return render_template("plan.html")

@app.route("/book")
def book():
    return render_template("book.html")

@app.route("/payment_checkout", methods=["GET", "POST"])
def submit_booking():
    if request.method == "POST":
        try:
            name = request.form["name"]
            email = request.form["email"]
            phone = request.form["phone"]
            plan = request.form["plan"]
            start_date = request.form["start_date"]

            # Save to database
            new_booking = Booking(
                name=name,
                email=email,
                phone=phone,
                plan=plan,
                start_date=start_date
            )
            db.session.add(new_booking)
            db.session.commit()

            # Determine amount in paise
            plan_amount_map = {
                "सिल्वर प्लान ₹400/महीना": 40000,
                "गोल्ड प्लान ₹1000/महीना": 100000,
                "सिल्वर वार्षिक ₹4000/वर्ष": 400000,
                "गोल्ड वार्षिक ₹10,000/वर्ष": 1000000
            }
            amount = plan_amount_map.get(plan, 0)

            if amount == 0:
                flash("Invalid plan selected. Please try again.", "danger")
                return render_template("book.html")

            # Add retry logic for connection issues
            max_retries = 3
            razorpay_order = None
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"Attempting to create Razorpay order (attempt {attempt + 1})")
                    razorpay_order = razorpay_client.order.create({
                        "amount": amount,
                        "currency": "INR",
                        "receipt": f"booking_{new_booking.id}",
                        "payment_capture": '1'
                    })
                    logger.info("Razorpay order created successfully")
                    break  # Success, exit the retry loop

                except (ConnectionError, RequestException) as e:
                    logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:  # Last attempt failed
                        flash("Payment gateway is temporarily unavailable. Please try again in a moment.", "danger")
                        # Delete the booking record since payment failed
                        db.session.delete(new_booking)
                        db.session.commit()
                        return render_template("book.html")
                    time.sleep(1)  # Wait before retrying

                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Razorpay BadRequestError: {e}")
                    flash("Invalid request to payment gateway. Please check your details and try again.", "danger")
                    # Delete the booking record
                    db.session.delete(new_booking)
                    db.session.commit()
                    return render_template("book.html")

                except Exception as e:
                    logger.error(f"Unexpected error creating Razorpay order: {e}")
                    flash("An unexpected error occurred. Please try again.", "danger")
                    # Delete the booking record
                    db.session.delete(new_booking)
                    db.session.commit()
                    return render_template("book.html")

            # Update booking with Razorpay order ID
            new_booking.razorpay_order_id = razorpay_order['id']
            db.session.commit()

            # Save order id in session and render checkout template
            session['razorpay_order_id'] = razorpay_order['id']
            return render_template("payment_checkout.html",
                                   razorpay_order_id=razorpay_order['id'],
                                   razorpay_key_id=os.environ.get("KEY_ID"),
                                   amount=amount,
                                   name=name,
                                   email=email,
                                   phone=phone,
                                   booking_id=new_booking.id)

        except Exception as e:
            logger.error(f"Error in submit_booking: {e}")
            flash("An error occurred while processing your request. Please try again.", "danger")
            return render_template("book.html")

    return render_template("book.html")

@app.route("/payment_success", methods=["GET", "POST"])
def payment_success():
    try:
        # Get payment details from request args or form data
        payment_id = request.args.get("razorpay_payment_id") or request.form.get("razorpay_payment_id")
        order_id = request.args.get("razorpay_order_id") or request.form.get("razorpay_order_id")
        signature = request.args.get("razorpay_signature") or request.form.get("razorpay_signature")

        if not payment_id or not order_id or not signature:
            logger.error("Missing payment details in callback")
            abort(400, description="Missing payment details")

        # Verify the payment signature
        try:
            params_dict = {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)
            logger.info("Payment signature verified successfully")
        except razorpay.errors.SignatureVerificationError:
            logger.error("Payment signature verification failed")
            abort(400, description="Payment signature verification failed")

        # Find booking by Razorpay order ID
        booking = Booking.query.filter_by(razorpay_order_id=order_id).first()
        if booking:
            booking.paid = True
            db.session.commit()
            logger.info(f"Booking {booking.id} marked as paid")
        else:
            logger.warning(f"No booking found for order ID: {order_id}")

        return render_template("payment_success.html", 
                               payment_id=payment_id, 
                               booking_id=booking.id if booking else None)

    except Exception as e:
        logger.error(f"Error in payment_success: {e}")
        flash("An error occurred while processing your payment. Please contact support if the amount was deducted.", "danger")
        return redirect("/book")

@app.route("/payment_failure")
def payment_failure():
    order_id = request.args.get("order_id")
    if order_id:
        # Optional: You might want to delete the booking record here
        # or mark it as failed in some way
        logger.info(f"Payment failed for order: {order_id}")
    
    flash("Payment was cancelled or failed. Please try again.", "warning")
    return redirect("/book")

@app.route("/submit", methods=['POST'])
def submit():
    try:
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        message = request.form['message']

        # Save to database
        new_contact = Contact(Name=name, Email=email, Number=number, Message=message)
        db.session.add(new_contact)
        db.session.commit()

        return render_template("submit.html", name=name, email=email, number=number, message=message)
    
    except Exception as e:
        logger.error(f"Error in contact form submission: {e}")
        flash("An error occurred while submitting your message. Please try again.", "danger")
        return redirect("/contact")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        try:
            email = request.form["email"].strip()
            password = request.form["password"].strip()

            user = User.query.filter_by(email=email).first()

            if user and check_password_hash(user.password, password):
                # Login successful
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

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect("/login")

@app.route("/update_password", methods=["GET", "POST"])
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

@app.route("/admin")
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

# Network test endpoint for debugging
@app.route("/network_test")
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

# Health check endpoint
@app.route("/health")
def health_check():
    try:
        # Check database connection
        db.session.execute("SELECT 1")
        db_status = "OK"
    except Exception as e:
        db_status = f"Error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "razorpay_configured": bool(os.environ.get("KEY_ID") and os.environ.get("KEY_SECRET"))
    })

# Run the application if the script is executed directly
if __name__ == "__main__":
    app.run(debug=False)