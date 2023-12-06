# main.py
import sys
import time
import cv2
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
trig = 20 # GPIO20
echo = 16 # GPIO16
led = 6 #GPIO6
camera = None

GPIO.setup(led, GPIO.OUT) # GPIO6 핀을 출력으로 지정
GPIO.setup(trig, GPIO.OUT)
GPIO.setup(echo, GPIO.IN)

def init(camera_id=0, width=640, height=480, buffer_size=1):
	global camera
	camera = cv2.VideoCapture(camera_id, cv2.CAP_V4L)
	camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
	camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
	camera.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)

# LED를 켜고 끄는 함수
def controlLED(on_off): # led 번호의 핀에 on_off(0/1) 값 출력하는 함수
	GPIO.output(led, on_off)

def take_picture(most_recent=False):
	global camera
	# most_recent가 True이면 버퍼에 저장되어 있는 프레임을 전부 버리도록 한다.
	len = 0 if most_recent == False else camera.get(cv2.CAP_PROP_BUFFERSIZE)
	while(len>0):
		camera.grab()	#버퍼에 저장되어 있는 프레임을 버린다.
		len -= 1
	success, image = camera.read()
	if not success:
		return None

	return image

def setTrigEcho(ltrig=20, lecho=16):
	global trig, echo
	trig = ltrig
	echo = lecho
	GPIO.setup(trig, GPIO.OUT)
	GPIO.setup(echo, GPIO.IN)
	
def measureDistance():
	GPIO.output(trig, 1) # tr
	GPIO.output(trig, 0) # trig 핀 신호 High->Low. 초음파 발사 지시
	while(GPIO.input(echo) == 0): # echo 핀 값이 0이 될때까지 루프
		pass
	# echo 핀 값이 1이면 초음파가 발사되었음
	pulse_start = time.time() #초음파 발사 시간 기록
	while(GPIO.input(echo) == 1) : #echo 핀 값이 0이 될때까지 루프
		pass
	# echo 핀 값이 0이 되면 초음파 수신하였음
	pulse_end = time.time() #초음파가 되돌아 온 시간 기록
	pulse_duration = pulse_end - pulse_start # 경과 시간 계산
	return pulse_duration*340*100/2 # 거리 계산하여 리턴(단위 cm)

def final():
	global camera
	if camera != None:
		camera.release()
	camera = None
	
if __name__ == "__main__":
	init()
	setTrigEcho()
	while True:
		distance = measureDistance()
		time.sleep(0.5) # 0.5초 간격으로 거리 측정
		print("물체와의 거리는 %fcm 입니다." %distance)
		pass
