// Define the pins connected to the Cytron Motor Driver
const int DIR_PIN = 7;  // Direction Pin - MOVED to pin 7 to free up pin 8
const int PWM_PIN = 9;  // PWM Pin (must be a PWM-capable pin)

// Define the pin for the brake status LED.
const int LED_PIN = 8; // Using digital pin 8 for the brake status LED

// Define the PWM value for braking. 255 is full stop/brake.
const int BRAKE_SPEED = 255;
// Define the PWM value when brakes are released. 0 is coast/stop.
const int RELEASE_SPEED = 0;

void setup() {
  // Initialize serial communication at 9600 bits per second:
  Serial.begin(9600);
  
  // Set the motor control pins as outputs
  pinMode(DIR_PIN, OUTPUT);
  pinMode(PWM_PIN, OUTPUT);
  
  // Set the LED pin as an output
  pinMode(LED_PIN, OUTPUT);
  
  // Start with the brakes released and the status LED OFF
  digitalWrite(DIR_PIN, LOW);
  analogWrite(PWM_PIN, RELEASE_SPEED);
  digitalWrite(LED_PIN, LOW); // Ensure LED is off at startup
  
  // Wait a moment for the serial connection to establish
  delay(2000); 
  
  // Send an 'A' (Acknowledge) signal to Python to confirm it's ready
  Serial.write('A');
}

void loop() {
  // Check if data is available to read from the serial port
  if (Serial.available() > 0) {
    // Read the incoming byte
    char command = Serial.read();

    // Check the command received from the Python script
    if (command == 'B') {
      // Apply the brakes: Set PWM to max value
      digitalWrite(DIR_PIN, LOW);
      analogWrite(PWM_PIN, BRAKE_SPEED);
      
      // Turn the status LED ON to indicate brakes are active
      digitalWrite(LED_PIN, HIGH); 
      Serial.println("Command Received: Brake ON");
      
    } else if (command == 'R') {
      // Release the brakes: Set PWM to 0
      digitalWrite(DIR_PIN, LOW);
      analogWrite(PWM_PIN, RELEASE_SPEED);
      
      // Turn the status LED OFF to indicate brakes are released
      digitalWrite(LED_PIN, LOW);
      Serial.println("Command Received: Brake OFF");

    } else if (command == 'P') {
      // 'P' is a Ping from Python to check the connection.
      // We don't change the LED state for a ping.
      Serial.println("Ping received from Python.");
    }
  }
}
