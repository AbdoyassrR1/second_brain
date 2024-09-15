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
