from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
@main_bp.route("/home")
def home():
    return render_template("home.html")

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/gallery")
def gallery():
    return render_template("gallery.html")

@main_bp.route("/contact")
def contact():
    return render_template("contact.html")

@main_bp.route("/plans")
def plan():
    return render_template("plan.html")

@main_bp.route("/book")
def book():
    return render_template("book.html")
