import network
import ntptime
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
from dht import DHT11
import time

# Wi-Fi configuration
SSID = ''
PASSWORD = ''

# Set up I2C and OLED
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Set up DHT sensor
DHT_pin = Pin(2, Pin.OUT, Pin.PULL_DOWN)
dht11 = DHT11(DHT_pin)

# Initialize global variables
text1 = "Time: --:--:--"
text2 = "Date: ----.--.--"
base_time = (0, 0, 0)  # (hour, minute, second)

# Connect to Wi-Fi
def connect_wifi():
    oled.fill(0)
    oled.text('Connecting...', 0, 0)
    oled.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    while not wlan.isconnected():
        time.sleep(1)

    oled.fill(0)
    oled.text('Connected!', 0, 0)
    oled.show()
    time.sleep(2)  # Show connected message for a short time

# Fetch and adjust time
def fetch_time():
    global text1, text2, base_time
    for attempt in range(5):  # Try 5 times
        try:
            ntptime.host = 'pool.ntp.org'  # Use a different NTP server
            ntptime.settime()  # Sync time with NTP server
            break  # Exit loop on success
        except Exception as e:
            display_error('Error fetching time:', str(e))
            time.sleep(2)  # Wait before retrying
    else:
        print("Failed to fetch time after multiple attempts.")

    # Get the current UTC time
    t = time.localtime()
    
    # Adjust for Tallinn time (UTC+2 or UTC+3 depending on daylight saving time)
    month, day = t[1], t[2]
    if (month > 3 and month < 10) or (month == 3 and day >= 25) or (month == 10 and day < 31):
        offset = 3  # EEST (UTC+3)
    else:
        offset = 2  # EET (UTC+2)

    adjusted_hour = (t[3] + offset) % 24  # Adjust the hour for Tallinn time

    # Store the base time
    base_time = (adjusted_hour, t[4], t[5])  # (hour, minute, second)
    text2 = 'Date:%04d.%02d.%02d' % (t[0], t[1], t[2])

def read_sensor_data():
    try:
        time.sleep(1)  # Wait before reading to allow stabilization
        temperature = dht11.temperature
        humidity = dht11.humidity
        return temperature, humidity
    except Exception as e:
        display_error('DHT11 read error:', str(e))
        return None, None

def display_error(message, error_details):
    oled.fill(0)
    oled.text(message, 0, 0)
    oled.text(error_details, 0, 10)
    oled.show()
    time.sleep(5)  # Show error message for a short time
    print(f"{message} {error_details}")

if __name__ == '__main__':
    try:
        connect_wifi()  # Connect to Wi-Fi
        fetch_time()    # Fetch initial date and time
        
        last_second_update = time.time()  # Track the last second update
        last_temp_read = time.time()  # Track the last temperature read
        temperature = None
        humidity = None

        while True:
            current_time = time.time()

            # Update seconds and display every second
            if current_time - last_second_update >= 1:
                last_second_update = current_time
                hour, minute, second = base_time
                
                # Increment seconds
                second += 1
                if second >= 60:
                    second = 0
                    minute += 1
                    if minute >= 60:
                        minute = 0
                        hour += 1
                        if hour >= 24:
                            hour = 0

                base_time = (hour, minute, second)
                text1 = 'Time:%02d:%02d:%02d' % base_time

                # Update the display immediately after updating time
                oled.fill(0)
                oled.text(text2, 0, 0)  # Date
                oled.text(text1, 0, 10)  # Time

                # Add an empty line
                oled.text("", 0, 20)  # Empty line

                # Read temperature and humidity every 2 seconds
                if current_time - last_temp_read >= 2:
                    temperature, humidity = read_sensor_data()
                    last_temp_read = current_time

                # Display temperature and humidity if available
                if temperature is not None:
                    oled.text("Temp: {}C".format(temperature), 0, 30)
                if humidity is not None:
                    oled.text("Humidity: {}%".format(humidity), 0, 40)

                oled.show()

            # Update time every minute
            if int(current_time) % 60 == 0:
                fetch_time()

            time.sleep(0.1)  # Short sleep to avoid busy waiting
    except Exception as e:
        display_error('Startup error:', str(e))
