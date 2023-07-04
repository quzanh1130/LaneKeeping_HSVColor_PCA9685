import cv2
import time

# Initialize the camera
cap = cv2.VideoCapture(0)

# Set the camera resolution (optional)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Capture images
image_count = 0  # Counter for captured images
image_dir = "dataset"  # Directory to save captured images
num_images = 10

while True:
    # Capture frame from the camera
    ret, frame = cap.read()
    frame = cv2.flip(frame,0)

    # Display the captured image
    cv2.imshow("Capture", frame)

    # Save the captured image
    image_path = f"{image_dir}/image_{image_count}.jpg"
    cv2.imwrite(image_path, frame)

    # Increment the image count
    image_count += 1

    # Check if the desired number of images has been reached
    if image_count == num_images:
        break

    # Delay for 0.5 seconds between capturing each image
    time.sleep(2)

    # Check if the user has pressed 'q' to stop capturing
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close windows
cap.release()
cv2.destroyAllWindows()