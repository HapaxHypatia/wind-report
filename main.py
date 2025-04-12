"""
Script to get forecast data from Willy Weather api and BOM website and send a
boating forecast for the weekend by email on Wednesdays and Fridays.
"""

from dotenv import load_dotenv
import os

# BOM Scrape
from selenium import webdriver
from selenium.webdriver.common.by import By

# Willy Weather
import requests
import json
import copy
from matplotlib import ticker
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
from matplotlib.markers import MarkerStyle
import matplotlib.dates as mdates
from datetime import date, datetime, timezone, timedelta

# Email
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

# TODO schedule the script to run on certain days
# TODO day/night lines in graph (shade between certain minor ticks)
# TODO data point labels should be direction and strength (e.g.'gentle SSE')
# TODO data point labels should be greyed out and not overlap each other
# TODO generate graph from forecast data, without a second call to get graph data


def scrapeBOM():
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(60)

    driver.get("http://www.bom.gov.au/qld/forecasts/moreton-bay.shtml")
    content = driver.find_element(by=By.ID, value="content")
    syn = content.find_element(by=By.CLASS_NAME, value="synopsis")
    syn_elements = syn.find_elements(by=By.XPATH, value=".//*")
    result = []
    for item in syn_elements:
        result.append(item.text)
    days = content.find_elements(by=By.CLASS_NAME, value="day")
    for item in days:
        result.append('\n')
        info = item.find_elements(by=By.XPATH, value=".//*")
        result += ([i.text for i in info])
    return result


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


def draw_graph(data, x_list, y_list):
    def rotate_marker(marker, degrees):
        rotated_marker = copy.deepcopy(marker)
        rotated_marker = rotated_marker.rotated(deg=degrees)
        return rotated_marker

    arrow = u'$\u2191$'
    fig, ax = plt.subplots(constrained_layout=True, figsize=(15, 6))
    hour_locator = mdates.HourLocator()
    hour_formatter = mdates.DateFormatter("%H:%M")
    day_locater = mdates.DayLocator()

    # Set up xticks: major
    ax.set_xlim(x_list[0]-timedelta(minutes=30), x_list[-1]+timedelta(minutes=30))
    ax.xaxis.set_major_locator(hour_locator)
    ax.xaxis.set_major_formatter(hour_formatter)
    ax.tick_params("x", which="major", rotation=45)

    days = ax.get_xticks()[24::24]
    for loc in days:
        ax.axvline(loc)
    for x0, x1 in zip(days[::2], days[1::2]):
        plt.axvspan(x0, x1, color='black', alpha=0.1, zorder=0)

    # Set up secondary axis
    secax = ax.secondary_xaxis('top')
    secax.xaxis.set_major_locator(mdates.DayLocator())
    secax.xaxis.set_major_formatter(ticker.NullFormatter())
    secax.tick_params(axis='x', which='major', tick1On=False, tick2On=False)

    secax.xaxis.set_minor_locator(mdates.HourLocator(byhour=12))
    secax.xaxis.set_minor_formatter(mdates.DateFormatter('%d %b'))
    secax.tick_params(axis='x', which='minor', tick1On=False, tick2On=False)

    # Align the minor tick label
    for label in secax.get_xticklabels(minor=True):
        label.set_horizontalalignment('right')

    ax.plot(x_list, y_list)

    # Set up y axis
    plt.ylim(0, 40)
    yloc = plticker.MultipleLocator(base=10.0)
    ax.yaxis.set_major_locator(yloc)
    ax.grid(visible=True, which='major', axis='y')

    # Place markers
    for x, y, dir_val, str_val in data:
        arrow_marker = mpl.markers.MarkerStyle(marker=arrow)
        m = rotate_marker(arrow_marker, -dir_val)
        ax.scatter(x, y, marker=m, color=str_val['colour'], s=200, zorder=-1)

    # Save & display graph
    fig1 = plt.gcf()
    fig1.savefig('wind.png')
    # plt.show()


if __name__ == '__main__':
    load_dotenv(dotenv_path=".env")
    open("report.txt", 'w').close()

    # Scrape BOM forecast & write to report ----------------------------------------------------------------------------
    BOM = scrapeBOM()
    with open('report.txt', 'a') as file:
        file.write(f"Moreton Bay Marine Forecast from BOM\n\n")
        file.write("\n".join(BOM))
        file.write('\n\n\n')

    # Get graph data from Willy Weather & save to file -----------------------------------------------------------------
    apiKey = os.environ.get("API_KEY")
    today = date.today()
    datestring = today.strftime("%a %d %b %Y")
    day, date, month, year = datestring.split()

    if day == "wed":
        offset = 3
    if day == "fri":
        offset = 1
    else:
        offset = 1
    startDate = today + timedelta(offset)

    graphJson = get_forecast_graph(startDate, "wind", 3)
    graphData = json.loads(graphJson)
    graphDays = graphData['forecastGraphs']['wind']['dataConfig']['series']['groups']
    times = []
    speeds = []
    degrees = []
    for i, day in enumerate(graphDays):
        times += [datetime.fromtimestamp(point['x'], tz=timezone.utc) for point in day['points']]
        speeds += ([point['y'] for point in day['points']])
        degrees += ([point['direction'] for point in day['points']])
    cutoffs = [
        {'cutoff': .6,
         'colour': '#F1F2F3',
         'description': 'calm'},
        {'cutoff': 6.8,
         'colour': '#d1ef51',
         'description': 'light'},
        {'cutoff': 10.7,
         'colour': '#a5de37',
         'description': 'gentle'},
        {'cutoff': 15.6,
         'colour': '#48ad00',
         'description': 'moderate'},
        {'cutoff': 21,
         'colour': '#0ec1f2',
         'description': 'fresh'},
        {'cutoff': 27,
         'colour': '#1896eb',
         'description': 'strong'},
        {'cutoff': 33.4,
         'colour': '#226be4',
         'description': 'near gale'},
        {'cutoff': 40.4,
         'colour': '#1950ab',
         'description': 'gale'},
        ]
    strengths = []
    for y in speeds:
        for item in cutoffs:
            if y < item['cutoff']:
                strengths.append(item)
                break

    data = zip(times, speeds, degrees, strengths)
    draw_graph(data, times, speeds)

    # Get Forecast Data from Willy Weather -----------------------------------------------------------------------------
    # forecastJson = get_forecast(startDate, "wind", 2)
    # forecastData = json.loads(forecastJson)
    # days = forecastData['forecasts']['wind']["days"]
    # entries = [e for d in days for e in d['entries']]
    # windSpeeds = [e['speed'] for e in entries]
    #
    # if max(windSpeeds) > 15:
    #     safeCruising = False
    # else:
    #     safeCruising = True
    #
    # with open('report.txt', 'a') as file:
    #     file.write(f"Willy Weather Wind Peel Island Forecast Report on {datestring}:\n\n")
    #     # if safeCruising:
    #     #     file.write("Looks safe to cruise this weekend!\n\n")
    #     for d in days:
    #         dateList = d['dateTime'].split()[0].split("-")
    #         dateObj = datetime.datetime(int(dateList[0]), int(dateList[1]), int(dateList[2]))
    #         file.write(f"{dateObj.strftime('%a %d %b %Y')}\n")
    #         for ent in d['entries']:
    #             timestring = ent['dateTime'][-8:-3]
    #             file.write(f"{timestring} {ent['speed']} knots, {ent['directionText']}\n")
    #         file.write('\n')

    # Set environment variables for email ------------------------------------------------------------------------------
    port = os.environ.get("PORT")  # For SSL
    smtp_server = os.environ.get("SERVER")
    sender_email = os.environ.get("EMAIL")  # Enter your address
    receiver_email = os.environ.get("RECIPIENTS")
    password = os.environ.get("PASSWORD")

    # Create text content ----------------------------------------------------------------------------------------------
    textfile = "report.txt"
    with open(textfile) as fp:
        text = "\n".join(fp.readlines())

    # Set up email -----------------------------------------------------------------------------------------------------
    message = MIMEMultipart()
    message["Subject"] = "Wind Forecast"
    message['From'] = sender_email
    message['To'] = receiver_email

    # Write the HTML part ----------------------------------------------------------------------------------------------
    html = """
            <html>
            <body>
                <img src="cid:graphImage">
            </body>
            </html>
            """

    # Add image --------------------------------------------------------------------------------------------------------
    fp = open('wind.png', 'rb')
    image = MIMEImage(fp.read())
    fp.close()
    image.add_header('Content-ID', '<graphImage>')
    message.attach(image)

    # Convert both parts to MIMEText objects and add them to the MIMEMultipart message ---------------------------------
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part2)
    message.attach(part1)

    # Send email -------------------------------------------------------------------------------------------------------
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context, timeout=120) as server:
        try:
            server.login(sender_email, password)
            server.send_message(message, sender_email, receiver_email)
            print("Email sent.")
        except Exception as e:
            print(e)

