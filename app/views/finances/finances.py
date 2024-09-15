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


@finances.route("/update_transaction/<transaction_id>", methods=["PATCH"])
@login_required
def update_transaction(transaction_id):
    """ update an existing transaction for the logged in user """
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    if not transaction:
        abort(404, description="Transaction Not Found Or Not Owned By The Current User")

    data = request.form
    # Allowed fields to update
    allowed_fields = ["title", "description", "type", "amount", "sub_category"]
    is_updated = False

    # Validate and update the fields
    for key, value in data.items():
        if key in allowed_fields:

            if key == "title" and value:
                transaction.title = value
                is_updated = True

            elif key == "description" and value:
                transaction.description = value
                is_updated = True

            elif key == "type" and value:
                try:
                    transaction.type = TransactionType[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid type value")

            elif key == "sub_category" and value:
                try:
                    transaction.sub_category = TransactionSubCategory[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid sub_category value")
            
            elif key == "amount" and value:
                try:
                    value = float(value)
                    if value <= 0:
                        abort(400, description="Amount must be a positive number")
                    transaction.amount = value
                    is_updated = True
                except ValueError:
                    abort(400, description="Invalid value for amount, must be a number")

    # If no changes were made, return an error
    if not is_updated:
        abort(400, description="No valid fields to update or no changes made")

    # Commit the changes to the database
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Transaction Updated Successfully",
        "Transaction": transaction.to_dict()
    }), 200


@finances.route("/delete_transaction/<transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    """ delete transaction for the logged in user """
    # Fetch the Transaction by id and make sure the user is the owner
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first()
    if not transaction:
        abort(404, description="Transaction not found or not owned by the current user")
    db.session.delete(transaction)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Transaction deleted successfully"
    }), 200
