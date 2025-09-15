from flask import Blueprint, render_template, request, session, flash, redirect
from app.models import Booking, db
from app.razorpay_client import razorpay_client
from requests.exceptions import ConnectionError, RequestException
import time
import logging
import razorpay.errors


booking_bp = Blueprint('booking', __name__)
logger = logging.getLogger(__name__)

@booking_bp.route("/payment_checkout", methods=["GET", "POST"])
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
                    break

                except (ConnectionError, RequestException) as e:
                    logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        flash("Payment gateway is temporarily unavailable. Please try again in a moment.", "danger")
                        db.session.delete(new_booking)
                        db.session.commit()
                        return render_template("book.html")
                    time.sleep(1)

                except razorpay.errors.BadRequestError as e:
                    logger.error(f"Razorpay BadRequestError: {e}")
                    flash("Invalid request to payment gateway. Please check your details and try again.", "danger")
                    db.session.delete(new_booking)
                    db.session.commit()
                    return render_template("book.html")

                except Exception as e:
                    logger.error(f"Unexpected error creating Razorpay order: {e}")
                    flash("An unexpected error occurred. Please try again.", "danger")
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
                                   razorpay_key_id=None,  # use os.environ.get("KEY_ID") in config if needed
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

@booking_bp.route("/payment_success", methods=["GET", "POST"])
def payment_success():
    try:
        payment_id = request.args.get("razorpay_payment_id") or request.form.get("razorpay_payment_id")
        order_id = request.args.get("razorpay_order_id") or request.form.get("razorpay_order_id")
        signature = request.args.get("razorpay_signature") or request.form.get("razorpay_signature")

        if not payment_id or not order_id or not signature:
            logger.error("Missing payment details in callback")
            return "Missing payment details", 400

        params_dict = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)
        logger.info("Payment signature verified successfully")

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

@booking_bp.route("/payment_failure")
def payment_failure():
    order_id = request.args.get("order_id")
    if order_id:
        logger.info(f"Payment failed for order: {order_id}")
    flash("Payment was cancelled or failed. Please try again.", "warning")
    return redirect("/book")
