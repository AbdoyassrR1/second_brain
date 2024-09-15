#!/usr/bin/python3
from flask import Blueprint, abort, request, jsonify
from flask_login import current_user, login_required
from app.models.finance import Transaction, TransactionType, TransactionSubCategory
from app.app import db

finances = Blueprint("finances", __name__)


@finances.route("/", methods=["GET"])
@login_required
def get_transactions():
    """ get all transaction for the logged in user """
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # handle query parameters 
    type = request.args.get("type", "")

    if type:
        try:
            type = TransactionType[type.upper()]
            query = query.filter_by(type=type)
        except KeyError:
            abort(400, description="invalid type")

    query = query.order_by(Transaction.created_at.desc())
    transactions = [trans.to_dict() for trans in query.all()]

    return jsonify(transactions)


@finances.route("/add_transaction", methods=["POST"])
@login_required
def add_transaction():
    """ add new transaction for the logged in user """
    data = request.form

    # Check required fields
    required_fields = ["title", "type", "amount"]
    for field in required_fields:
        if field not in data:
            abort(400, description=f"Missing {field}")

    # Validate and convert enum fields
    try:
        type = TransactionType[data["type"].upper()]
        sub_category = data.get("sub_category", None)
        if sub_category:
            sub_category = TransactionSubCategory[sub_category.upper()]
    except KeyError as e:
        error = str(e).split("\'")[1]
        abort(400, description=f"Invalid ENUM value for {error}")

    # Validate and convert amount field
    try:
        amount = float(data["amount"])
        if amount <= 0:
            abort(400, description="Amount must be a positive number")
    except ValueError:
        abort(400, description="Invalid value for amount, must be a number")

    # create new transaction
    new_transaction = Transaction(
        title=data["title"],
        type=type,
        sub_category=sub_category,
        amount=float(data["amount"]),
        description=data.get("description", "")
    )
    new_transaction.user_id = current_user.id

    # add new_transaction to the database
    db.session.add(new_transaction)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Transaction Created Successfully",
        "Transaction": new_transaction.to_dict()
    }), 201
