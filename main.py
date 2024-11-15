from flask import Flask, render_template
import requests
from datetime import date, datetime

app = Flask(__name__)

@app.route('/')

def home():
    return render_template('index.html')

@app.route('/calender')
def calender():
    url = 'http://ergast.com/api/f1/2024.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']
    return render_template('calender.html', races=races, date=date, datetime=datetime)


if __name__ == '__main__':
    app.run(debug=True)