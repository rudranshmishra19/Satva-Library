from flask import Flask, render_template, request, redirect, session,flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash,generate_password_hash
from dotenv import load_dotenv
import os


load_dotenv () # <- Load variables from .env
# Create an instance of the Flask class
app = Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY")or "fallback_secret"

#Replace these with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI']=os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False

db=SQLAlchemy(app)
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
    with app.app_context():
        db.create_all()
        
    app.run(debug=False)