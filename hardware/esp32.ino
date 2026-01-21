#include <WiFi.h>
#include <WiFiClientSecure.h>

const char* ssid = "ShahNet";
const char* password = "jjjainam";

// Gemini API key
const char* gemini_api_key = "AIzaSyD2xLji9JTlobcrjDX7iM4B7TDs0vfEN7M";

const char* host = "generativelanguage.googleapis.com";
const int httpsPort = 443;

WiFiClientSecure client;

void setup() {
  Serial.begin(115200);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());

  client.setInsecure();  // OK for labs / learning

  sendPrompt("Explain ESP32 WiFi in one sentence.");
}

void loop() {
  // nothing
}

void sendPrompt(String prompt) {
  if (!client.connect(host, httpsPort)) {
    Serial.println("Connection to Gemini failed");
    return;
  }

  String payload =
    "{"
      "\"contents\": [{"
        "\"parts\": [{"
          "\"text\": \"" + prompt + "\""
        "}]"
      "}]"
    "}";

  // ✅ UPDATED MODEL NAME
  String url = String("/v1beta/models/gemini-1.5-flash:generateContent?key=") + gemini_api_key;

  client.println("POST " + url + " HTTP/1.1");
  client.println("Host: " + String(host));
  client.println("Content-Type: application/json");
  client.print("Content-Length: ");
  client.println(payload.length());
  client.println();
  client.println(payload);

  Serial.println("\n--- Gemini Response ---");

  // Skip HTTP headers
  while (client.connected()) {
    String line = client.readStringUntil('\n');
    if (line == "\r") break;
  }

  String response = client.readString();
  Serial.println(response);
}
