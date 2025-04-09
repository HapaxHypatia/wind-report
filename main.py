# webscraper for 2 weather sites
from dotenv import load_dotenv
import datetime
import os
import ssl
import requests
import json
import smtplib
from email.message import EmailMessage
from selenium import webdriver
from selenium.common import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
import copy
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
from matplotlib.markers import MarkerStyle

# TODO schedule the script to run on certain days
# TODO day/night lines in graph
# TODO populate graph data from api request
# TODO data point labels should be direction and strength (e.g.'gentle SSE')
# TODO data point labels should be greyed out and not overlap each other

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
        # rotated_marker._transform = rotated_marker.get_transform().rotate_deg(degrees)
        rotated_marker = rotated_marker.rotated(deg=degrees)
        rotated_marker
        return rotated_marker

    arrow = u'$\u2191$'
    fig, ax = plt.subplots()
    fig.set_figwidth(10)
    ax.plot(x_list, y_list)
    for x, y, dir_val, str_val in data:
        arrow_marker = mpl.markers.MarkerStyle(marker=arrow)
        m = rotate_marker(arrow_marker, dir_val)
        ax.scatter(x, y, marker=m, color=colours[str_val], s=200)
        plt.annotate(str(y), (x, y), textcoords="offset points", xytext=(0,10))
    plt.ylim(0, 40)
    ax.tick_params(axis='x', length=0)
    ax.set_xticklabels('')
    ax.grid(visible=True, which='major', axis='y')
    loc = plticker.MultipleLocator(base=10.0)
    ax.yaxis.set_major_locator(loc)
    fig1 = plt.gcf()
    fig1.savefig('wind.png')
    plt.show()


if __name__ == '__main__':
    load_dotenv(dotenv_path=".env")
    open("report.txt", 'w').close()

    time = [
        1744070400,
        1744074000,
        1744077600,
        1744081200,
        1744084800,
        1744088400,
        1744092000,
        1744095600,
        1744099200,
        1744102800,
        1744106400,
        1744110000,
        1744113600,
        1744117200,
        1744120800,
        1744124400,
        1744128000,
        1744131600,
        1744135200,
        1744138800,
        1744142400,
        1744146000,
        1744149600,
        1744153200
    ]
    speed = [
        9.7,
        5.1,
        5.4,
        5.8,
        6,
        6.4,
        6.8,
        7.2,
        11.5,
        12.6,
        12.6,
        12.4,
        12.2,
        12.1,
        12.4,
        12.4,
        12.4,
        12.8,
        13,
        12.4,
        8.2,
        8.6,
        8.4,
        8]
    direction = [
        129,
        145,
        151,
        156,
        161,
        157,
        153,
        148,
        140,
        131,
        123,
        122,
        121,
        118,
        120,
        122,
        126,
        130,
        135,
        139,
        143,
        148,
        151,
        156
    ]
    colours = ['#F1F2F3', '#d1ef51', '#a5de37', '#48ad00', '#0ec1f2', '#1896eb', '#226be4', '#1950ab']
    cutoffs = [.6, 6.8, 10.7, 15.6, 21, 27, 33.4, 40.4]
    strength = []
    for y in speed:
        for i, knots in enumerate(cutoffs):
            if y < knots:
                strength.append(i)
                break

    data = zip(time, speed, direction, strength)
    draw_graph(data, time, speed)
    #
    # BOM = scrapeBOM()
    # with open('report.txt', 'a') as file:
    #     file.write(f"Moreton Bay Marine Forecast from BOM\n\n")
    #     file.write("\n".join(BOM))
    #     file.write('\n\n\n')
    #
    # apiKey = os.environ.get("API_KEY")
    #
    # today = datetime.date.today()
    # datestring = today.strftime("%a %d %b %Y")
    # day, date, month, year = datestring.split()
    #
    # if day == "wed":
    #     offset = 3
    # if day == "fri":
    #     offset = 1
    # else:
    #     offset = 0
    # startDate = today + datetime.timedelta(offset)
    # jsonContent = get_forecast(startDate, "wind", 2)
    # data = json.loads(jsonContent)
    # days = data['forecasts']['wind']["days"]
    #
    # entries = [e for d in days for e in d['entries']]
    # windSpeeds = [e['speed'] for e in entries]
    # if max(windSpeeds) > 15:
    #     safeCruising = False
    # else:
    #     safeCruising = True
    #
    # with open('report.txt', 'a') as file:
    #     file.write(f"Willy Weather Wind Peel Island Forecast Report on {datestring}:\n\n")
    #     if safeCruising:
    #         file.write("Looks safe to cruise this weekend!\n\n")
    #     for d in days:
    #         dateList = d['dateTime'].split()[0].split("-")
    #         dateObj = datetime.datetime(int(dateList[0]), int(dateList[1]), int(dateList[2]))
    #         file.write(f"{dateObj.strftime('%a %d %b %Y')}\n")
    #         for ent in d['entries']:
    #             timestring = ent['dateTime'][-8:-3]
    #             file.write(f"{timestring} {ent['speed']} knots, {ent['directionText']}\n")
    #         file.write('\n')
    #
    # port = os.environ.get("PORT")  # For SSL
    # smtp_server = os.environ.get("SERVER")
    # sender_email = os.environ.get("EMAIL")  # Enter your address
    # receiver_email = os.environ.get("RECIPIENTS")
    # password = os.environ.get("PASSWORD")
    #
    # textfile = "report.txt"
    # # Open the plain text file whose name is in textfile for reading.
    # with open(textfile) as fp:
    #     # Create a text/plain message
    #     msg = EmailMessage()
    #     msg.set_content(fp.read())
    # msg['Subject'] = 'Weather report'
    # msg['From'] = sender_email
    # msg['To'] = receiver_email
    #
    # context = ssl.create_default_context()
    # with smtplib.SMTP_SSL(smtp_server, port, context=context, timeout=120) as server:
    #     try:
    #         server.login(sender_email, password)
    #         server.send_message(msg, sender_email, receiver_email)
    #         print("Email sent.")
    #     except Exception as e:
    #         print(e)

