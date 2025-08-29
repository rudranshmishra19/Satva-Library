from flask import Flask, render_template, request, redirect, session,flash,abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
from dotenv import load_dotenv
import os
import razorpay

load_dotenv () # <- Load variables from .env
razorpay_client=razorpay.Client(auth=(os.environ.get("KEY_ID"),os.environ.get("KEY_SECRET")))



# Create an instance of the Flask class
#Initialize FlaskS
app = Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY")or "fallback_secret"

#Database URL fix for postgress
db_url=os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url=db_url.replace("postgres://","postgresql://",1)
print("Active DB URL:",db_url)    

#Replace these with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI']=db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False

db=SQLAlchemy(app)
with app.app_context():
    db.create_all()
#Define a model
class Contact(db.Model):
     id=db.Column(db.Integer,primary_key=True)
     Name=db.Column(db.String(100))
     Email=db.Column(db.String(120))
     Number=db.Column(db.String(20))
     Message=db.Column(db.Text)

#Define User for admin
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(150),unique=True,nullable=False)
    password=db.Column(db.String(200),nullable=False) #Hashed Password


class Booking(db.Model):
    id= db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(120),nullable=False)    
    phone=db.Column(db.String(20),nullable=False)
    plan=db.Column(db.String(50),nullable=False)
    start_date=db.Column(db.String(20),nullable=False)   
    paid=db.Column(db.Boolean,default=False) #New column for payment status 
# Define a route for the root URL ("/")
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
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        plan = request.form["plan"]
        start_date = request.form["start_date"]

        # Step 1: Save to database
        new_booking = Booking(
            name=name,
            email=email,
            phone=phone,
            plan=plan,
            start_date=start_date
        )
        db.session.add(new_booking)
        db.session.commit()

        # Step 2: Determine amount in paise (smallest INR unit)
        plan_amount_map = {
            "सिल्वर प्लान ₹400/महीना": 40000,
            "गोल्ड प्लान ₹1000/महीना": 100000,
            "सिल्वर वार्षिक ₹4000/वर्ष": 400000,
            "गोल्ड वार्षिक ₹10,000/वर्ष": 1000000
        } 
        amount = plan_amount_map.get(plan, 0)

        # Create Razorpay order
        try:
            razorpay_order = razorpay_client.order.create({
                "amount": amount,
                "currency": "INR",
                "receipt": f"booking_{new_booking.id}",
                "payment_capture": '1'  # automatic capture
            })
        except razorpay.errors.BadRequestError:
            flash("Payment gateway authentication failed.", "danger")
            return render_template("book.html")

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

    # For GET requests show booking form
    return render_template("book.html")


@app.route("/payment_success",methods=["GET","POST"])
def payment_success():
    #Get payment details from request args or from data
    payment_id=request.args.get("payment_id") or request.form.get("payment_id")
    order_id=request.args.get("order_id") or request.form.get("order_id")
    signature=request.args.get("signature") or request.form.get("signature")


    if not payment_id or not order_id or not signature: 
        abort(400, description="Missing payment details")
    
    # Verify the payment signature to ensure it's valid and from razorpay 
    try:
        params_dict={

            "razorpay_order_id":order_id,
            "razorpay_payment_id":payment_id,
            "razorpay_signature":signature
        }
         # This method raises an exception if verification fails
        razorpay_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        abort(400,description="Payment signature verfication failed")

    booking_id=None
    if order_id:
       razorpay_order=razorpay_client.order.fetch(order_id)
       receipt=razorpay_order.get("receipt")

       if receipt and receipt.startswith("booking_"):
           try:
               booking_id=int(receipt.split("_")[1])
           except (IndexError,ValueError):
               booking_id=None
    if booking_id:
        booking=Booking.query.get(booking_id)
        if booking:
            booking.paid=True
            db.session.commit()
    
    return render_template("payment_success.html",payment_id=payment_id,booking_id=booking_id)
   
       



@app.route("/submit",methods=['POST'])
def submit():
    name= request.form['name']
    email=request.form['email']
    number=request.form['number']
    message=request.form['message']



    #save to database
    new_contact=Contact(Name=name,Email=email,Number=number, Message=message)
    db.session.add(new_contact)
    db.session.commit()
       
    return render_template("submit.html",name=name,email=email,number=number,message=message)

@app.route("/login",methods=["GET","POST"])
def login():
    error=None
    if request.method=="POST":
        email=request.form["email"].strip()
        password=request.form["password"].strip()

        user=User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password,password):
        # login sucessful    
            session["user_id"]=user.id
            flash("Login sucessful","success")
            return redirect("/admin")
        else:
            error="Invalid email or password"
    return render_template("login.html",error=error)
 
@app.route("/logout")
def logout():
    session.pop("user_id",None)
    flash("Logged out successfully","success")
    return redirect("/login")


@app.route("/update_password", methods=["GET", "POST"])
def update_password():
    error = None
    success = None
    
    if request.method == "POST":
        email = request.form["email"].strip()
        current_password = request.form["current_password"].strip()

        new_password = request.form["new_password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        user = User.query.filter_by(email=email).first()

        if not user:
            error = "Email not found."
        elif not check_password_hash(user.password,current_password):
            error = "Current password is incorrect."
        elif new_password != confirm_password:
            error = "New passwords do not match."
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            success="Password updated successfully"
            return redirect("/login")

    # For GET requests or if there was an error, render the update form with messages
    return render_template("update_password.html", error=error, success=success)

        
@app.route("/admin")
def admin():
    print("Session date:",session) #print session contents to console/log
    if "user_id" not in session:
        return redirect("/login")
    all_contacts= Contact.query.all()
    all_booking=Booking.query.all()
    return render_template("admin.html",contacts=all_contacts,booking=all_booking)


# Run the application if the script is executed directly
if __name__ == "__main__":   
        app.run(debug=True)