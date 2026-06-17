
from playsound3 import playsound
import time


sound_object = None

if __name__ == "__main__":
    # global sound_object
    
    sound_object = playsound('delo-sdelano.mp3', block=False)
    # sound_object
    for i in range(10):
        print(i)
        time.sleep(0.2)