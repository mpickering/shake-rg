import numpy as np
import cv2 as cv
import sys
import os
import os.path


def debugImwrite(filename, img):
    #cv.imwrite(filename, img)
    pass

def crop(input_image, output_dir):
    print(os.path.isfile(input_image))
    print(input_image)
    name = os.path.basename(input_image)
    print(name)

    d = os.path.dirname(input_image)
    print(os.listdir(d))

    ## (1) Read
    img = cv.imread(input_image)
    #img = ocr.ocr(img)
    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    debugImwrite('0.jpg', gray)

    vis      = img.copy()

    ## (2) Threshold
    th, threshed = cv.threshold(gray, 255, 255, cv.THRESH_BINARY_INV|cv.THRESH_OTSU)
    th, threshed = cv.threshold(gray, 240, 255, cv.THRESH_BINARY_INV)
    #debugImwrite('1.jpg', threshed)

    ## (3) Find the min-area contour
    k = 0
    factor=100
    row, col= img.shape[:2]
    while True:
        _, cnts, _ = cv.findContours(threshed, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv.contourArea, reverse=True)
        cnt = cnts[0]

        # If the outside contour is a rectangle, then the image has a border so
        # we aggressively chop it.
        epsilon = 0.01*cv.arcLength(cnt,True)
        smoothed_outside = cv.approxPolyDP(cnt, epsilon, True)
        print (len(smoothed_outside))
        if len(smoothed_outside) > 4: break

        #If the outermost contour is a border try to remove it by filling
        # the outside with a solid white border.
        threshed= cv.rectangle(threshed, (0,0), (col, row), (0,0,0), 20+k*factor)
        k += 1
        #debugImwrite('border.jpg', threshed)

    # Crop the image by 20 anyway
    img= cv.rectangle(img, (0,0), (col, row), (255,255,255), 20+k*factor)
    #debugImwrite('img-border.jpg', img)



    ## Now remove anything in the image which is rectangular
    _, cnts, _ = cv.findContours(threshed, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv.contourArea, reverse=True)

    remove = []
    do_remove = False
    for i,cnt in enumerate(cnts[:10]):
        print (i, len(cnt), do_remove)
        epsilon = 0.001*cv.arcLength(cnt,True)
        cnt = cv.approxPolyDP(cnt, epsilon, True)
        print (i, len(cnt), do_remove)
        if len(cnt) < 10 and do_remove:
            print("Removing {}".format(cnt))
            remove.append(cnt)
        print (i, len(cnt))
        if len(cnt) > 10:
            print(i)
            do_remove = True
        mask = np.zeros(img.shape[:2],np.uint8)
        cv.drawContours(mask, [cnt],-1, 255, -1)
        #debugImwrite('contours-{}.jpg'.format(i), mask)

    mask = np.zeros(img.shape,np.uint8)
    cv.drawContours(mask, remove,-1, (255, 255, 255), -1)
    debugImwrite('mask-remove.jpg', mask)
    img = cv.bitwise_or(img, mask)
    debugImwrite('img2.jpg', img)

    gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    kernel = np.ones((35,35),np.float32)/(35 * 35)
    gray = cv.filter2D(gray,-1,kernel)
    #debugImwrite('gray.jpg', gray)

    ## (2) Threshold
    th, threshed = cv.threshold(gray, 255, 255, cv.THRESH_BINARY_INV|cv.THRESH_OTSU)
    th, threshed = cv.threshold(gray, 250, 255, cv.THRESH_BINARY_INV)
    debugImwrite('1.jpg', threshed)

    ## (3) Find the min-area contour
    _, cnts, _ = cv.findContours(threshed, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    print(len(cnts))
    cnts = sorted(cnts, key=cv.contourArea, reverse=True)



    kernel = np.ones((10,10),np.uint8)
    threshed = cv.morphologyEx(threshed, cv.MORPH_CLOSE, kernel)
    threshed = cv.morphologyEx(threshed, cv.MORPH_OPEN, kernel)
    #debugImwrite('1a.jpg', threshed)

    ## (3) Find the min-area contour

    kernel = np.ones((10,10),np.uint8)
    threshed = cv.morphologyEx(threshed, cv.MORPH_CLOSE, kernel)
    threshed = cv.morphologyEx(threshed, cv.MORPH_OPEN, kernel)
    #debugImwrite('1a.jpg', threshed)

    ## (3) Find the min-area contour
    _, cnts, _ = cv.findContours(threshed, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    print(len(cnts))
    cnts = sorted(cnts, key=cv.contourArea, reverse=True)

    remove = []

    cnt = cnts[0]


    mask = np.zeros(img.shape[:2],np.uint8)
    cv.drawContours(mask, [cnt],-1, 255, 2)
    #debugImwrite('3.jpg', mask)

    #kernel = np.ones((10,10),np.uint8)
    #opening = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
    #closing = cv.morphologyEx(img, cv.MORPH_CLOSE, kernel)
    ##debugImwrite('3a.jpg', closing)

    epsilon = 0.001*cv.arcLength(cnt,True)
    cnt = cv.approxPolyDP(cnt, epsilon, True)
    mask = np.zeros(img.shape[:2],np.uint8)
    cv.drawContours(mask, [cnt],-1, 255, -1)
    #debugImwrite('4.jpg', mask)


    #kernel = np.ones((10,10),np.uint8)
    #opening = cv.morphologyEx(mask, cv.MORPH_OPEN, kernel)
    ##debugImwrite('4a.jpg', opening)
    #kernel = np.ones((100,100),np.uint8)
    #opening = cv.morphologyEx(opening, cv.MORPH_DILATE, kernel)
    ##debugImwrite('4b.jpg', opening)

    #cnt = cv.convexHull(cnt)

    # (4) Create mask and do bitwise-op
    img = cv.imread(input_image)
    mask = np.zeros(img.shape[:2],np.uint8)
    cv.drawContours(mask, [cnt],-1, 255, -1)
    kernel = np.ones((25,25),np.uint8)
    mask = cv.erode(mask,kernel,iterations = 1)
    #debugImwrite('mask.jpg', mask)
    dst = cv.bitwise_and(img, img, mask=mask)

    cv.imwrite(os.path.join(output_dir, name), dst)

