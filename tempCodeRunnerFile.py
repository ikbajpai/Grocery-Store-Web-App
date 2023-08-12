# -----------------------------------IMPORTING LIBARIES----------------------------------------------------
from flask import Flask, render_template, request, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api, Resource, reqparse, fields
from werkzeug.exceptions import HTTPException
import json
import sqlite3
from datetime import datetime

# ---------------------------------------SETTING APP------------------------------------------------------

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
db = SQLAlchemy()
db.init_app(app)
api = Api(app)
app.app_context().push()

app.secret_key = 'mykey'

# -----------------------------------------------------------CLASSES---------------------------------------------------------------------------------------------------


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    account_type = db.Column(db.Integer, nullable=False, default=0)


class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)


class Product(db.Model):
    __tablename__ = 'products'
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True, default=None)
    category_id = db.Column(db.Integer, db.ForeignKey(
        "categories.category_id"), nullable=False)


class Order(db.Model):
    __tablename__ = 'orders'
    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey(
        "users.user_id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey(
        "products.product_id"), nullable=False)


db.create_all()

# -----------------------------------------------------USERS----------------------------------------------------------------------------

# CREATE : register if user doesn't exist and redirect to search_products.html


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")  # register
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        c_password = request.form['confirm_password']
        user_exists = db.session.query(User).filter_by(
            username=username).first() is not None
        if user_exists:  # check if user exists
            return render_template("message.html", message='User exists. Please Sign in.', type=-1)
        else:  # register non-existing user
            if password == c_password:
                user = User(name=name, username=username,
                            password=password, account_type=0)
                db.session.add(user)
                db.session.commit()
                session['uid'] = user.user_id
                return redirect(url_for('search_products'))
            else:
                return render_template("message.html", message='Invalid Credentials..!!, Username/Password entered wrong..!!', type=-1)

# CREATE : login and redirect to show_products.html


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.session.query(User).filter_by(username=username).first()
        if user and user.password == password:
            session['uid'] = user.user_id
            if user.account_type == 0:  # user:0 , manager:1 , admin:2
                return redirect(url_for('search_products'))
            else:
                return redirect(url_for('showcategory'))
        else:
            return render_template('message.html', message='Invalid Credentials..!!, Username/Password entered wrong..!!', type=-1)

# ----------------------------------------------MANAGERS--------------------------------------------------------------------------------

# CREATE : admin will create manager


@app.route('/create_manager', methods=['GET', 'POST'])
def create_manager():
    if request.method == "GET":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        if user.account_type == 2:
            print(user.account_type)
            return render_template("create_manager.html")
        else:
            return render_template('message.html', message='You are not authorized to visit this webpage.')
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        c_password = request.form['confirm_password']
        user_exists = db.session.query(User).filter_by(
            username=username).first() is not None
        if user_exists:  # check if user exists
            return render_template("message.html", message='Username taken. Please try another username.')
        else:  # register non-existing user
            if password == c_password:
                user = User(name=name, username=username,
                            password=password, account_type=1)
                db.session.add(user)
                db.session.commit()
                return render_template("message.html", message='Manager\'s account created successfully')
            else:
                return render_template("message.html", message='Password mismatched..!! Kindly re-enter..!! ')

# READ : show managers by name for admin


@app.route("/show_managers")
def show_managers():
    if request.method == "GET":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        if user.account_type == 2:
            managers = db.session.query(User).filter_by(account_type=1)
            return render_template("show_managers.html",  managers=managers)
        else:
            return render_template('message.html', message='Kindly visit main login page..!!')

# DELETE : delete manager

# confirming category deletion


@app.route('/confirm_delete_manager/<int:manager_id>', methods=['GET'])
def confirm_delete_manager(manager_id):
    user = db.session.query(User).filter_by(user_id=session['uid']).first()
    if user.account_type == 2:
        return render_template('confirm_delete_manager.html', manager_id=manager_id)
    else:
        return render_template('message.html', message='Kindly visit main login page..!!')

# deleting category


@app.route('/delete_manager', methods=["POST"])
def delete_manager():
    if request.method == 'POST':
        manager_id = request.form['manager_id']
        db.session.query(User).filter_by(user_id=manager_id).delete()
        db.session.commit()
        return redirect(url_for('show_managers'))

# ------------------------------------------------ CATEGORY -----------------------------------------------------------------------

# READ


@app.route("/showcategory")
def showcategory():
    if request.method == "GET":
        if session.get('uid') and session['uid']:
            user = db.session.query(User).filter_by(
                user_id=session['uid']).first()
            categories = Category.query.all()
            if user.account_type == 1 or user.account_type == 2:
                return render_template("showcategory.html", categories=categories, type=user.account_type)
            else:
                return render_template('message.html', message='You are not authorized to visit this webpage.')

# CREATE


@app.route('/create_category', methods=['GET', 'POST'])
def create_category():
    if request.method == "GET":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        if user.account_type == 1 or user.account_type == 2:
            return render_template("create_category.html", type=user.account_type)
        else:
            return render_template('message.html', message='You are not authorized to visit this webpage.')
    if request.method == 'POST':
        name = request.form['name']
        category_exists = db.session.query(
            Category).filter_by(name=name).first() is not None
        if category_exists:
            return render_template('message.html', message='Category already exists.')
        else:
            category = Category(name=name)
            db.session.add(category)
            db.session.commit()
            return render_template('message.html', message='Category created successfully.')

# UPDATE


@app.route("/update_category", methods=["GET", "POST"])
def update_category():
    if request.method == "POST":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        page = request.form['page']
        category_id = request.form['category_id']
        if page == "update":
            category_name = request.form['name']
            category = db.session.query(Category).filter_by(
                category_id=category_id).first()
            category.name = category_name
            db.session.commit()
            return redirect(url_for('showcategory'))
        else:
            return render_template('update_category.html', category_id=category_id, type=user.account_type)
    else:
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        if user.account_type == 1 or user.account_type == 2:
            return redirect(url_for('showcategory'))
        else:
            return render_template('message.html', message='You are not authorized to visit this webpage.')

# confirming category deletion


@app.route('/confirm_delete_category/<int:category_id>', methods=['GET'])
def confirm_delete_category(category_id):
    user = db.session.query(User).filter_by(user_id=session['uid']).first()
    if user.account_type == 1 or user.account_type == 2:
        return render_template('confirm_delete_category.html', category_id=category_id, type=user.account_type)
    else:
        return render_template('message.html', message='You are not authorized to visit this webpage.')

# deleting category


@app.route('/delete_category', methods=['POST'])
def delete_category():
    if request.method == 'POST':
        category_id = request.form['category_id']
        db.session.query(Product).filter_by(category_id=category_id).delete()
        db.session.query(Category).filter_by(category_id=category_id).delete()
        db.session.commit()
        return redirect(url_for('showcategory'))

# -------------------------------------------------PRODUCT------------------------------------------------------------------------------

# CREATE


@app.route('/create_product', methods=['GET', 'POST'])
def create_product():
    if request.method == "GET":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        categories = Category.query.all()
        if user.account_type == 1 or user.account_type == 2:
            return render_template("create_product.html", categories=categories, type=user.account_type)
        else:
            return render_template('message.html', message='You are not authorized to visit this webpage.')
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        price = request.form['price']
        category_id = request.form['category_id']
        expiry_date_str = request.form['expiry_date']
        if expiry_date_str:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        else:
            expiry_date = None
        product = Product(name=name, quantity=quantity, price=price,
                          category_id=category_id, expiry_date=expiry_date)
        db.session.add(product)
        db.session.commit()
        return render_template('message.html', message='Product created successfully.')

# READ


@app.route("/show_products", methods=['GET', 'POST'])
def show_products():
    user = db.session.query(User).filter_by(user_id=session['uid']).first()
    products = db.session.query(Category, Product).filter(
        Category.category_id == Product.category_id).all()
    if user.account_type == 1 or user.account_type == 2:
        return render_template("show_products.html", products=products, type=user.account_type)
    else:
        return render_template('message.html', message='You are not authorized to visit this webpage.')

# UPDATE


@app.route("/update_product", methods=["GET", "POST"])
def update_product():
    if request.method == "POST":
        user = db.session.query(User).filter_by(user_id=session['uid']).first()
        page = request.form['page']
        product_id = request.form['product_id']
        if page == "update":
            name = request.form['name']
            quantity = request.form['quantity']
            price = request.form['price']
            expiry_date_str = request.form['expiry_date']
            product = db.session.query(Product).filter_by(
                product_id=product_id).first()
            if name:
                product.name = name
            if quantity:
                product.quantity = quantity
            if price:
                product.price = price
            if expiry_date_str:
                expiry_date = datetime.strptime(
                    expiry_date_str, '%Y-%m-%d').date()
                product.expiry_date = expiry_date
            db.session.commit()
            return redirect(url_for('show_products'))
        else:
            return render_template('update_product.html', product_id=product_id, type=user.account_type)
    else:
        if user.account_type == 1 or user.account_type == 2:
            return redirect(url_for('show_products'))
        else:
            return render_template('message.html', message='You are not authorized to visit this webpage.')

# DELETE : delete product for managers

# confirming product deletion


@app.route('/confirm_delete_product/<int:product_id>', methods=['GET'])
def confirm_delete_product(product_id):
    user = db.session.query(User).filter_by(user_id=session['uid']).first()
    product = db.session.query(Product).filter_by(
        product_id=product_id).first()
    if user.account_type == 1 or user.account_type == 2:
        return render_template('confirm_delete_product.html', product_id=product_id, type=user.account_type)
    else:
        return render_template('message.html', message='You are not authorized to visit this webpage.')

# deleting product


# create a delete button on showcategories.html
@app.route('/delete_product', methods=['GET', 'POST'])
def delete_product():
    if request.method == 'POST':
        product_id = request.form['product_id']
        db.session.query(Product).filter_by(product_id=product_id).delete()
        db.session.commit()
        return redirect(url_for('show_products'))

# -------------------------------------------------------------------ORDERS------------------------------------------------------------------------------------------

# Search Products


@app.route('/search_products', methods=["POST", "GET"])
def search_products():
    if request.method == 'GET':
        products = Product.query.all()
        categories = Category.query.all()
        return render_template('search_products.html', products=products, categories=categories)
    if request.method == 'POST':
        products = db.session.query(Product)
        if request.form['name']:
            products = products.filter(
                Product.name.like('%'+request.form['name']+'%'))
        if request.form['category_id'] != 'all':
            products = products.filter_by(
                category_id=request.form['category_id'])
        if request.form['min_price']:
            products = products.filter(
                Product.price >= request.form['min_price'])
        if request.form['max_price']:
            products = products.filter(
                Product.price <= request.form['max_price'])
        if request.form['expiry_date']:
            expiry_date = datetime.strptime(
                request.form['expiry_date'], '%Y-%m-%d').date()
            products = products.filter(Product.expiry_date >= expiry_date)
        products = products.all()
        categories = Category.query.all()
        return render_template('search_products.html', products=products, categories=categories)

# View Product


@app.route('/view_product', methods=["POST", "GET"])
def view_product():
    if request.method == "POST":
        product_id = request.form['product_id']
        product = db.session.query(Product).filter_by(
            product_id=product_id).first()
        category = db.session.query(Category).filter_by(
            category_id=product.category_id).first()
        return render_template('view_product.html', product=product, categoryname=category.name)
    else:
        return redirect(url_for('search_products'))

# Add to Cart


@app.route('/add_to_cart', methods=["POST", "GET"])
def add_to_cart():
    if request.method == "POST":
        product_id = request.form['product_id']
        quantity = request.form['quantity']
        if session.get('uid') and session['uid']:
            order = Order(
                user_id=session['uid'], quantity=quantity, status=0, product_id=product_id)
            db.session.add(order)
            db.session.commit()
            return render_template('message.html', message='Added item to cart successfully', type=0)
        else:
            return render_template('message.html', message='There was an error with your user id', type=0)
    else:
        return redirect(url_for('search_products'))

# View Cart


@app.route('/view_cart', methods=['GET', 'POST'])
def view_cart():
    if request.method == 'POST':  # show orders with status=0; not placed yet
        if session.get('uid') and session['uid']:
            orders = db.session.query(Order).filter_by(
                user_id=session['uid'], status=0)
            for order in orders:
                order.status = 1
                product = db.session.query(Product).filter_by(
                    product_id=order.product_id).first()
                product.quantity = product.quantity - order.quantity
            db.session.commit()
            return render_template('message.html', message='Order Placed Successfully', type=0)
        else:
            return redirect(url_for('login'))
    else:
        # when user has not clicked place order button and is simply viewing cart
        if session.get('uid') and session['uid']:
            orders = db.session.query(Order, Product).filter(
                Order.user_id == session['uid'], Order.status == 0, Order.product_id == Product.product_id).all()
            sum = 0
            for order in orders:
                sum += order.Product.price * order.Order.quantity
            return render_template('view_cart.html', orders=orders, sum=sum)
        else:
            return redirect(url_for('login'))

# DELETE : delete order of a product from cart


@app.route('/delete_order', methods=["GET", "POST"])
def delete_order():
    if request.method == 'POST':
        order_id = request.form['order_id']
        db.session.query(Order).filter_by(order_id=order_id).delete()
        db.session.commit()
        return redirect(url_for('view_cart'))

# -------------------------------------------------------------API----------------------------------------------------------------------

# COMMON ERRORS


class NotFoundError(HTTPException):
    def __init__(self, status_code):
        self.response = make_response('', status_code)


class InternalServerError(HTTPException):
    def __init__(self, status_code):
        self.response = make_response('', status_code)


class ExistsError(HTTPException):
    def __init__(self, status_code):
        self.response = make_response('', status_code)


class NotExistsError(HTTPException):
    def __init__(self, status_code):
        self.response = make_response('', status_code)


class BuisnessValidationError(HTTPException):
    def __init__(self, status_code, error_code, error_message):
        message = {"error_code": error_code, "error_message": error_message}
        self.response = make_response(json.dumps(message), status_code)

# ----------------------------------------------------------------CATEGORY API


output_category = {
    "category_id": fields.Integer,
    "category_name": fields.String,
}

category_parser = reqparse.RequestParser()
category_parser.add_argument("category_name")


class categoryAPI(Resource):
    # READ
    def get(self, category_id):
        try:
            category = db.session.query(Category).get(int(category_id))
            if category:
                cat = {'category_id': category.category_id,
                       'category_name': category.name}
                return cat, 200
            else:
                raise NotFoundError(status_code=404)
        except NotFoundError as nfe:
            raise nfe
        except Exception as e:
            raise InternalServerError(status_code=500)

    # UPDATE
    def put(self, category_id):
        try:
            args = category_parser.parse_args()
            category_name = args.get("category_name")
            if category_name is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Category Name is required")
            category = db.session.query(Category).filter_by(
                category_id=category_id).first()
            if category:
                category = db.session.query(Category).filter_by(
                    category_id=category_id).first()
                category.name = category_name
                db.session.commit()
                updated_category = db.session.query(
                    Category).filter_by(category_id=category_id).first()
                cat = {'category_id': updated_category.category_id,
                       'category_name': updated_category.name}
                return cat, 200
            else:
                raise NotExistsError(status_code=404)
        except BuisnessValidationError as bve:
            raise bve
        except NotExistsError as nee:
            raise nee
        except Exception as e:
            raise InternalServerError(status_code=500)

    # DELETE
    def delete(self, category_id):
        try:
            category = db.session.query(Category).filter_by(
                category_id=category_id).first()
            if category:
                product = db.session.query(Product).filter_by(
                    category_id=category.category_id).first()
                if product:
                    db.session.delete(product)
                    db.session.commit()
                    product = db.session.query(Product).filter_by(
                        category_id=category.category_id).first()
                db.session.delete(category)
                db.session.commit()
                return "successfully deleted", 200
            else:
                raise NotFoundError(status_code=404)
        except NotFoundError as nfe:
            raise nfe
        except Exception as e:
            raise InternalServerError(status_code=500)

    # CREATE
    def post(self):
        try:
            args = category_parser.parse_args()
            category_name = args.get("category_name")
            if category_name is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Category Name is required")
            category = db.session.query(Category).filter_by(
                name=category_name).first()
            if category:
                raise ExistsError(status_code=409)
            else:
                new_category = Category(name=category_name)
                db.session.add(new_category)
                db.session.commit()
                catid = new_category.category_id
                new_category = db.session.query(
                    Category).filter_by(category_id=catid).first()
                cat = {'category_id': new_category.category_id,
                       'category_name': new_category.name}
                return cat, 201
        except BuisnessValidationError as bve:
            raise bve
        except ExistsError as ee:
            raise ee
        except Exception as e:
            raise InternalServerError(status_code=500)


api.add_resource(categoryAPI, "/api/category",
                 "/api/category/<int:category_id>")


# ------------------------------------------------------PRODUCT API
output_product = {
    "product_id": fields.Integer,
    "product_name": fields.String,
    "product_price": fields.Integer,
    "product_quantity": fields.Integer,
    "product_expiry_date": fields.DateTime,
    "product_category_id": fields.Integer,
}

product_parser = reqparse.RequestParser()
product_parser.add_argument("product_name")
product_parser.add_argument("product_price")
product_parser.add_argument("product_quantity")
product_parser.add_argument("product_category_id")
product_parser.add_argument("product_expiry_date")


class productAPI(Resource):
    # READ
    def get(self, product_id):
        try:
            product = db.session.query(Product).filter_by(
                product_id=product_id).first()
            if product:
                prod = {'product_id': product.product_id, 'product_name': product.name, 'product_quantity': product.quantity,
                        'product_price': product.price, 'product_expiry_date': str(product.expiry_date), 'product_category_id': product.category_id}
                return prod, 200
            else:
                raise NotFoundError(status_code=404)
        except NotFoundError as nfe:
            raise nfe
        except Exception as e:
            raise InternalServerError(status_code=500)

    # UPDATE
    def put(self, product_id):
        try:
            args = product_parser.parse_args()
            product_name = args.get("product_name")
            product_price = args.get("product_price")
            product_quantity = args.get("product_quantity")
            product_expiry_date = args.get("product_expiry_date")
            product_category_id = args.get("product_category_id")
            if product_name is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Name is required")
            if product_price is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Price is required")
            if product_quantity is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Quantity is required")
            if product_category_id is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Category ID is required")
            product = db.session.query(Product).filter_by(
                product_id=product_id).first()
            if product:
                product.name = product_name
                product.price = product_price
                product.quantity = product_quantity
                if product_expiry_date:
                    expiry_date = datetime.strptime(
                        product_expiry_date, '%Y-%m-%d').date()
                    print('exp')
                else:
                    expiry_date = None
                print(expiry_date)
                product.expiry_date = expiry_date
                product.category_id = product_category_id
                db.session.commit()
                upd_product = db.session.query(Product).filter_by(
                    product_id=product_id).first()
                prod = {'product_id': upd_product.product_id, 'product_name': upd_product.name, 'product_quantity': upd_product.quantity,
                        'product_price': upd_product.price, 'product_expiry_date': str(upd_product.expiry_date), 'product_category_id': upd_product.category_id}
                return prod, 200
            else:
                raise NotExistsError(status_code=404)
        except BuisnessValidationError as bve:
            raise bve
        except NotExistsError as nee:
            raise nee
        except Exception as e:
            raise InternalServerError(status_code=500)

    # DELETE
    def delete(self, product_id):
        try:
            product = db.session.query(Product).filter_by(
                product_id=product_id).first()
            if product:
                product = db.session.query(Product).filter_by(
                    product_id=product.product_id).delete()
                db.session.commit()
                return "successfully deleted", 200
            else:
                raise NotFoundError(status_code=404)
        except NotFoundError as nfe:
            raise nfe
        except Exception as e:
            raise InternalServerError(status_code=500)

    # CREATE
    def post(self):
        try:
            args = product_parser.parse_args()
            product_name = args.get("product_name")
            product_price = args.get("product_price")
            product_quantity = args.get("product_quantity")
            product_expiry_date = args.get("product_expiry_date")
            product_category_id = args.get("product_category_id")
            if product_name is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Name is required")
            if product_price is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Price is required")
            if product_quantity is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Quantity is required")
            if product_category_id is None:
                raise BuisnessValidationError(
                    status_code=400, error_message="Product Category ID is required")
            product = db.session.query(Product).filter_by(
                name=product_name).first()
            if product:
                raise ExistsError(status_code=409)
            else:
                if product_expiry_date:
                    expiry_date = datetime.strptime(
                        product_expiry_date, '%Y-%m-%d').date()
                else:
                    expiry_date = None
                new_product = Product(name=product_name, price=product_price, quantity=product_quantity,
                                      category_id=product_category_id, expiry_date=expiry_date)
                db.session.add(new_product)
                db.session.commit()
                prodid = new_product.product_id
                upd_product = db.session.query(
                    Product).filter_by(product_id=prodid).first()
                prod = {'product_id': upd_product.product_id, 'product_name': upd_product.name, 'product_quantity': upd_product.quantity,
                        'product_price': upd_product.price, 'product_expiry_date': str(upd_product.expiry_date), 'product_category_id': upd_product.category_id}
                return prod, 200
        except BuisnessValidationError as bve:
            raise bve
        except ExistsError as ee:
            raise ee
        except Exception as e:
            raise InternalServerError(status_code=500)


api.add_resource(productAPI, "/api/product", "/api/product/<int:product_id>")

# --------------------------------------------------------------MAIN-------------------------------------------------------------------


@app.route('/')
def index():  # default page w/o login
    return render_template('index.html')

# Logout Functionality Handling --


@app.route('/logout')
def logout():
    session.pop('uid', default=None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    # run the app
    app.run(debug=True)
