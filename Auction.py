from flask import Flask,request, session, redirect, render_template,flash 
from flask_login import  UserMixin,LoginManager,login_required, login_user, current_user, logout_user
from flask_mail import Mail,Message
import os
from datetime import date,timedelta
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.db') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '@yschen'

app.config['MAIL_SERVER'] = 'smtp.test.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'username'
app.config['MAIL_PASSWORD'] = 'password'

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    username=db.Column(db.String(100))
    password= db.Column(db.String(100))
    email= db.Column(db.String(255))
    phone= db.Column(db.String(11))

    def __init__(self,username,password,email,phone):
        self.username=username
        self.password=password
        self.email=email
        self.phone=phone

    def __repr__(self):
        return '<User %r>' % self.username 

class Item(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True,autoincrement=True)
    name=db.Column(db.String(255))
    seller_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    pic = db.Column(db.Text)
    add_date= db.Column(db.Date)
    description =db.Column(db.Text)
    is_sold = db.Column(db.Boolean,default=False) 
    seller = db.relationship('User')
    

    def __init__(self,name, seller_id, add_date,description,pic ):
        self.name = name
        self.pic  = pic 
        self.add_date = add_date
        self.description = description
        self.seller_id = seller_id 

    def __repr__(self):
        return '<Item %r>' % self.name 

class Bid(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)  
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False) 
    price = db.Column(db.Integer, nullable=False)
    user = db.relationship('User')

    def __init__(self, user_id, item_id, price):
        self.user_id=user_id
        self.item_id=item_id
        self.price=price 

    def __repr__(self):
        return '<Bid %r>' % self.id
    
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user

@app.route("/")
def index():
    items = Item.query.filter_by(is_sold=False)
    res = []
    for i in items:
        b = Bid.query.filter_by( item_id=i.id ).order_by(-Bid.price).first()
        if b is not None:
            res.append( (b.price,i) )
        else:
            res.append( ( 0, i ) )
    return render_template('index.html',res = res )  

@app.route("/home")
@login_required
def home():
    return render_template('home.html')


@app.route("/pay")
@login_required
def pay():
    return render_template('pay.html')

@app.route("/bid",  methods=['GET', 'POST'] )
@login_required 
def bidnow():
    if request.method == "POST":
        item_id = int(request.form['tid'])
        price =  int(request.form['bid'])
        if Item.query.get(item_id).seller_id == current_user.id:
            flash("Can't bid for your own item ! ")
            return redirect('/bid?id={}'.format(item_id))
        if (date.today() - Item.query.get(item_id).add_date) > timedelta(days=3): #three days duration 
            flash( "The auction is over !" )
            return redirect('/bid?id={}'.format(item_id))
        bid_price = Bid.query.filter_by( item_id=item_id ).order_by(-Bid.price).first()
        if bid_price is not None:
            if bid_price.price < price -10:
                flash("Bid price must 10p higher than others ! ")
                return redirect('/bid?id={}'.format(item_id)) 
        bd = Bid.query.filter_by( user_id=current_user.id,item_id=item_id ).first()
        if bd is not None:
            bd.price =price 
            db.session.commit()
        else:
            b = Bid(  user_id=current_user.id, item_id=item_id, price=price )
            db.session.add(b)
            db.session.commit()
        flash("Bid Success! ")
        return redirect('/detail?id={}'.format(item_id)) 
    else:
        item = Item.query.get(int(request.args.get('id') ))
        return render_template('bid.html',item=item)

@app.route("/detail")
@login_required 
def detail():
    item = Item.query.get(int(request.args.get('id') )) 
    current_bid = Bid.query.filter_by(  item_id = int(request.args.get('id') ) ).order_by(-Bid.price).first() 
    return render_template('detail.html',item=item, price= current_bid.price if current_bid else "No bid" )


@app.route("/myitems")
@login_required 
def myitems():
    items = Item.query.filter_by(seller_id=current_user.id).all()
    return render_template('my.html',items=items) 

@app.route("/duraion_check")
@login_required 
def duraion_check():
    items = Item.query.filter_by(is_sold=False)
    for item in items:
        if (date.today() - item.add_date) > timedelta(days=3): #three days duration 
            bs = Bid.query.filter_by(item_id=item.id).order_by(-Bid.price).all()
            if len(bs) >= 1:
                msg = Message("Auction Results",
                  sender="from@auction.com",
                  recipients=[bs[0].user.email])
                msg.html = 'Congratulations! You win the item ,please click the following link to pay for it. <a href="/pay?bid={bs[0].id}"> Click to pay </a>' 
                # mail.send(msg)
                if len(bs) >1:
                    with mail.connect() as conn:
                        for b in bs[1:]:
                            message = 'We are sorry to inform you that you did not win the auction due to your bid.To see more datail, <a href="/detail?id={b.id}"> Click </a> '
                            subject = "Auction Results"
                            print(message)
                            msg = Message(recipients=[b.user.email],
                                        body=message,
                                        subject=subject)
                            conn.send(msg) 
    return "Check OK"



@app.route("/sell" , methods=['GET', 'POST'])
@login_required 
def sell():
    if request.method == "POST":
        name=request.form['name']
        photo=request.files['photo']
        pic = '/static/' + photo.filename
        photo.save(basedir+pic)
        desc=request.form['desc']
        # print(pic)
        item = Item(name=name,seller_id=current_user.id,add_date=date.today() , pic=pic,description=desc )
        db.session.add(item)
        db.session.commit() 
        flash("Add item success !")
        return redirect('/sell')
    else:
        return render_template('sell.html')

@app.route("/domark" , methods=['GET'])
@login_required
def domark():
    try:
        item = Item.query.filter_by(seller_id=current_user.id,id=int( request.args.get('id') )).first()
        item.is_sold = True
        db.session.commit()  
    except Exception as e:
        raise(e)
        db.session.rollback() 
        flash("save failed !")
    return  redirect('/myitems')   


@app.route("/register" , methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name=request.form['username']
        pwd=request.form['password']
        email=request.form['email']
        phone=request.form['phone']
        if User.query.filter_by(username=name).first():
            flash("This username has already been used !")
            return render_template('register.html')
        user = User(username=name,password=pwd,email=email,phone=phone)
        db.session.add(user)
        db.session.commit() 
        flash("Register success !")
        return redirect('/login')
    else:
        return render_template('register.html')

@app.route("/login" , methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        name=request.form['username']
        pwd=request.form['password']
        user = User.query.filter_by(username=name,password=pwd).first()
        if user: 
            login_user(user) 
            return redirect('/home')
    else:
        return render_template('login.html')

@app.route("/logout" , methods=['GET'])
def logout():
    logout_user()
    return redirect('/login')


    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True )
    