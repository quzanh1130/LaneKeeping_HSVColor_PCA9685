import cv2
import numpy as np
import logging
import math
import datetime
import sys
import matplotlib.pyplot as plt
from servor import servo_Class
from utils import map_range, clamp
import time


_SHOW_IMAGE = False


############################
# Frame processing steps
############################
def detect_lane(frame):
    logging.debug('detecting lane lines...')

    edges = detect_edges(frame)
    # show_image('edges', edges)

    cropped_edges = region_of_interest(edges)
    # show_image('edges cropped', cropped_edges)
    # imgplot = plt.imshow(cropped_edges)
    # plt.show()
    # plt.show()

    line_segments = detect_line_segments(cropped_edges)
    # print(line_segments)
    line_segment_image = display_lines(frame, line_segments)
    # show_image("line segments", line_segment_image)
    
    # print(line_segments.shape)
    # imgplot = plt.imshow(line_segment_image)
    # plt.show()
    # plt.show()

    lane_lines = average_slope_intercept(frame, line_segments)
    lane_lines_image = display_lines(frame, lane_lines)
    # show_image("lane lines", lane_lines_image)
    # imgplot = plt.imshow(lane_lines_image)
    # plt.show()
    # plt.show()

    return lane_lines, lane_lines_image

def detect_edges(frame):
    # filter for blue lane lines
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # show_image("hsv", hsv)
    # imgplot = plt.imshow(hsv)
    # plt.show()

    # map lon
    # lower_white = np.array([75, 29, 0])
    # upper_white = np.array([179, 255, 255])

    # map nho it sang
    # lower_white = np.array([0, 0, 56])
    # upper_white = np.array([66, 255, 252])
    # map nho loa sang
    lower_white = np.array([0, 96, 0])
    upper_white = np.array([17, 255, 255])

    # map lon
    # lower_white = np.array([0, 46, 66])
    # upper_white = np.array([13, 255, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)
    # show_image("blue mask", mask)
    # imgplot = plt.imshow(mask)
    # plt.show()
    # detect edges
    edges = cv2.Canny(mask, 200, 400)
    # imgplot = plt.imshow(edges)
    # plt.show()
    # plt.show()
 
    return edges

def region_of_interest(canny):
    height, width = canny.shape
    mask = np.zeros_like(canny)

    # only focus bottom half of the screen

    polygon = np.array([[                  ## Crop the eage , Do hinh anh danh dau nguoc nen phai lam nguoc
        (0, height * 0.6),  #goc ban dau 3/4, trong code deep learning 1/2
        (width, height * 0.6),
        (width, height),
        (0, height),
    ]], np.int32)

    imgplot = plt.imshow(mask)
    # plt.show()
    cv2.fillPoly(mask, polygon, 255)
    # show_image("mask", mask)
    # imgplot = plt.imshow(mask)
    # plt.show()
    masked_image = cv2.bitwise_and(canny, mask)
    # imgplot = plt.imshow(masked_image)
    # plt.show()
    return masked_image

def detect_line_segments(cropped_edges):
    # tuning min_threshold, minLineLength, maxLineGap is a trial and error process by hand
    rho = 1  # precision in pixel, i.e. 1 pixel
    angle = np.pi / 180  # degree in radian, i.e. 1 degree
    min_threshold = 10  # minimal of votes
    line_segments = cv2.HoughLinesP(cropped_edges, rho, angle, min_threshold, np.array([]), minLineLength=8,
                                    maxLineGap=4)

    if line_segments is not None:
        for line_segment in line_segments:
            logging.debug('detected line_segment:')
            logging.debug("%s of length %s" % (line_segment, length_of_line_segment(line_segment[0])))

    return line_segments

def average_slope_intercept(frame, line_segments):
    """
    This function combines line segments into one or two lane lines
    If all line slopes are < 0: then we only have detected left lane
    If all line slopes are > 0: then we only have detected right lane
    """
    lane_lines = []
    if line_segments is None:
        logging.info('No line_segment segments detected')
        return lane_lines

    height, width, _ = frame.shape
    left_fit = []
    right_fit = []

    boundary = 1/2.5
    left_region_boundary = width * (1 - boundary)  # left lane line segment should be on left 2/3 of the screen
    right_region_boundary = width * boundary # right lane line segment should be on left 2/3 of the screen
    
    # print(line_segments)
    count = 0

    for line_segment in line_segments:
        count = count +1
        # print(count)
        
        for x1, y1, x2, y2 in line_segment:
            if x1 == x2:
                logging.info('skipping vertical line segment (slope=inf): %s' % line_segment)
                continue
            fit = np.polyfit((x1, x2), (y1, y2), 1)
            slope = fit[0]
            intercept = fit[1]
            if slope < 0:
                if x1 < left_region_boundary and x2 < left_region_boundary:
                    left_fit.append((slope, intercept))
            else:
                if x1 > right_region_boundary and x2 > right_region_boundary:
                    right_fit.append((slope, intercept))

    left_fit_average = np.average(left_fit, axis=0)
    if len(left_fit) > 0:
        lane_lines.append(make_points(frame, left_fit_average))

    right_fit_average = np.average(right_fit, axis=0)
    if len(right_fit) > 0:
        lane_lines.append(make_points(frame, right_fit_average))

    logging.debug('lane lines: %s' % lane_lines)  # [[[316, 720, 484, 432]], [[1009, 720, 718, 432]]]

    return lane_lines

def compute_steering_angle(frame, lane_lines):
    """ Find the steering angle based on lane line coordinate
        We assume that camera is calibrated to point to dead center
    """
    # print(lane_lines)
    if len(lane_lines) == 0:
        logging.info('No lane lines detected, do nothing')
        return -90

    height, width, _ = frame.shape
    
    #################################################################################################
    if len(lane_lines) == 1:                     #One_lane_line
        logging.debug('Only detected one lane line, just follow it. %s' % lane_lines[0])
        x1, _, x2, _ = lane_lines[0][0]
        x_offset = x2 - x1
        # print(x_offset)
    else:                                        #Two_lane_line   
        left_x1, _, left_x2, _ = lane_lines[0][0]
        right_x1, _, right_x2, _ = lane_lines[1][0]
        
       
        camera_mid_offset_percent = 0 # 0.0 means car pointing to center, -0.03: car is centered to left, +0.03 means car pointing to right
        mid = int(width / 2 * (1 + camera_mid_offset_percent))
        
    
        x_offset  = (math.sqrt((right_x1-left_x1)*(right_x1-left_x1)) / 2 + (left_x1)) - mid

        # print(left_x1)
        # print(right_x1)
        # print(x_offset)

    # find the steering angle, which is angle between navigation direction to end of center line
    y_offset = int(height / 2)

    # angle_to_mid_radian = math.atan(x_offset / y_offset)  # angle (in radian) to center vertical line
    # angle_to_mid_deg = int(angle_to_mid_radian * 180.0 / math.pi)  # angle (in degrees) to center vertical line
    # steering_angle = angle_to_mid_deg + 90  # this is the steering angle needed by picar front wheel\
    
    if x_offset != 0 :
        # angle_to_mid_radian = math.atan(y_offset / x_offset)  # angle (in radian) to center vertical line
        # angle_to_mid_deg = int(angle_to_mid_radian * 180.0 / math.pi)  # angle (in degrees) to center vertical line
        
        # print(angle_to_mid_deg)

        # if x_offset >= 0:
        #     steering_angle = (90 - angle_to_mid_deg) # this is the steering angle needed by picar front wheel\
        # else:
        #     steering_angle = angle_to_mid_deg

        # print(steering_angle)

        # Code PID
        angle_to_mid_radian = math.atan(x_offset / y_offset)  # angle (in radian) to center vertical line
        angle_to_mid_deg = int(angle_to_mid_radian * 180.0 / math.pi)  # angle (in degrees) to center vertical line

        steering_angle = angle_to_mid_deg
        
        # if x_offset >= 0:
        #     steering_angle = -angle_to_mid_deg # this is the steering angle needed by picar front wheel\
        # else:
        #     steering_angle = angle_to_mid_deg

        # print('Real' + str(steering_angle))
        # Write the variable `my_variable` to the serial port
        serial_steering_angle = steering_angle
        # serial_steering_angle +=90
        # print('Serial' + str(serial_steering_angle))
        # ser.write(bytes(serial_steering_angle))



    else:
        steering_angle = 0
    #####################################################################################################
    ######################################### end my code ###############################################
    # print(lane_lines)
    # # # print(mid)
    # print(x_offset)
    # print(y_offset)
    
    # # print(angle_to_mid_radian)
    # print(angle_to_mid_deg)
    # print(steering_angle)

    logging.debug('new steering angle: %s' % steering_angle)
    return steering_angle

def stabilize_steering_angle(curr_steering_angle, new_steering_angle, num_of_lane_lines, max_angle_deviation_two_lines=5, max_angle_deviation_one_lane=10):
    """
    Using last steering angle to stabilize the steering angle
    This can be improved to use last N angles, etc
    if new angle is too different from current angle, only turn by max_angle_deviation degrees
    """
    # if num_of_lane_lines == 2 :
    #     # if both lane lines detected, then we can deviate more
    #     max_angle_deviation = max_angle_deviation_two_lines
    # else :
    #     # if only one lane detected, don't deviate too much
    #     max_angle_deviation = max_angle_deviation_one_lane
    
    # angle_deviation = new_steering_angle - curr_steering_angle
    # if abs(angle_deviation) > max_angle_deviation:
    #     stabilized_steering_angle = int(curr_steering_angle
    #                                     + max_angle_deviation * angle_deviation / abs(angle_deviation))
    # else:
    #     stabilized_steering_angle = new_steering_angle
    
    stabilized_steering_angle = new_steering_angle   ## Adding

    logging.info('Proposed angle: %s, stabilized angle: %s' % (new_steering_angle, stabilized_steering_angle))
    return stabilized_steering_angle

############################
# Utility Functions
############################
def display_lines(frame, lines, line_color=(0, 255, 0), line_width=10):
    line_image = np.zeros_like(frame)
    if lines is not None:
        for line in lines:
            # print(line)
            for x1, y1, x2, y2 in line:
                x1 = np.int64(x1)
                y1 = np.int64(y1 )
                x2 = np.int64(x2)
                y2 = np.int64(y2)
                cv2.line(line_image, (x1, y1), (x2, y2), line_color, line_width)
    line_image = cv2.addWeighted(frame, 0.8, line_image, 1, 1)
    return line_image

def display_heading_line(frame, steering_angle, line_color=(0, 0, 255), line_width=5, ):
    heading_image = np.zeros_like(frame)
    height, width, _ = frame.shape

    # figure out the heading line from steering angle
    # heading line (x1,y1) is always center bottom of the screen
    # (x2, y2) requires a bit of trigonometry

    # Note: the steering angle of:
    # 0-89 degree: turn left
    # 90 degree: going straight
    # 91-180 degree: turn right 
    steering_angle_radian = steering_angle / 180.0 * math.pi
    x1 = np.int64(width / 2)
    y1 = np.int64(height)
    x2 = np.int64(x1 - height / 2 / math.tan(steering_angle_radian))
    y2 = np.int64(height / 2)
    
    if x1 < 2000 and y1  < 2000 and x2  < 2000 and y2  < 2000:
        cv2.line(heading_image, (x1, y1), (x2, y2), line_color, line_width)
        heading_image = cv2.addWeighted(frame, 0.8, heading_image, 1, 1)
    else:
        x1 = np.int64(width / 2)
        y1 = np.int64(height)
        x2 = np.int64(width / 2)
        y2 = np.int64(height / 2)
        cv2.line(heading_image, (x1, y1), (x2, y2), line_color, line_width)
        heading_image = cv2.addWeighted(frame, 0.8, heading_image, 1, 1)
    


    return heading_image

def length_of_line_segment(line):
    x1, y1, x2, y2 = line
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def show_image(title, frame, show=_SHOW_IMAGE):
    if show:
        cv2.imshow(title, frame)

def make_points(frame, line):
    height, width, _ = frame.shape
    slope, intercept = line
    y1 = height  # bottom of the frame
    y2 = int(y1 * 1 / 2)  # make points from middle of the frame down

    # bound the coordinates within the frame
    x1 = max(-width, min(2 * width, int((y1 - intercept) / slope)))
    x2 = max(-width, min(2 * width, int((y2 - intercept) / slope)))
    return [[x1, y1, x2, y2]]


class Follower:
    def __init__(self, car=None):
        Motor = servo_Class(Channel=0, ZeroOffset=0)
        Servor = servo_Class(Channel=1, ZeroOffset=0)    
        speed = 396
        vid = cv2.VideoCapture(0)

        while(True):

            # Capture the video frame
            # by frame
            ret, frame = vid.read()
            frame = cv2.flip(frame, 0)
            if ret == False: break

             # combo_image = land_follower.follow_lane(frame)
            self.curr_steering_angle = 90
            self.car = car
            combo_image = self.follow_lane(frame)
            lane_lines, frame = detect_lane(frame)

            if self.curr_steering_angle + 90 < 60 | self.curr_steering_angle + 90 > 135:
                steer = int((self.curr_steering_angle*4) + 90)
                deg = map_range(clamp(steer))
            else:
                steer = int((self.curr_steering_angle*2) + 90)
                deg = map_range(clamp(steer))

            Servor.SetPos(deg)
            Motor.SetPos(speed) 
            print(deg)
            # print(speed)
            # time.sleep(0.001)

            # cv2.imshow("Camera", combo_image)
            
            # the 'q' button is set as the
            # quitting button you may use any
            # desired button of your choice
            if cv2.waitKey(1) & 0xFF == ord('q'):
                Servor.ServorCleanup()
                Motor.MotorCleanup()
                vid.release()  
                cv2.destroyAllWindows()
                # time.sleep(0.1)
                break

        #         self.twist = Twist()
                
        # After the loop release the cap object
        # Destroy all the windows
       	
        

    def follow_lane(self, frame):
        # Main entry point of the lane follower
        lane_lines, frame = detect_lane(frame)
        final_frame = self.steer(frame, lane_lines)
        return final_frame

    def steer(self, frame, lane_lines):
        logging.debug('steering...')
        if len(lane_lines) == 0:
            logging.error('No lane lines detected, nothing to do.')
            return frame

        new_steering_angle = compute_steering_angle(frame, lane_lines)

        self.curr_steering_angle = stabilize_steering_angle(self.curr_steering_angle, new_steering_angle, len(lane_lines))

        if self.car is not None:
            self.car.front_wheels.turn(self.curr_steering_angle)
        
        # print(self.curr_steering_angle)
        ###################display heading line form 0 - 180 -> left to right ( need +90 )######################
        curr_heading_image = display_heading_line(frame, self.curr_steering_angle+90)  
        # show_image("heading", curr_heading_image)
        return curr_heading_image
        # return self.curr_steering_angle

follow = Follower()
