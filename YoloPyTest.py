#YoloPyTest.py
import main
import time
import RPi.GPIO as GPIO
#파이썬을 통해 사물인식이 가능한지를 테스트하는 코드로, 프로젝트의 구동과는 무관함
import signal
import cv2
import datetime
import os
import paho.mqtt.client as mqtt
import base64
import sys
import os
# 현재 스크립트의 디렉토리 경로를 얻습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
# 'darknet' 디렉토리를 모듈 검색 경로에 추가합니다.
sys.path.append(os.path.join(current_dir, 'darknet'))
import darknet
import darknet_images

def on_connect(client, userdata, flag, rc):
	client.subscribe("feed", qos = 0) # "led" 토픽으로 구독 신청

def on_message(client, userdata, msg) :
    print("사료급여를 시작합니다")
    start_feeding()

def start_feeding():
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

    # 이미지 탐지
     analyzed_image, detections = darknet_images.image_detection(file_path, network, class_names, class_colors, thresh=0.5)
     print("탐지완료")
     return analyzed_image, detections

def analyze_detections(detections):
    has_full = any("full" in detection[0] for detection in detections)
    has_empty = any("empty" in detection[0] for detection in detections)

    if has_full and not has_empty:
        return "반려동물이 사료를 남겼습니다"
    elif has_empty and not has_full:
        return "반려동물이 사료를 남기지 않았습니다"
    else:
        return "오류가 발생했습니다"


image_directory = "projectImg" #촬영된 이미지를 저장한 디렉토리를 지정
if not os.path.exists(image_directory): #만일 그러한 디렉토리가 존재하지 않는다면 새로 생성한다
	os.makedirs(image_directory)

def handle_exit(signal, frame): # 프로그램 종료 시그널(Ctrl+C)을 처리하는 함수 등록
    print("\nProgram terminated..")
    GPIO.cleanup()  # GPIO 설정 초기화
    main.final() #카메라 해방
    exit(0)	#프로그램 종료
signal.signal(signal.SIGINT, handle_exit)

print("사진찍습니다") #터미널에 출력하고
main.init()
image = main.take_picture()  # 연결된 카메라에서 사진을 촬영하고
filename = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"  # 현재 시간을 문자열로 변환한 이름을 생성한다
file_path = os.path.join(image_directory, filename)  # 경로와 파일명을 지정하여
cv2.imwrite(file_path, image)  # 사진을 저장한다
analyzed_image, detections = detect_image(file_path)# YOLO를 사용한 이미지 분석
analysis_file_path = os.path.join(image_directory, "analyzed_" + filename) #분석된 이미지 파일 경로
cv2.imwrite(analysis_file_path, analyzed_image) #분석된 이미지 저장
analyzed_detection = analyze_detections(detections)
print(analyzed_detection)
print("박스표시된 이미지 저장완료")
