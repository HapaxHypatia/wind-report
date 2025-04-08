# webscraper for 2 weather sites
from dotenv import load_dotenv
import datetime
import os
import ssl
import requests
import json
import smtplib
from email.message import EmailMessage


# TODO scrape BOM data
# TODO re-create graph from data? Or webscrape graph?
# TODO schedule the script to run on certain days

load_dotenv(dotenv_path=".env")


def get_request(req_type, location, payload):
    if req_type == "search":
        url = f"https://api.willyweather.com.au/v2/{apiKey}/search.json"
    if req_type == "weather":
        url = f"https://api.willyweather.com.au/v2/{apiKey}/locations/{location}/weather.json?units=speed:knots"

    r = requests.get(url, params=payload)
    if r.status_code != 200:
        print("Request failed.")
    return r.content


def get_forecast(startDate, forecast_type, days):
    payload = {
        "forecasts": [forecast_type],
        "days": days,
        "startDate": startDate
    }
    return get_request("weather", 8629, payload)


def get_forecast_graph(startDate, graph_type, days):
    payload = {
        "forecastGraphs": [graph_type],
        "days": days,
        "startDate": startDate
    }
    return get_request("weather", 8629, payload)

def get_units():
    payload = {
        "units": {
            "amount": "mm",
            "distance": "km",
            "speed": "knots",
            "swellHeight": "ft",
            "temperature": "c",
            "tideHeight": "ft",
            "riverHeight": "ft",
            "pressure": "hpa",
            "cloud": "oktas"
    }
  }


if __name__ == '__main__':
    # locationID = 8629
    apiKey = os.environ.get("API_KEY")

    today = datetime.date.today()
    datestring = today.strftime("%a %d %b %Y")
    day, date, month, year = datestring.split()

    if day == "wed":
        offset = 3
    if day == "fri":
        offset = 1
    else:
        offset = 0
    startDate = today + datetime.timedelta(offset)
    jsonContent = get_forecast(startDate, "wind", 2)
    data = json.loads(jsonContent)
    days = data['forecasts']['wind']["days"]

    # TODO logic to check if it is good weather, add a summary at top of report

    entries = [e for d in days for e in d['entries']]
    windSpeeds = [e['speed'] for e in entries]
    if max(windSpeeds) > 15:
        safeCruising = False
    else:
        safeCruising = True

    open("report.txt", 'w').close()
    with open('report.txt', 'a') as file:

        file.write(f"Forecast Report on {datestring}:\n\n")
        if safeCruising:
            file.write("Looks safe to cruise this weekend!\n\n")
        for d in days:
            dateList = d['dateTime'].split()[0].split("-")
            dateObj = datetime.datetime(int(dateList[0]), int(dateList[1]), int(dateList[2]))
            file.write(f"{dateObj.strftime('%a %d %b %Y')}\n")
            for ent in d['entries']:
                timestring = ent['dateTime'][-8:-3]
                file.write(f"{timestring} {ent['speed']} knots, {ent['directionText']}\n")
            file.write('\n')

    port = os.environ.get("PORT")  # For SSL
    smtp_server = os.environ.get("SERVER")
    sender_email = os.environ.get("EMAIL")  # Enter your address
    receiver_email = os.environ.get("RECIPIENTS")# Enter receiver address
    password = os.environ.get("PASSWORD")

    textfile = "report.txt"
    # Open the plain text file whose name is in textfile for reading.
    with open(textfile) as fp:
        # Create a text/plain message
        msg = EmailMessage()
        msg.set_content(fp.read())
    msg['Subject'] = 'Weather report'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context, timeout=120) as server:
        try:
            server.login(sender_email, password)
            server.send_message(msg, sender_email, receiver_email)
            print("Email sent.")
        except Exception as e:
            print(e)