import cv2
def add_to_gallery(count, item):
    cv2.imwrite(f'sarcastic-photographer/gallery/photo_{count}.jpg', item)
def display_gallery(count):
    for i in range(count):
        img = cv2.imread(f'sarcastic-photographer/gallery/photo_{i}.jpg')
        cv2.imshow(f'Photo {i}', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    