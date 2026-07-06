import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from gpiozero import LED
from time import sleep
from gpiozero import MCP3008
import requests

#coordinate del mio paese per meteo API
LATITUDE = "45.68"
LONGITUDE = "11.41"

#definizione funzione per prendere misure reali
def get_real_data():
    url=f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,relative_humidity_2m"
    try:
        response = requests.get(url, timeout=5)
        data=response.json()
        
        #data extraction
        realTemp = data["current"]["temperature_2m"]
        realHum = data["current"]["relative_humidity_2m"]
        return realTemp, realHum
    except Exception as e:
        print(f"weather API error: {e}")
        return 0,0

#istanza classe LED
led=LED(4)

#istanza classe MCP3008 sul canale  2 per leggere tensione fotoresistenza
lux_reader = MCP3008(channel=2, differential=False, max_voltage=1.5)

#parametri InfluxDB
myToken="YibU849rnAlse6HjpcnRtmvS-sguB5E23IeNXQg47tsYteVJndEYRknou-C57NLDGGXl-K-GrxytlHxGAI2OPQ=="
myOrg="studenteUniurb"
myBucket="corsoIoT"
myHost="ProgettoN503"
myUrl="http://informatica-iot.freeddns.org:8086/"

#parametri MQTT locale
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sensori_ESP_merlo503"

#istanza InfluxDB e configurazione API di scrittura SINCRONA
client = InfluxDBClient(url=myUrl, token=myToken, org=myOrg)
write_api=client.write_api(write_options=SYNCHRONOUS)

#funzione di connessione MQTT e subscribe
def on_connect(client, userdata, flags, rc):
    if rc==0:
        print("--- local MQTT broker synched\n")
        client.subscribe(MQTT_TOPIC, qos=1)
        print("--- subscribed to topic: " + MQTT_TOPIC + " \n")
        
    else:
        print(f"local broker connection error: {rc}")

#funzione di decode e parsing del messaggio
def on_message(client, userdata, msg):
    
    #led blinks
    led.on()
    sleep(0.05)
    led.off()
    
    #conversione byte a stringa
    payload = msg.payload.decode()
    print(f"Received message: {payload}", flush=True)
    
    #inizializzazione variabili temporanee per parsing
    current_key = ""
    current_value = ""
    value_toggle = False
    
    #inizializzazione variabili dati estratti
    floor = ""
    tempC = None
    hum = None
    lux = round(lux_reader.value*100,1)
    
    #parsing del payload ricevuto
    
    for payload_char in payload:
       
        if payload_char == ':':
            value_toggle = True
            
        elif payload_char == ';':
            if current_key == "P":
                floor = current_value
            elif current_key == "T":
                tempC = float(current_value)
            elif current_key == "H":
                hum = float(current_value)
        
            #reset current_key, current_value e value_toggle
            current_key = ""
            current_value = ""
            value_toggle = False
        
        else:
            if not value_toggle:
                current_key += payload_char
            else:
                current_value += payload_char
                
    #fine parsing del payload
    
    #tentativo invio dati a InfluxDB
    try:
        if tempC is not None and hum is not None:
            #stampa per debug valori parsati
            print(f"Parsed data: floor= {floor} , tempC= {tempC} , hum= {hum}")
            print(f"Reading Luminosity ... lux= {lux}")
            #creazione dei points da inviare a InfluxDB
            point1 = Point(myHost).tag("location", "Marano").tag("floor", floor).field("temperatura", tempC)
            point2 = Point(myHost).tag("location", "Marano").tag("floor", floor).field("umidità", hum)
            point3 = Point(myHost).tag("location", "Marano").tag("floor", floor).field("luminosità", lux)
            #creazione points weather API
            temp_vera, hum_vera = get_real_data()
            print(f"readin real time data: real_temp= {temp_vera} , real_hum= {hum_vera}")
            point4 = Point(myHost).tag("location", "Marano").tag("floor", "outside").field("temperatura_API", temp_vera)
            point5 = Point(myHost).tag("location", "Marano").tag("floor", "outside").field("umidità_API", hum_vera)
            
            #scrittura su DB
            write_api.write(bucket=myBucket, record =[point1, point2, point3, point4, point5])
            print("Sent data to InfluxDB\n")
        else:
            print("Incomplete data / parsing error")
    
    except Exception as e:
        print(f"Error during InfluxDB write")
            
#connessione MQTT
client_mqtt = mqtt.Client()
client_mqtt.on_connect = on_connect
client_mqtt.on_message = on_message

client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)

client_mqtt.loop_forever()  
            
            
    