import time
import rtc
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import PWMOut
import adafruit_rgbled
import adafruit_requests as requests
import adafruit_ntp
from adafruit_datetime import datetime
from APRS import APRS
import config

# our version
VERSION = "RF.Guru_APRSGateway 0.1" 

print(f"{config.call} -=- {VERSION}\n")

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

esp32_cs = DigitalInOut(board.GP17)
esp32_ready = DigitalInOut(board.GP14)
esp32_reset = DigitalInOut(board.GP13)

spi = busio.SPI(board.GP18, board.GP19, board.GP16)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

RED_LED = PWMOut.PWMOut(esp, 25)
GREEN_LED = PWMOut.PWMOut(esp, 26)
BLUE_LED = PWMOut.PWMOut(esp, 27)
status_light = adafruit_rgbled.RGBLED(RED_LED, BLUE_LED, GREEN_LED)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
      print("ESP32 found and in idle mode")
print("Firmware vers.", esp.firmware_version)
print("MAC addr:", [hex(i) for i in esp.MAC_address])

## Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected!")
  
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)

# Initialize a requests object with a socket and esp32spi interface
socket.set_interface(esp)
requests.set_socket(socket, esp)

now_utc = None
while now_utc is None:
    try:
        now_utc = time.localtime(esp.get_time()[0])
    except OSError:
        pass
rtc.RTC().datetime = now_utc

# SEND iGate Postition
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(10)
socketaddr = socket.getaddrinfo(config.aprs_host, config.aprs_port)[0][4]
s.connect(socketaddr)

stamp = datetime.now()
aprs = APRS()
pos = aprs.makePosition(config.latitude, config.longitude, -1, -1, config.symbol)
altitude = "/A={:06d}".format(int(config.altitude*3.2808399))
comment = config.comment + altitude
now = stamp.timetuple()
ts = aprs.makeTimestamp('z',now.tm_mday,now.tm_hour,now.tm_min,now.tm_sec)
message = f'user {config.call} pass {config.passcode} vers {VERSION}\n'
s.send(bytes(message, 'utf-8'))
message = f'{config.call}>APDW16,TCPIP*:@{ts}{pos}{comment}\n'
s.send(bytes(message, 'utf-8'))
print(f"{stamp}: [{config.call}] iGatePossition: {message}", end="")

while True:
    time.sleep(1)
