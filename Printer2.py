#!/usr/bin/env micropython
'''
This version of Printer adds the feedin and feedout for the paper and speed configuration
Also deleted the touch sensor part cause it's not needed
And uses Micropython instead of python3
Next version should try on external output
'''
from time import sleep

from GCode import GCodeParse
import math, os, time
from ev3dev2.motor import *#Motor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedPercent
from ev3dev2.sensor import INPUT_1
from ev3dev2.sensor.lego import ColorSensor
from ev3dev2.led import Leds
from ev3dev2.sound import Sound
#from ev3dev2.display import Display
from ev3dev2.button import Button

#display = Display()
leds = Leds()
sound = Sound()
button = Button()

class mymotor(Motor):
    def stop(self, stop_command='coast'):
        self.stop_action = stop_command
        self.command = "stop"

    def reset_position(self, value = 0):
        self.stop()
        iter = 1
        while (self.position != 0 and iter < 10):
            iter += 1
            try:
                self.position = value
            except:
                print ("impossible to fix position, attempt",iter-1,"on 10.")
            time.sleep(0.05)

    def rotate_forever(self, speed=480, regulate='on', stop_command='brake'):
        self.stop_action = stop_command
        self.speed_regulation = regulate
        if regulate=='on':
            self.speed_sp = int(speed)
            self.command = 'run-forever'
        else:
            self.duty_cycle_sp = int(speed)
            self.command = 'run-direct'

    def goto_position(self, position, speed=480, up=0, down=0, regulate='on', stop_command='brake', wait=0):
        self.stop_action = stop_command
        self.speed_regulation = regulate
        self.ramp_up_sp,self.ramp_down_sp = up,down
        if regulate=='on':
            self.speed_sp = speed
        else:
            self.duty_cycle_sp = speed
        self.position_sp = position
        sign = math.copysign(1, self.position - position)
        self.command = 'run-to-abs-pos'

        if (wait):
            new_pos = self.position
            nb_same = 0
            while (sign * (new_pos - position) > 5):
                time.sleep(0.05)
                old_pos = new_pos
                new_pos = self.position
                if old_pos == new_pos:
                    nb_same += 1
                else:
                    nb_same = 0
                if nb_same > 10:
                    break
            time.sleep(0.05)
            if (not stop_command == "hold"):
                self.stop()

class Writer():

    def __init__(self, calibrate=True,speedPercent = 1.):
        self.mot_pen    = mymotor(OUTPUT_A)
        self.mot_paper    = mymotor(OUTPUT_B)
        self.mot_lift = mymotor(OUTPUT_C)
        self.speedP = speedPercent
        #self.touch = TouchSensor('in1')
        self.light = ColorSensor('in1')
        


        if (calibrate):
            self.calibrate()
        self.pen_up()
        #self.feedIn()
        

    def exit(self):
        self.mot_lift.stop()
        self.mot_pen.stop()
        self.mot_paper.stop()
        self.feedOut()

        sound.speak('printer stopped')
        quit()

    def pen_up (self, wait=1):
        self.mot_lift.goto_position(120, int(30*self.speedP), regulate = 'off', stop_command='brake', wait = wait)
        if wait:
            time.sleep(0.1)
            
    def pen_down(self, wait=1):
        self.mot_lift.goto_position(-20, int(30*self.speedP), regulate = 'off', stop_command='brake', wait = wait)
        if wait:
            time.sleep(0.1)
    def feedIn(self):
        self.light.MODE_COL_REFLECT = 'COL-REFLECT'
        while(self.light.reflected_light_intensity<=15):
            self.mot_paper.rotate_forever(-100.)
        self.mot_paper.stop(stop_command='hold')
        self.mot_paper.reset_position()
        sound.speak('Feed in complete')
        
    def feedOut(self):
        self.light.MODE_COL_REFLECT = 'COL-REFLECT'
        while(self.light.reflected_light_intensity>=16):
            self.mot_paper.rotate_forever(100)
        self.mot_paper.stop(stop_command='brake')
        

    def button_control_process(self):
        # Create a separate process for button control
        while True:
            if(button.any()):
                if button.enter:
                    # Exit the loop if the enter button is pressed
                    sound.speak('Pen height confirmed')
                    self.mot_lift.reset_position()
                    self.pen_up()
                    break
                elif button.up:
                    # Rotate the motor forward by 5 degrees at a speed of 25
                    self.mot_lift.on_for_degrees(25, 5, brake=True)
                elif button.down:
                    # Rotate the motor backward by 5 degrees at a speed of 25
                    self.mot_lift.on_for_degrees(-25, 5, brake=True)
    def calibrate (self):
        # Equivalent to Z axis calibration
        self.button_control_process()
        # X axis calibration
        # Move to the far right
        self.mot_pen.on_for_degrees(50., 1050, brake=True)
        time.sleep(0.05)
        # Move to the far left
        self.mot_pen.on_for_degrees(50., -1050, brake=True)
        self.mot_pen.reset_position()
        
    # Converts coordinates x,y into motor position
    @staticmethod
    def coordinates_to_motorpos (x, y):
        # mot_pen   (0,1050)    from x  (0,11*8mm) with calculation-adjusted diameter of 28.8mm
        # mot_paper (0,unknown) from y  (0,unknown) with measured diameter of 43mm
        pos1 = x * 3 * 360 / (28.8 * math.pi)
        pos2 = y * 3 * 360 / (43 * math.pi)
        return pos1,pos2

    @staticmethod
    def motorpos_to_coordinates (pos1, pos2):
        x = pos1 * math.pi * 28.8 / (3 * 360)
        y = pos2 * math.pi * 43 / (3 * 360)
        return x,y

    def set_speed_to_coordinates (self,x,y,max_speed,initx=None,inity=None,brake=1.):
        # Current position(in degrees) of motors
        posX, posY = self.mot_pen.position, self.mot_paper.position
        # Current position(in millimeters) of coordinate system
        myx, myy = Writer.motorpos_to_coordinates (posX, posY)
        dist = math.sqrt((myx-x)*(myx-x) + (myy-y)*(myy-y))

        # Setting the accuracy
        if (dist < 1.*self.speedP and brake == 0 ) or dist < .8*self.speedP:
            return 0

        next_posX, next_posY = Writer.coordinates_to_motorpos (x, y)
        speed = max_speed

        slow_down_dist = (max_speed / 21.)
        if (dist <= slow_down_dist):
            speed -= (slow_down_dist-dist)/slow_down_dist * (max_speed-21)/1.

        '''
        slow_down_dist = (max_speed / 20.)
        if (dist < slow_down_dist):
            speed -= (slow_down_dist-dist)/slow_down_dist * (brake * (max_speed-20))/1.
        '''
        distX = (next_posX - posX)
        distY = (next_posY - posY)
        if abs(distX) > abs(distY):
            speedX = speed
            speedY = abs(speedX / distX * distY)
        else:
            speedY = speed
            speedX = abs(speedY / distY * distX)

        self.mot_pen.rotate_forever((math.copysign(speedX, distX)), regulate='off')
        self.mot_paper.rotate_forever((math.copysign(speedY, distY)), regulate='off')
        
        return 1

    def goto_point (self, x,y, brake=1, last_x=None, last_y=None, max_speed=70.):
        max_speed*=self.speedP
        if (last_x == None or last_y == None):
            initposX, initposY = self.mot_pen.position, self.mot_paper.position
            initx, inity = Writer.motorpos_to_coordinates (initposX, initposY)
        else:
            initx, inity = last_x, last_y
        max_speed_ = 20*self.speedP
        while (self.set_speed_to_coordinates (x,y,max_speed_,initx,inity,brake)):
            max_speed_ += 5*self.speedP
            if max_speed_>max_speed:max_speed_=max_speed
            time.sleep(0.0001)
        if brake == 1:
            self.mot_paper.stop(stop_command='hold')
            self.mot_pen.stop(stop_command='hold')
        else:
            self.mot_paper.stop(stop_command='brake')
            self.mot_pen.stop(stop_command='brake')

        
def main():
    wri = Writer(calibrate = True, speedPercent = .75)
    #wri.follow_mouse()
    #wri.pen_up()
    gcode_obj = GCodeParse("./Gcodes/legibility.gcode")
    gcode_dict = gcode_obj.read_one_line()
    while gcode_dict is not None:
        
        print("From code get xyzgs>>", gcode_dict)
        
        # Get the data
        x = gcode_dict.get("x")
        y = gcode_dict.get("y")
        z = gcode_dict.get("z")


        if z is not None:
            print("z", z)
            if z <= 0.:
                wri.pen_down() 
            else:
                wri.pen_up() 
        
        if x is not None and y is not None:
            wri.goto_point(x, y,brake = 0)
            print("x", x, "y", y)

        time.sleep(0.0001)
        
        gcode_dict = gcode_obj.read_one_line()
    wri.exit()
    


if __name__ == '__main__':
    main()
    