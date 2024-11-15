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


@app.route('/race/<round>')
def race_details(round):
    url = 'http://ergast.com/api/f1/2024.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    race_details = next((race for race in races if race['round'] == round), None)

    if not race_details:
        return "Race not found", 404

    return render_template('race.html', race=race_details)

@app.route('/drivers')
def drivers_standings():
    url = 'http://ergast.com/api/f1/2024/driverStandings.json'
    response = requests.get(url)
    data = response.json()
    drivers = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']

    return render_template('drivers.html', drivers=drivers)


if __name__ == '__main__':
    app.run(debug=True)