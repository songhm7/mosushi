#mqttPub.py
import main
import time
import RPi.GPIO as GPIO
import signal
import cv2
import datetime
import os
import paho.mqtt.client as mqtt
import base64
import sys
import os
import threading

current_dir = os.path.dirname(os.path.abspath(__file__))# 현재 스크립트의 디렉토리 경로를 얻는다
sys.path.append(os.path.join(current_dir, 'darknet'))# 'darknet' 디렉토리를 모듈 검색 경로에 추가
import darknet
import darknet_images

threshold = 20  # 거리 임계값 (cm)
counter = 0  # 거리가 임계값 미만인 상태를 추적하는 카운터
min_counts = 10  # 최소 지속 카운트 (10초에 해당)

main.init()	#카메라,초음파 초기화
main.setTrigEcho(20, 16)	# 초음파 핀 지정
broker_ip = "localhost"	#브로커 아이피를 로컬호스트로 지정
topic = "petStatus"	#텍스트를 전송할 토픽명을 petStatus로 지정

def on_connect(client, userdata, flag, rc):
	client.subscribe("feed", qos = 0) # "led" 토픽으로 구독 신청

def on_message(client, userdata, msg) : #라즈베리파이에 사료급여 명령이 전송되면 사료급여기가 가동
    print("사료급여를 시작합니다")
    start_feeding()

def start_feeding(): #LED를 3번 점멸하는것으로 실제 사료급여기를 대신
    main.controlLED(1)
    time.sleep(1)
    main.controlLED(0)
    time.sleep(1)
    main.controlLED(1)
    time.sleep(1)
    main.controlLED(0)
    time.sleep(1)
    main.controlLED(1)
    time.sleep(1)
    main.controlLED(0)

def detect_image(file_path):
     #YOLO 모델과 관련된 파일 경로 설정
     config_path = "darknet/cfg/yolov4-tiny-custom.cfg"
     weight_path = "darknet/dogFood.weights"
     meta_path = "darknet/cfg/dogFood.data"
     
    # YOLO 모델 로드
     network, class_names, class_colors = darknet.load_network(
        config_path,
        meta_path,
        weight_path,
        batch_size=1
    )

    # 이미지를 분석한다. darknet_images.image_detecton함수의 리턴값은 탐지박스가 추가된 이미지와 탐지된 물체들의 배열
     analyzed_image, detections = darknet_images.image_detection(file_path, network, class_names, class_colors, thresh=0.5)
     return analyzed_image, detections

def analyze_detections(detections): #탐지된 물체들의 배열을 해석해 자연어로 바꿔주는 함수
    has_full = any("full" in detection[0] for detection in detections)
    has_empty = any("empty" in detection[0] for detection in detections)

    if has_full and not has_empty:
        return "반려동물이 사료를 남겼습니다"
    elif has_empty and not has_full:
        return "반려동물이 사료를 남기지 않았습니다"
    else:
        return "밥그릇이 탐지되지 않았습니다"
    
#별도 스레드에서 비동기적으로 실행되는함수. 이미지를 분석하는데 시간이 오래 걸리기 때문에 따로 분리했다.
def process_image_async(file_path): #파라미터로 분석할 이미지의 경로를 받아서
    def process(): #
        analyzed_image, detections = detect_image(file_path) #박스붙은 이미지와 탐지된 물체 배열을 변수에 저장
        analysis_file_path = os.path.join(image_directory, "analyzed_" + filename)
        cv2.imwrite(analysis_file_path, analyzed_image) #박스붙은 이미지를 파일시스템에 저장한다
        message = analyze_detections(detections) #탐지된 물체 배열의 해석 결과를 자연어로 바꾸어 변수에 저장
        with open(analysis_file_path, "rb") as image_file: #저장한 박스붙은 이미지를 base64형태로 mqtt를 통해 전송
            analyzed_image_data = image_file.read()
            analyzed_image_base64 = base64.b64encode(analyzed_image_data)
            client.publish("image_topic", payload=analyzed_image_base64, qos=0)
        client.publish("detections", message, qos=0) #해석 결과를 mqtt를 통해 전송
    
    thread = threading.Thread(target=process)
    thread.start()

client = mqtt.Client()	# mqtt 클라이언트를 초기화
client.connect(broker_ip, 1883)	#로컬호스트의 1883포트로 연결
client.loop_start()	#루프 스타트
client.on_connect = on_connect
client.on_message = on_message


image_directory = "projectImg" #촬영된 이미지를 저장한 디렉토리를 지정
if not os.path.exists(image_directory): #만일 그러한 디렉토리가 존재하지 않는다면 새로 생성한다
	os.makedirs(image_directory)

def handle_exit(signal, frame): # 프로그램 종료 시그널(Ctrl+C)을 처리하는 함수 등록
    print("\nProgram terminated..")
    GPIO.cleanup()  # GPIO 설정 초기화
    main.final() #카메라 해방
    exit(0)	#프로그램 종료
signal.signal(signal.SIGINT, handle_exit)


     
while(True):  # 무한루프 시작
    distance = main.measureDistance()  # 초음파탐지기로 거리를 재어 distance 변수에 저장한다
    time.sleep(1.0)  # 간격을 1초로 지정

    if distance < threshold: #20cm 이내에 물체가 감지되면 반려동물이 식사중이라고 판단
        counter += 1  #카운터 증가
        print("반려동물이 식사중입니다") #터미널에 출력하고
        client.publish(topic, "반려동물이 식사중입니다", qos=0)  # mqtt를 통해 같은 메시지를 전송한다
    else: #20이내에 물체가 감지되지 않는다면
        if counter >= min_counts: # 식사시간이 10초 이상이었다면 식사가 끝난것으로 판단
            print("반려동물의 식사가 끝났습니다") #터미널에 출력하고
            client.publish(topic, "반려동물이 식사를 끝냈습니다.", qos=0)  # mqtt를 통해 메시지를 전송한다
            client.publish(topic, "관찰을 끝내고 이미지를 분석합니다.", qos=0)  # mqtt를 통해 메시지를 전송한다
            image = main.take_picture()  # 연결된 카메라에서 사진을 촬영하고
            filename = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"  # 현재 시간을 문자열로 변환한 이름을 생성한다
            file_path = os.path.join(image_directory, filename)  # 경로와 파일명을 지정하여
            cv2.imwrite(file_path, image)  # 사진을 저장한다
            process_image_async(file_path) # 비동기적으로 실행되는 사진처리함수
        counter = 0 #감지된 거리가 20cm 이상이었다면 카운터를 리셋
    msg = str(distance)
    print(msg)  # 거리를 현재 터미널에 출력
