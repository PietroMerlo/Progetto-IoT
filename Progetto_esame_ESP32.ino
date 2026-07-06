#include <ArduinoMqttClient.h>
#include <WiFi.h>
#include <DHT.h>

//codice client univoco
char clientID[] = "esp99";

//definizione costanti per connessione wifi
char WIFI_SSID[] = "TIM FWA-G3R7";
char WIFI_PASSWORD[] = "39gvma43LxX6";

//configurazione MQTT broker
const char broker[] = "192.168.1.111";
int port = 1883;
const char topic[] = "sensori_ESP_merlo503";

//configurazione con IP statico
/*IPAddress local_IP(10,42,0,50);
IPAddress gateway(10,42,0,1);
IPAddress subnet(255,255,255,0);*/

//configurazione chip DHT e LED
#define DHTPIN 25
#define DHTTYPE DHT11
const int fotores = 39;
const int led = 32;

//istanze sensore DHT, client wifi e MQTT
DHT dht(DHTPIN, DHTTYPE);
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

//variabili per le misure
double tempC = 0.0;
double hum = 0.0;


void setup() {
  // put your setup code here, to run once:

  //start timer esecuzione
  unsigned long startTime = millis();

  //setup iniziale
  pinMode(led, OUTPUT);
  Serial.begin(115200);
  while(!Serial){ ; }
  Serial.println("\n--- ESP32 awake ---");
  dht.begin();

  //connessione wifi
  WiFi.mode(WIFI_STA);
  Serial.print("\nAttempting connection to WPA SSID: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long wifiTimeoutStart = millis();
  while(WiFi.status() != WL_CONNECTED){
    Serial.print(":");
    delay(500);
    if(millis() - wifiTimeoutStart > 15000){
      Serial.println("\nConnection unsuccesfull, took too long\n");
      unsigned long partial_elapsedTime_sec = (millis() - startTime) / 1000;
      long sleep_time_sec = 300-partial_elapsedTime_sec;
      if (sleep_time_sec < 0){sleep_time_sec = 300;}
      go_to_sleep(sleep_time_sec);

    }
  }
  Serial.println("\nWPA connection succesfull!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  //connessione MQTT
  mqttClient.setId(clientID);
  mqttClient.setCleanSession(true);
  //prova errorcode-1
  //mqttClient.setProtocolVersion(MqttClient::MQTT_3_1_1);
  //fine prova
  Serial.print("\nAttempting connection to MQTT broker: ");
  Serial.println(broker);

 


  if(!mqttClient.connect(broker,port)){
    Serial.print("MQTT connection failed! Error code=");
    Serial.println(mqttClient.connectError());
    unsigned long partial_elapsedTime_sec = (millis() - startTime) / 1000;
    long sleep_time_sec = 300-partial_elapsedTime_sec;
    if (sleep_time_sec < 0){sleep_time_sec = 300;}
    go_to_sleep(sleep_time_sec);
  }
  Serial.println("MQTT broker connection succesfull!");

  //lettura sensori
  Serial.println("\nReading from sensors...");
  tempC = dht.readTemperature();
  hum = dht.readHumidity();

  //debug valori letti
  Serial.println("temperature= " + String(tempC) + "°C");
  Serial.println("humidity= " + String(hum) + "%");

  //costruzione stringa da pubblicare
  String message = "P:PT;T:" + String(tempC,1) + ";H:" + String(hum,1) + ";";

  //debug e invio messaggio
  Serial.print("\nSending message to topic: ");
  Serial.println(topic);
  Serial.println("Payload: " + message);

  mqttClient.beginMessage(topic, false, 1);
  mqttClient.print(message);
  mqttClient.endMessage();

  //led blink
  digitalWrite(led, HIGH);
  delay(50);
  digitalWrite(led, LOW);

  //fine connessione e deepsleep
  Serial.println("Data published succesfully!");

  //calcolo tempo impiegato
  unsigned long elapsedTime_sec = (millis() - startTime) / 1000;
  Serial.print("\nElapsed time: ");
  Serial.print(elapsedTime_sec);
  Serial.println(" s");
  long sleep_time_sec = 300-elapsedTime_sec;


  Serial.print("\nDisconnecting and going to sleep");
  WiFi.disconnect();
  delay(10);
  go_to_sleep(sleep_time_sec);

}

void loop() {
  // put your main code here, to run repeatedly:

}

void go_to_sleep(long sleep_time){
  Serial.print("\ngoing to sleep for ");
  Serial.print(sleep_time);
  Serial.println(" seconds...");
  Serial.flush();
  ESP.deepSleep((sleep_time) * 1e6);
}