import os
import subprocess as sub
import sys
import time
from datetime import datetime, timedelta

import PIL
import cv2
import numpy
from PIL import Image
from pygame import mixer

adb = '/home/jester/Android/Sdk/platform-tools/adb'
if not os.path.isfile(adb):
    adb = '/home/jasonk/Android/Sdk/platform-tools/adb'
if not os.path.isfile(adb):
    adb = '/bin/adb'

device = '192.168.1.29:5555'


def adb_back():
    sub.Popen(
        [adb, '-s', device, 'shell', 'input keyevent 4'],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()


def get_device_size():
    stdout, stderr = sub.Popen(
        [adb, '-s', device, 'shell', 'wm size'],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()
    return int(stdout.replace("Physical size: ", "").replace("\n", "").split("x")[0]), int(
        stdout.replace("Physical size: ", "").replace("\n", "").split("x")[1])


def tap(x, y):
    sub.Popen(
        [adb, '-s', device, 'shell', 'input tap %s %s' % (x, y)],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()


def swipe(x1, y1, direction):
    x2 = x1
    y2 = y1
    if direction == 'left' or direction == 'w':
        x2 -= 640
    elif direction == 'right' or direction == 'e':
        x2 += 640
    elif direction == 'up' or direction == 'n':
        y2 -= 640
    elif direction == 'down' or direction == 's':
        y2 += 640
    elif direction == 'nw':
        x2 -= 640
        y2 -= 640
    elif direction == 'ne':
        x2 += 640
        y2 -= 640
    elif direction == 'sw':
        x2 -= 640
        y2 += 640
    elif direction == 'se':
        x2 += 640
        y2 += 640

    sub.Popen(
        [adb, '-s', device, 'shell', 'input', 'swipe %s %s %s %s %s' % (x1, y1, x2, y2, 200)],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()


def get_screen():
    sub.Popen(
        [adb, '-s', device, 'shell', 'screencap /sdcard/screen.png'],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()
    sub.Popen(
        [adb, '-s', device, 'pull', '/sdcard/screen.png'],
        stdin=sub.PIPE, stdout=sub.PIPE, stderr=sub.PIPE
    ).communicate()

    desired_width = 300
    img = Image.open('screen.png')
    hsize = int((float(img.size[1]) * float(desired_width / float(img.size[0]))))
    img = img.resize((desired_width, hsize), PIL.Image.ANTIALIAS)
    img.save('scaled_screen.png')


def get_unscaled_xy(x, y):
    w, h = get_device_size()
    scale = 1 / float(300 / float(w))
    return ((x + 10) * scale), ((y + 10) * scale)


def find_image(image):
    img_rgb = cv2.imread('scaled_screen.png')
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(image, 0)
    w, h = template.shape[::-1]
    template_match = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.90
    template_location = numpy.where(template_match >= threshold)

    x = None
    y = None

    total_match = len(template_location[0])

    if total_match > 0:
        for pt in zip(*template_location[::-1]):
            cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)
            x = pt[0]
            y = pt[1]

        cv2.imwrite('matched_image.png', img_rgb)

    return total_match, x, y


def move_directions(directions, battle_free=False):
    width, height = get_device_size()
    battle = False
    step = 0
    chances = 0
    while step < len(directions):
        get_screen()

        match, x, y = find_image('back.png')
        if match > 0:
            print("Leaving menu!")
            adb_back()

        match, x, y = find_image('world_menu.png')
        if not battle and match > 0:
            if chances < 3:
                print("Moving %s... step: %s chance: %s" % (directions[step], step, chances))
                swipe(width / 2, height / 4, directions[step])
                if battle_free:
                    time.sleep(6)
                    chances = 10
                else:
                    chances += 1
            else:
                chances = 0
                step += 1

        match, x, y = find_image('battle_menu.png')
        if match > 0:
            print("Currently in battle...")
            battle = True
            chances = 0
            match, x, y = find_image('battle_results.png')
            if match > 0:
                print("Battle Done!")
                battle = False
                tap(width / 2, height / 2)
                time.sleep(1)
            else:
                match, x, y = find_image('auto.png')
                if match == 0:
                    print("Starting auto combat")
                    tap(200, 2400)


def farm():
    last_battle = datetime.now()
    width, height = get_device_size()
    direction = "left"
    battle = False
    while True:
        get_screen()

        match, x, y = find_image('back.png')
        if match > 0:
            print("Leaving menu!")
            adb_back()

        match, x, y = find_image('world_menu.png')
        if not battle and match > 0:
            if datetime.now() - timedelta(seconds=60) > last_battle:
                print("It's been a while since your last battle... Let's check our progress")

                # Click on the menu
                ux, uy = get_unscaled_xy(x, y)
                tap(ux, uy)
                time.sleep(1)

                # Grab Screen
                get_screen()

                # Are we half way done?
                match, x, y = find_image('halfgil.png')
                if match > 0:
                    print("time to go to next zone!")
                    break

                # Are we all the way done?
                match, x, y = find_image('maxgil.png')
                if match > 0:
                    print("Done!")
                    break

                match, x, y = find_image('back.png')
                if match > 0:
                    print("Leaving menu!")
                    adb_back()

                last_battle = datetime.now()
            else:
                print("In world, lets walk around...")
                if direction == "left":
                    direction = "right"
                else:
                    direction = "left"
                swipe(width / 2, height / 4, direction)

        match, x, y = find_image('battle_menu.png')
        if match > 0:
            print("Currently in battle...")
            battle = True
            last_battle = datetime.now()
            match, x, y = find_image('battle_results.png')
            if match > 0:
                print("Battle Done!")
                battle = False
                tap(width / 2, height / 2)
                time.sleep(1)
            else:
                match, x, y = find_image('auto_unclicked.png')
                if match > 0:
                    print("Starting auto combat")
                    ux, uy = get_unscaled_xy(x, y)
                    tap(ux, uy)


if __name__ == '__main__':
    mixer.init()
    mixer.music.load('reee.ogg')
    print("Starting")
    if sys.argv[1] == "zone1":
        move_directions(['s', 'nw', 'ne', 'w', 'sw', 'n'])
        farm()
        move_directions(['w', 'w', 'se', 'se', 'n', 'nw', 'sw'], True)
        move_directions(['w', 's', 'e', 's', 'sw', 'nw', 'sw', 'n', 'e', 'nw', 'e', 'n'])
        farm()
        move_directions(['w'], True)
        mixer.music.play()
        time.sleep(5)
        sys.exit(0)
    elif sys.argv[1] == "zone1f":
        farm()
        move_directions(['w', 'w', 'se', 'se', 'n', 'nw', 'sw'], True)
        move_directions(['w', 's', 'e', 's', 'sw', 'nw', 'sw', 'n', 'e', 'nw', 'e', 'n'])
        farm()
        move_directions(['w'], True)
        mixer.music.play()
        time.sleep(5)
        sys.exit(0)
    elif sys.argv[1] == "zone2":
        move_directions(['w', 's', 'e', 's', 'sw', 'nw', 'sw', 'n', 'e', 'nw', 'e', 'n'])
        farm()
        move_directions(['w'], True)
        mixer.music.play()
        time.sleep(5)
        sys.exit(0)
    elif sys.argv[1] == "zone2f":
        farm()
        move_directions(['w'], True)
        mixer.music.play()
        time.sleep(5)
        sys.exit(0)
    elif sys.argv[1] == "screen":
        get_screen()
    elif sys.argv[1] == "farm":
        farm()
