const int LED = 9; // LED PIN
const int BUTTON = 7;

int val = 0;
int old_val = 0; // storage

int state = 0;

unsigned long start_time = 0;
unsigned long change_bright_thresh = 250;
int bright_change_speed = 10; // higher is slower in this case because it's how much time (ms) between increments
int brightness = 128; 

void setup(){
	pinMode(LED, OUTPUT);
	pinMode(BUTTON, INPUT);
}

void loop(){

	val = digitalRead(BUTTON);

	if((val == HIGH) && (old_val == LOW)) {
		state = 1 - state; // swap it

		start_time = millis();
		delay(10);
	}

	if((val == HIGH) && (old_val == HIGH)) {
		if (state == 1 && (millis()-start_time) > change_bright_thresh){
			brightness++;
			delay(bright_change_speed);

			if (brightness  > 255){
				brightness = 10; // start over
			}
		}
	}

	old_val = val;

	if(state == 1){
		analogWrite(LED,brightness);
	}else{
		analogWrite(LED,0);
	}
}