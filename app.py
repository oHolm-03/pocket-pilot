from flask import Flask, render_template, request, redirect, url_for, flash, session as flask_session, abort
from dotenv import load_dotenv
import numpy as np
from src.tracker import FinanceTracker
from src.predictor import BalancePredictor
import plotly.graph_objs as go
import plotly.utils
import json
import os
from functools import wraps
import secrets
import hmac
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
flask_secret_key = os.getenv("FLASK_SECRET_KEY")

if not supabase_url or not supabase_key:
    raise RuntimeError("Supabase url and/or key missing")
if not flask_secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is missing")

app = Flask(__name__)
app.secret_key = flask_secret_key
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)


@app.before_request
def ensure_csrf_token():
    if 'csrf_token' not in flask_session:
        flask_session['csrf_token'] = secrets.token_urlsafe(32)
    if request.method == 'POST':
        supplied = request.form.get('csrf_token', '')
        expected = flask_session.get('csrf_token', '')
        if not supplied or not hmac.compare_digest(supplied, expected):
            abort(400, description='Invalid CSRF token')


@app.context_processor
def inject_csrf_token():
    return {'csrf_token': flask_session.get('csrf_token', '')}


def create_user_client():
    client = create_client(supabase_url, supabase_key)
    access_token = flask_session.get('supabase_access_token')
    refresh_token = flask_session.get('supabase_refresh_token')
    if access_token and refresh_token:
        client.auth.set_session(access_token, refresh_token)
    return client


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not flask_session.get('user_id'):
            flash('Please sign in to continue.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


def get_current_tracker():
    user_id = flask_session['user_id']
    return FinanceTracker(create_user_client(), user_id)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        response = create_client(supabase_url, supabase_key).auth.sign_up({
            'email': email,
            'password': password,
        })
        if response.session:
            flask_session['user_id'] = response.user.id
            flask_session['supabase_access_token'] = response.session.access_token
            flask_session['supabase_refresh_token'] = response.session.refresh_token
            return redirect(url_for('index'))
        flash('Check your email to confirm your account.', 'info')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        try:
            response = create_client(supabase_url, supabase_key).auth.sign_in_with_password({
                'email': email,
                'password': password,
            })
            flask_session['user_id'] = response.user.id
            flask_session['supabase_access_token'] = response.session.access_token
            flask_session['supabase_refresh_token'] = response.session.refresh_token
            return redirect(url_for('index'))
        except Exception as error:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    try:
        create_user_client().auth.sign_out()
    except Exception:
        pass
    flask_session.clear()
    return redirect(url_for('login'))


# ROUTES
@app.route('/')
@login_required
def index():
    tracker = get_current_tracker()
    #get summary stats
    stats = tracker.get_summary_stats()

    #get recent transactions
    recent_transactions = tracker.transactions[-10:][::-1]

    #render the HTML tempalte and pass data to it
    return render_template('index.html', stats=stats, transactions=recent_transactions)

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    #get form data, request.form is a dictionary with the form fields
    trans_type = request.form.get('type') # income or expense
    amount = float(request.form.get('amount'))
    description = request.form.get('description', '')

    #add transaction using the signed-in user's tracker
    tracker = get_current_tracker()
    tracker.add_transaction(amount, trans_type, description)

    return redirect(url_for('index'))

@app.route('/predictions')
@login_required
def predictions():
    tracker = get_current_tracker()
    #get num days from URL parameter (def 30)
    days = request.args.get('days', 30, type=int)
    days = max(7, min(days, 365))

    #get predictions from a predictor for the signed-in user
    predictor = BalancePredictor(tracker)
    result = predictor.predict_future_balance(days)

    chart_json = None
    trend_info = None

    if result:
        future_dates, predictions_data, hist_dates, hist_balances = result
        trend_info = predictor.get_trend_info()
        
        # Convert predictions_data to list if it's numpy array
        predictions_list = predictions_data.tolist() if hasattr(predictions_data, 'tolist') else list(predictions_data)

        #Calculate confidence interval
        std_dev = np.std(hist_balances)

        #Start with +-10% of std_dev, grow to +-30% by end of prediction period
        confidence_lower = []
        confidence_upper = []

        for i, pred in enumerate(predictions_list):
            uncertainty_factor = 0.1 + (0.2 * (i/len(predictions_list)))
            margin = std_dev * uncertainty_factor
            confidence_lower.append(pred-margin)
            confidence_upper.append(pred+margin)

        historical_trace = go.Scatter(
            x=hist_dates,
            y=hist_balances,
            mode='lines',
            name='Historical Balance',
            line=dict(color='blue', width=2)
        )

        prediction_trace = go.Scatter(
            x=future_dates,
            y=predictions_list,
            mode='lines',
            name='Predicted Balance',
            line=dict(color='red', width=2, dash='dash'),
            connectgaps=True
        )

        #Upper confidence bound 
        upper_bound_line = go.Scatter(
            x=future_dates,
            y=confidence_upper,
            mode='lines',
            name='Upper Confidence',
            line=dict(color='rgba(255, 0, 0, 0.6)', width=1, dash='dot')
        )

        #Lower confidence bound
        lower_bound_line = go.Scatter(
            x=future_dates,
            y=confidence_lower,
            mode='lines',
            name='Lower Confidence',
            line=dict(color='rgba(255, 0, 0, 0.6)', width=1, dash='dot')
        )

        #create lists for concat
        future_dates_list = list(future_dates)

        #Shaded fill for upper bound CI
        fill_upper = go.Scatter(
            x=future_dates_list +future_dates_list[::-1],
            y=confidence_upper + predictions_list[::-1],
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        )

        #Shaded fill for lower bound CI
        fill_lower = go.Scatter(
            x=future_dates_list +future_dates_list[::-1],
            y=predictions_list + confidence_lower[::-1],
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        )

        data = [fill_upper, fill_lower, historical_trace, upper_bound_line, prediction_trace, lower_bound_line]

        layout = go.Layout(
            title='Balance History and Predictions',
            xaxis=dict(title='Date'),
            yaxis=dict(title='Balance ($)'),
            hovermode='closest',
            template='plotly_white'
        )

        fig = go.Figure(data=data, layout=layout)
        chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return render_template('predictions.html', chart_json=chart_json, trend_info=trend_info, days=days)

    return render_template(
        'predictions.html',
        chart_json=None,
        trend_info=None,
        days=days,
    )
    
@app.route('/analytics')
@login_required
def analytics():
    tracker = get_current_tracker()
    stats = tracker.get_summary_stats()

    data = [
        go.Bar(
            x=['Income', 'Expenses'],
            y=[stats['total_income'], stats['total_expenses']],
            marker=dict(color=['rgba(0, 100, 0, 1)', 'rgba(139, 0, 0, 1)']),
            text=[f"${stats['total_income']:,.2f}", f"${stats['total_expenses']:,.2f}"],
            textposition='outside'
        )
    ]

    layout = go.Layout(
        title='Income vs Expenses',
        yaxis=dict(title='Amount ($)'),
        template='plotly_white'
    )

    fig = go.Figure(data=data, layout=layout)
    chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('analytics.html', chart_json=chart_json, stats=stats)
    
@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    tracker = get_current_tracker()
    tracker.delete_transaction(transaction_id)
    return redirect(url_for('index'))
    
# Run the server
if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting Personal Finance Tracker Web App")
    print("="*60)
    print("Open your browser and go to: http://localhost:5000")
    print("Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)