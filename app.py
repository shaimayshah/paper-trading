from flask import Flask, render_template, request, redirect, Response
# from quart import Quart, render_template, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from sentiment import get_sentiment
from scraping import get_company_data, plot_historical, get_batch_data
import os
import json 

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/trader.db'
db = SQLAlchemy(app)

class Money(db.Model):
    __tablename__ = "money"
    id = db.Column(db.Integer, primary_key=True)
    CurrCash = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return 'Money made' + str(self.id)

class Trade(db.Model):
    __tablename__ = "trade"
    trade_id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(4), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float(10), nullable=False)

    def __repr__(self):
        return 'Trade made ' + str(self.trade_id)

class Portfolio(db.Model):
    __tablename__ = "portfolio"
    ticker = db.Column(db.String(10), primary_key=True)
    shares = db.Column(db.Integer, nullable=False)
    avg_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return 'New stock added ' + self.ticker


@app.route('/', methods=['GET', 'POST'])
def root():
    if request.method == 'GET':
        return render_template('index.html')
    else:
        tick = request.form['tick']
        return redirect('/trade/'+tick)

@app.route('/trade/<string:ticker>', methods=['GET', 'POST'])
def trade(ticker): 
    max_shares = 0
    avg_price = 0
    if request.method == 'GET':
        tick = ticker
        sentiment_news = str(get_sentiment(ticker))
        name, price, market, isOpen = get_company_data(ticker)
        image = plot_historical(ticker)
        CurrCash = Money.query.filter_by(id=1).first().CurrCash
        if(Portfolio.query.filter_by(ticker=ticker).count() != 0):
            max_shares = Portfolio.query.filter_by(ticker=ticker)[0].shares
            avg_price = Portfolio.query.filter_by(ticker=ticker)[0].avg_value
        return render_template('trade.html', sentiment=sentiment_news, name=name, price=price, 
        market=market, isOpen = isOpen, ticker=tick, avg_price=avg_price, image=image, CurrCash=CurrCash, maxshares=int(max_shares))
    else: 
        if request.form['tick']:
            tick = request.form['tick']
            return redirect('/trade/'+tick)

@app.route('/portfolio', methods=['GET', 'POST'])
def show_portfolio():
    portfolios = Portfolio.query.all()
    money = Money.query.all()[0].CurrCash
    current_value = 0
    tickers = []
    for porfolio in portfolios: 
        tickers.append(porfolio.ticker)
    prices = get_batch_data(tickers)
    for portfolio in portfolios:
        current_value += (prices[portfolio.ticker]*porfolio.shares)
    return render_template('portfolio.html', portfolios = portfolios, prices = prices, money=money, currval = current_value)




@app.route('/trade/<string:ticker>/buy/<float:price>', methods=['GET', 'POST'])
def buy(ticker, price):
    # First check how much money needed. 
    share = request.form['shares']
    total_investment = price*int(share)
    CurrCash = Money.query.filter_by(id=1).first().CurrCash
    if(total_investment > CurrCash):
        return("Investment exceeds the amount of cash at hand.")
    else:
        # Reduce money availale 
        Money.query.filter_by(id=1).first().CurrCash = CurrCash - total_investment
        db.session.commit()
        # Make a transaction
        transac = Trade(ticker=ticker, action='buy', shares=share, price=price)
        db.session.add(transac)
        # Check to see if ticker in porfolio, if yes then: 
        if(Portfolio.query.filter_by(ticker=ticker).count() != 0):
            portfolio = Portfolio.query.filter_by(ticker=ticker)[0]
            curr_investment = portfolio.shares * portfolio.avg_value
            new_investment = total_investment
            new_total = curr_investment + new_investment
            total_shares = portfolio.shares + int(share)
            portfolio.shares = total_shares
            portfolio.avg_value = new_total/total_shares
            db.session.commit()

        else:
            portfolio = Portfolio(ticker=ticker, shares=share, avg_value=price)   
            db.session.add(portfolio)
            db.session.commit()      
        return redirect('/trade/'+ticker)

    
@app.route('/trade/<string:ticker>/sell/<float:price>', methods=['GET', 'POST'])
def sell(ticker, price):
    
    # Get no. of shares selling
    share = request.form['shares']
    total_sold = price*int(share)
    
    money = Money.query.filter_by(id=1).first()
    money.CurrCash += total_sold

    # Create a trade class
    transac = Trade(ticker=ticker, action='sell', shares=share, price=price)
    db.session.add(transac)

    #Edit Portfolio
    portfolio = Portfolio.query.filter_by(ticker=ticker)[0]
    new_shares = portfolio.shares - int(share)

    if(new_shares == 0):
        db.session.delete(portfolio)
        db.session.commit()
        return redirect('/trade/'+ticker)
    else: 
        portfolio.shares = new_shares
        db.session.commit()
        return redirect('/trade/'+ticker)


@app.route('/search', methods=['GET', 'POST'])
def search(): 
    if request.method == 'GET':
        return render_template('search.html')
    else: 
        ticker = request.form['tick']
        return redirect('/trade/'+ticker)

if __name__ == "__main__":
    os.environ["IEX_API_VERSION"] = "iexcloud-sandbox" 
    app.run(debug=True)
    