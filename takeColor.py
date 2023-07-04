import cv2
import numpy as np

def main():
    global output

    cv2.namedWindow("image")

    cv2.createTrackbar('HMin','image',0,179,nothing)
    cv2.createTrackbar('SMin','image',0,255,nothing)
    cv2.createTrackbar('VMin','image',0,255,nothing)
    cv2.createTrackbar('HMax','image',0,179,nothing)
    cv2.createTrackbar('SMax','image',0,255,nothing)
    cv2.createTrackbar('VMax','image',0,255,nothing)

    cv2.setTrackbarPos('HMax', 'image', 179)
    cv2.setTrackbarPos('SMax', 'image', 255)
    cv2.setTrackbarPos('VMax', 'image', 255)

    output = np.zeros((480,640,3), dtype=np.uint8)

    while True:
        cv_image = cv2.imread("image.jpg")

        hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

        hMin = cv2.getTrackbarPos('HMin','image')
        sMin = cv2.getTrackbarPos('SMin','image')
        vMin = cv2.getTrackbarPos('VMin','image')
        hMax = cv2.getTrackbarPos('HMax','image')
        sMax = cv2.getTrackbarPos('SMax','image')
        vMax = cv2.getTrackbarPos('VMax','image')

        lower = np.array([hMin, sMin, vMin])
        upper = np.array([hMax, sMax, vMax])

        mask = cv2.inRange(hsv, lower, upper)
        output = cv2.bitwise_and(cv_image, cv_image, mask=mask)

        cv2.imshow("image", output)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
