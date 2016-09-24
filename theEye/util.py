from config import *

TOP = 0
BOTTOM = 1
LEFT = 0
RIGHT = 1
display_ratio = 2.5

def merge_collided_bboxes( bbox_list ):
    # For every bbox...
    for this_bbox in bbox_list:

        # Collision detect every other bbox:
        for other_bbox in bbox_list:
            if this_bbox is other_bbox: continue  # Skip self

            # Assume a collision to start out with:
            has_collision = False

            # These coords are in screen coords, so > means
            # "lower than" and "further right than".  And <
            # means "higher than" and "further left than".

            # We also inflate the box size by 10% to deal with
            # fuzziness in the data.  (Without this, there are many times a bbox
            # is short of overlap by just one or two pixels.)
            if this_bbox[TOP][0] < other_bbox[TOP][0]:
                if this_bbox[BOTTOM][0]*1.1 > other_bbox[TOP][0]*0.9:
                    has_collision = True
            elif this_bbox[TOP][0]*0.9 < other_bbox[BOTTOM][0]*1.1:
                has_collision = True
            elif this_bbox[LEFT][1] < other_bbox[LEFT][1]:
                if this_bbox[RIGHT][1]*1.1 > other_bbox[LEFT][1]*0.9:
                    has_collision = True
            elif this_bbox[LEFT][1]*0.9 < other_bbox[RIGHT][1]*1.1:
                has_collision = True

            if has_collision:
                # merge these two bboxes into one, then start over:
                new_left = min( this_bbox[LEFT][1], other_bbox[LEFT][1] )
                new_right = max( this_bbox[RIGHT][1], other_bbox[RIGHT][1] )
                new_top = min( this_bbox[TOP][0], other_bbox[TOP][0] )
                new_bottom = max( this_bbox[BOTTOM][0], other_bbox[BOTTOM][0] )

                new_bbox = ( (new_top, new_left), (new_bottom, new_right) )

                bbox_list.remove( this_bbox )
                bbox_list.remove( other_bbox )
                bbox_list.append( new_bbox )
                # Start over with the new list:
                return merge_collided_bboxes( bbox_list )

    # When there are no collions between boxes, return that list:
    return bbox_list


def detect_capture_faces( image, haar_cascade, face_dict, capture ):

    faces = []
    image_size = (image.shape[0], image.shape[1])

    #faces = haar_cascade.detectMultiScale(grayscale, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, (20, 20) )
    #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING )
    #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 16, 16 ) )
    #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 4,4 ) )
    faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv2.cv.CV_HAAR_SCALE_IMAGE, ( image_size[0]/10, image_size[1]/10) )

    for box in faces:
        cv2.rectangle(image, ( box[0], box[1] ),
            ( box[0] + box[2], box[1] + box[3]), cv.RGB(255, 0, 0), 1, 8, 0)
        if capture:
            cropped = image[ box[1] : box[1] + box[3], box[0] : box[0] + box[2] ]
            name = "faces/" + str(time.time()) + ".jpg"
            cv2.imwrite(name, cropped)

def detect_faces( image, haar_cascade, mem_storage ):
    faces = []
    image_size = cv.GetSize( image )

    #faces = cv.HaarDetectObjects(grayscale, haar_cascade, storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, (20, 20) )
    #faces = cv.HaarDetectObjects(image, haar_cascade, storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING )
    #faces = cv.HaarDetectObjects(image, haar_cascade, storage )
    #faces = cv.HaarDetectObjects(image, haar_cascade, mem_storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 16, 16 ) )
    #faces = cv.HaarDetectObjects(image, haar_cascade, mem_storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 4,4 ) )
    faces = cv.HaarDetectObjects(image, haar_cascade, mem_storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( image_size[0]/10, image_size[1]/10) )

    for face in faces:
        box = face[0]
        cv.Rectangle(image, ( box[0], box[1] ),
            ( box[0] + box[2], box[1] + box[3]), cv.RGB(255, 0, 0), 1, 8, 0)

# def train_recognizer():