from flask import Flask, render_template, request, url_for, flash, redirect
import numpy as np
import pandas as pd
import yfinance as yf
from os import removedirs
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, length, ValidationError
from flask_bcrypt import Bcrypt
import financials as fin

app = Flask(__name__)
sql=SQLAlchemy(app)
bcrypt=Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URL']='sqlite:///database.sql'
app.secret_key = "tdlog"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(sql.Model,UserMixin): 
   id=sql.Column(sql.Integer,primary_key=True)
   username = sql.Column(sql.String(100),nullable=False, unique=True)
   email_adress = sql.Column(sql.String(80),nullable=False)
   password = sql.Column(sql.String(80),nullable=False)
sql.create_all()

class RegisterForms(FlaskForm): 
    username = StringField(validators=[InputRequired(),Length(min=4, max=100)],render_kw={"placeholder": "Username"})
    email_adress = StringField(validators=[InputRequired(),Length(min=4, max=100)],render_kw={"placeholder": "Email Adress"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

def validate_username(self, username) :
    existing_user_username = User.query.filter_by(username=username.data).first()
    if existing_user_username :
        raise ValidationError("that username already exists, please find an other one")

def validate_email_adress(self, email_adress) :
    existing_user_email_adress = User.query.filter_by(email_adress=email_adress.data).first()
    if existing_user_email_adress :
        raise ValidationError("that email adress already exists, please find an other one")

class LoginForms(FlaskForm): 
    username = StringField(validators=[InputRequired(),Length(min=4, max=20)],render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)],render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

messages = {'ticker_title': 'Ticker: ',
             'ticker_content': '',
             'name_title': 'Company: ',
             'name_content': '',
             'period':'5d' 
             } 

def graphic(acao,interval="5d"):
    '''
    Returns the values need to render the price evolution graph

            Parameters:
                    acao (ticker object): target company
                    interval (str): the time interval of the graph

            Returns:
                   list_graphic (list): a list containing the graphs values and labels
    '''
    hist = acao.history(period=interval)['Close']
    labels = list(np.array(hist.index, dtype='datetime64[D]').astype(str)) 
    values=list(np.around(np.array(hist),decimals=2))
    list_graphic = [labels, values]
    return list_graphic

def description(acao):
    '''
	returns a simple description of the company whose ticker we searched

	Parameters:
		acao : a dictionary that contains the informations about the company in the YahooFinance database
	Returns:
		list_description : a list that contains the short name of the company and its description 
'''
    shortName = acao.info['shortName']
    summary = acao.info['longBusinessSummary']
    list_description = [shortName, summary]
    return list_description


def fairprice(acao,ticker):
    '''
    Calls the functions from the financials module and returns the fair value

            Parameters:
                    acao (ticker object): target company
                    ticker (str): the company ticker 

            Returns:
                    value (float): the company's fair value
    '''
    finviz=fin.get_finviz_data(ticker)
    discount_rate=fin.discount_rate(finviz)
    if discount_rate is None:
        return "nan"

    EPS_growth_5Y=finviz['EPS next 5Y']
    EPS_growth_6Y_to_10Y=finviz['EPS next 5Y']/2
    EPS_growth_11Y_to_20Y=0.04

    value= fin.calculate_intrinsic_value(acao,EPS_growth_5Y, EPS_growth_6Y_to_10Y, EPS_growth_11Y_to_20Y, discount_rate,finviz)

    return value

@app.route("/", methods=("POST", "GET"))
def home():
    '''
	returns the home page, where we have the search box and the buttons to login and register

	Parameters: 
		None

	Returns:
		render_template("home.html")
	
'''
    if request.method == 'POST':
        ticker = request.form['user_input']
        if not ticker:
            return render_template("home.html")
        else:
            messages['ticker_content'] = ticker
            return redirect(url_for('page_ticker'))
    else:
        return render_template("home.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
	returns the login page, where we have the forms to login, and the buttons to go back to home and go to register page

	Parameters: 
		None

	Returns:	
		render_template('login.html', form=form )
'''
    form = LoginForms()
    if form.validate_on_submit() :
        #permet de vérifier si les données que l'on rentre pour se connecter sont correcte (le mot de passe correspond bien à l'email dans la table user)
        user = User.query.filter_by(username=form.username.data).first()
        if user : 
            #si tel est le cas l'utilisateur peut se connecter
            if bcrypt.check_password_hash(user.password, form.password.data) :
                login_user(user)
                return redirect (url_for('dashboard')) 
          #sinon on signifie à l'utilisateur qu'il n'a pas la bonne combinaison email/password
        flash ('You wrote an invalid username/password. Try again.')
        return render_template('login.html',form=form) 
    return render_template('login.html', form=form )

    if request.method == 'GET':
        return render_template("home.html")


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    '''
	returns a page similar to the home page, where we have the search box, the buttons to logout and register, and also shows the name of the user currently logged in

	Parameters: 
		None

	Returns: 
		render_template('dashboard.html')	
    '''
    if request.method == 'POST':
        ticker = request.form['user_input']
        if not ticker:
            return render_template("dashboard.html")
        else:
            messages['ticker_content'] = ticker
            return redirect(url_for('page_ticker'))
    else:
        return render_template('dashboard.html')


#fonction pour se déconnecter
@app.route('/logout',methods=['GET', 'POST'])
@login_required
def logout():
    '''
	returns the home page, after logging out the user

	Parameters: 
		None

	Returns: 
		redirect(url_for('home'))	
'''
    logout_user()
    return redirect(url_for('home'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
	returns the register page, where we have the forms to register, and the buttons to go back to home and go to login page

	Parameters: 
		None

	Returns:
		render_template('register.html', form=form)	
'''
    form = RegisterForms()
    if form.validate_on_submit() :
        #pour sécuriser la connexion on hash le mot de passe 
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username = form.username.data, password = hashed_password, email_adress = form.email_adress.data)
        sql.session.add(new_user)
        sql.session.commit()
        return redirect (url_for('login'))
    return render_template('register.html', form=form)
    if request.method == 'GET':
        return render_template("home.html")


@app.route("/page_ticker", methods=("POST", "GET"))
def page_ticker():
    '''
	returns the page with the informations about the company whose ticker we searched, where we have the buttons to go back to home, login and do a new register, and also the search box to do a new search. If there is a user logged in, login is replaced by logout and we can also see a button to favorite the company in the profile. 

	Parameters: 
		None

	Returns:	
		redirect(url_for('page_ticker')) 
'''
    acao=yf.Ticker(messages['ticker_content'])
    list_description = description(acao)

    if request.method == 'POST':
        if 'user_input' in request.form :
            messages['ticker_content'] = request.form['user_input']
            #resets selection to standard value, can keep preference if deleted
            messages['period']='5d'

        if 'interval' in request.form :
            interval=request.form["interval"]
            messages['period']=interval

        return redirect(url_for('page_ticker')) 
        
            
    else:
        list_graphic = graphic(acao,messages['period'])      
        price=fairprice(acao,messages['ticker_content'])
        if type(price)==str:
            recommendation="nan"
        else:
            if list_graphic[1][-1]<price:
                recommendation="Buy"
            else:
                recommendation="Sell"
        return render_template("page_ticker.html", 
            messages=messages, 
            labels=list_graphic[0], 
            values=list_graphic[1], 
            shortName=list_description[0], 
            summary=list_description[1],
            recommendation=recommendation,
            price=price)

    if request.method == 'GET':
        return render_template("home.html")


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    '''
	returns the profile page, where we have the informations about the user and the buttons to go back to home, logout and do a new register. The function only runs if there is a user logged in.

	Parameters: 
		None

	Returns: 
		render_template("profile.html")	
'''
    return render_template("profile.html")


if __name__ == "__main__":
    app.run(debug=True)
