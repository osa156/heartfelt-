from flask import Blueprint, request, jsonify
import jwt
import requests
from functools import wraps
from datetime import datetime, timedelta
from src.models.user import db, User

subscription_bp = Blueprint("subscription", __name__)

# Paystack configuration
PAYSTACK_SECRET_KEY = "sk_live_86fcee14d403288d8fd5c991850896d1b68e225a"
PAYSTACK_PUBLIC_KEY = "pk_live_669ad09183f1ded9229c99297d5d67f539e3c828"

def get_secret_key():
    return "asdf#FGSgvasgf$5$WGT"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"message": "Token is missing"}), 401
        try:
            token = token.split(" ")[1]
            data = jwt.decode(token, get_secret_key(), algorithms=["HS256"])
            current_user = User.query.get(data["user_id"])
            if not current_user:
                return jsonify({"message": "User not found"}), 401
        except:
            return jsonify({"message": "Token is invalid"}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@subscription_bp.route("/subscription/plans", methods=["GET"])
def get_subscription_plans():
    plans = {
        "male": [
            {"id": "male_unlimited", "name": "Unlimited Swipes", "price": 299900, "description": "Unlimited right swipes for 30 days"}
        ],
        "female": [
            {"id": "silver", "name": "Silver", "price": 150900, "description": "Access to men earning ₦300k+/month"},
            {"id": "gold", "name": "Gold", "price": 250900, "description": "Access to men earning ₦600k+/month + Priority matching"},
            {"id": "platinum", "name": "Platinum", "price": 350900, "description": "Access to men earning ₦900k+/month + Advanced filters"},
            {"id": "diamond", "name": "Diamond", "price": 500900, "description": "Access to men earning ₦1.2M+/month + VIP features"}
        ]
    }
    return jsonify(plans)

@subscription_bp.route("/subscription/verify", methods=["POST"])
@token_required
def verify_subscription(current_user):
    data = request.get_json()
    reference = data.get("reference")
    plan_id = data.get("plan_id")
    
    # Verify payment with Paystack
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers
    )
    
    if response.status_code == 200:
        payment_data = response.json()
        if payment_data["data"]["status"] == "success":
            # Update user subscription
            if current_user.gender == "male" and plan_id == "male_unlimited":
                current_user.swipe_count = 0  # Reset swipe count
                current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            elif current_user.gender == "female":
                current_user.subscription = plan_id
                current_user.subscription_expires = datetime.utcnow() + timedelta(days=30)
            
            db.session.commit()
            
            return jsonify({
                "message": "Subscription updated successfully",
                "subscription": current_user.subscription,
                "swipe_count": current_user.swipe_count
            })
    
    return jsonify({"message": "Payment verification failed"}), 400

