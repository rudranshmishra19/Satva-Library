from flask import Flask, render_template, request, redirect, session,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash,generate_password_hash
from dotenv import load_dotenv
import os


load_dotenv () # <- Load variables from .env
# Create an instance of the Flask class
app = Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY")or "fallback_secret"

db_url=os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url=db_url.replace("postgres://","postgresql://",1)


#Replace these with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI']=db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False

db=SQLAlchemy(app)
with app.app_context():
    db.create_all()
#Define a model
class Contact(db.Model):
     Id=db.Column(db.Integer,primary_key=True)
     Name=db.Column(db.String(100))
     Email=db.Column(db.String(120))
     Number=db.Column(db.String(20))
     Message=db.Column(db.Text)

#Define User for admin
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    fullname=db.Column(db.String(150),nullable=False)
    email=db.Column(db.String(150),unique=True,nullable=False)
    password=db.Column(db.String(200),nullable=False) #Hashed Password

class Booking(db.Model):
    id= db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    email=db.Column(db.String(120),nullable=False)    
    phone=db.Column(db.String(20),nullable=False)
    plan=db.Column(db.String(50),nullable=False)
    start_date=db.Column(db.String(20),nullable=False)   
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

@app.route("/submit_booking",methods=["GET","POST"])
def submit_booking():
    if request.method =="POST":
        name=request.form["name"]
        email=request.form["email"]
        phone=request.form["phone"]
        plan=request.form["plan"]
        start_date=request.form["start_date"]

    #Save to database
        new_booking=Booking(
          name=name,
          email=email,
          phone=phone,
          plan=plan,
          start_date=start_date
       )
        db.session.add(new_booking)
        db.session.commit()
    
        return render_template(
            "submit_booking.html",
          name=name,
          email=email,
          phone=phone,
          plan=plan,
          start_date=start_date

     )

    return render_template("submit_booking.html")




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

@app.route("/logout",methods=["POST"])
def logout():
    session.pop("user_id",None)
    flash("Logged out successfully","success")
    return redirect("/login")
        


@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/login")
    all_contacts= Contact.query.all()
    return render_template("admin.html",contacts=all_contacts)


# Run the application if the script is executed directly
if __name__ == "__main__":
        
    app.run(debug=False)