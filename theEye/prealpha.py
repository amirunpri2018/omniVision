#!/usr/bin/env python

import cv, cv2

from math import *
from scipy import *
from scipy.cluster import vq
import numpy as np
import time, sys, os, random, hashlib, heapq

import util
from config import *

"""
Python Motion Tracker

Reads an incoming video stream and tracks motion in real time.
Detected motion events are logged to a text file.  Also has face detection.
"""

class Target:
    def __init__(self):

        if len( sys.argv ) > 1:
            self.capture = cv2.VideoCapture( sys.argv[1] )
        else:
            fps=15
            is_color = True
            self.capture = cv2.VideoCapture(0)
            self.capture.set( cv.CV_CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH );
            self.capture.set( cv.CV_CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT );
        
        #self.writer = cv.CreateVideoWriter("/dev/shm/test1.mp4", cv.CV_FOURCC('D', 'I', 'V', 'X'), fps, frame_size, is_color )
        #self.writer = cv.CreateVideoWriter("test2.mpg", cv.CV_FOURCC('P', 'I', 'M', '1'), fps, frame_size, is_color )
        #self.writer = cv.CreateVideoWriter("test3.mp4", cv.CV_FOURCC('D', 'I', 'V', 'X'), fps, cv.GetSize(frame), is_color )
        #self.writer = cv.CreateVideoWriter("test4.mpg", cv.CV_FOURCC('P', 'I', 'M', '1'), fps, (320, 240), is_color )

        # These both gave no error message, but saved no file:
        ###self.writer = cv.CreateVideoWriter("test5.h263i", cv.CV_FOURCC('I', '2', '6', '3'), fps, cv.GetSize(frame), is_color )
        ###self.writer = cv.CreateVideoWriter("test6.fli",   cv.CV_FOURCC('F', 'L', 'V', '1'), fps, cv.GetSize(frame), is_color )
        # Can't play this one:
        ###self.writer = cv.CreateVideoWriter("test7.mp4",   cv.CV_FOURCC('D', 'I', 'V', '3'), fps, cv.GetSize(frame), is_color )

        # 320x240 15fpx in DIVX is about 4 gigs per day.

        self.writer = None
        _, frame = self.capture.retrieve()
        frame_size = (frame.shape[0], frame.shape[1])
        cv2.namedWindow("Target", 1)
        #cv.NamedWindow("Target2", 1)

    def detect_capture_faces( image, haar_cascade, face_dict, capture ):

        faces = []
        image_size = (image.shape[0], image.shape[1])

        #faces = haar_cascade.detectMultiScale(grayscale, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, (20, 20) )
        #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING )
        #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 16, 16 ) )
        #faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, ( 4,4 ) )
        faces = haar_cascade.detectMultiScale(image, 1.2, 2, cv2.cv.CV_HAAR_SCALE_IMAGE, ( image_size[0]/10, image_size[1]/10) )

        for box in faces:
            for f in face_dict.keys():

            cv2.rectangle(image, ( box[0], box[1] ),
                ( box[0] + box[2], box[1] + box[3]), cv.RGB(255, 0, 0), 1, 8, 0)
            if capture:
                cropped = image[ box[1] : box[1] + box[3], box[0] : box[0] + box[2] ]
                name = "faces/" + str(time.time()) + ".jpg"
                cv2.imwrite(name, cropped)

    def run(self):
        # Initialize
        #log_file_name = "tracker_output.log"
        #log_file = file( log_file_name, 'a' )

        _, frame = self.capture.read()

        # Capture the first frame from webcam for image properties
        display_image = frame.copy()
        # Greyscale image, thresholded to create the motion mask:
        grey_image = np.zeros((frame.shape[0], frame.shape[1], 1), uint8)
        # The RunningAvg() function requires a 32-bit or 64-bit image...
        running_average_image = np.zeros((frame.shape[0], frame.shape[1], 3), float32)
        # ...but the AbsDiff() function requires matching image depths:
        running_average_in_display_color_depth = running_average_image.copy()
        # The difference between the running average and the current frame:
        difference = running_average_image.copy()

        # For target counting
        target_count = 1
        last_target_count = 1
        last_target_change_t = 0.0

        # For obj counting
        last_frame_objs = 0
        obj_count = 0

        k_or_guess = 1
        frame_count=0
        codebook=[]
        last_frame_entity_list = []

        # For image saving
        last_scene_clear = False
        face_time_limit = 3.0
        time_limit = 2.0
        last_save_time = time.time()
        last_save_face_time = time.time()
        accumulated_scenes = []

        # For toggling display:
        image_list = [ "camera", "difference", "threshold", "display", "faces" ]
        image_index = 0   # Index into image_list

        # Prep for text drawing:
        text_font = cv2.FONT_HERSHEY_SIMPLEX
        text_coord = ( 5, 15 )
        text_color = (255,255,255)

        # For face recognition
        """
        Dictionary to store the recognition information about the face.
        { generated_name : (alias, image_list) }
        """
        face_dict = {}

        # Use the LBPH Face Recognizer for face recognition
        recognizer = cv2.createLBPHFaceRecognizer()

        ###############################
        ### HaarCascade Selection
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_frontalface_default.xml' )
        haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_frontalface_alt.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_frontalface_alt2.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_mcs_mouth.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_eye.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_frontalface_alt_tree.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_upperbody.xml' )
        #haar_cascade = cv2.CascadeClassifier( 'haarcascades/haarcascade_profileface.xml' )

        # Set this to the max number of targets to look for (passed to k-means):
        max_targets = 3

        t0 = time.time()


        while True:

            """
            Preprocessing image
            """
            # Capture frame from webcam
            _, camera_image = self.capture.retrieve()
            frame_count += 1
            frame_t0 = time.time()

            # Create an image with interactive feedback:
            display_image = camera_image.copy()

            # Create a working "color image" to modify / blur
            color_image = camera_image.copy().astype(float32)

            # Smooth to get rid of false positives
            cv2.GaussianBlur( color_image, (5,5), 0)

            # Use the Running Average as the static background
            # a = 0.020 leaves artifacts lingering way too long.
            # a = 0.320 works well at 320x240, 15fps.  (1/a is roughly num frames.)
            cv2.accumulateWeighted( color_image, running_average_image, 0.320, None )

            # Convert the scale of the moving average.
            running_average_in_display_color_depth = running_average_image.copy()

            # Subtract the current frame from the moving average.
            cv2.absdiff( color_image, running_average_in_display_color_depth, difference )

            # Convert the image to greyscale.
            grey_image = cv2.cvtColor( difference, cv2.COLOR_BGR2GRAY ).astype(uint8)

            # Threshold the image to a black and white motion mask:
            cv2.threshold( grey_image, 2, 255, cv2.THRESH_BINARY )
            # Smooth and threshold again to eliminate "sparkles"
            cv2.GaussianBlur( color_image, (5,5), 0)
            cv2.threshold( grey_image, 240, 255, cv2.THRESH_BINARY )

            grey_image_as_array = grey_image
            non_black_coords_array = np.where( grey_image > 3 )
            # Convert from np.where()'s two separate lists to one list of (x, y) tuples:
            non_black_coords_array = zip( non_black_coords_array[1], non_black_coords_array[0] )

            points = []   # Was using this to hold either pixel coords or polygon coords.
            bounding_box_list = []

            # Now calculate movements using the white pixels as "motion" data
            _,thresh = cv2.threshold(grey_image,127,255,0)
            _,contours = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
            print contours
            """
            Finding contours and bounding boxes
            """
            for contour in contours:
                bounding_rect = cv2.boundingRect( contour )
                point1 = ( bounding_rect[0], bounding_rect[1] )
                point2 = ( bounding_rect[0] + bounding_rect[2], bounding_rect[1] + bounding_rect[3] )

                bounding_box_list.append( ( point1, point2 ) )
                polygon_points = cv2.approxPolyDP( contour, 0.1 * cv2.arcLength(contour, True), True )

                # To track polygon points only (instead of every pixel):
                #points += list(polygon_points)

                # Draw the contours:
                ###cv.DrawContours(color_image, contour, cv.CV_RGB(255,0,0), cv.CV_RGB(0,255,0), levels, 3, 0, (0,0) )
                cv2.fillPoly( grey_image, polygon_points, (255,255,255), 0, 0 )
                cv2.polylines( display_image, [ polygon_points, ], 0, (255,255,255), 1, 0, 0 )
                #cv.Rectangle( display_image, point1, point2, cv.CV_RGB(120,120,120), 1)


            # Find the average size of the bbox (targets), then
            # remove any tiny bboxes (which are prolly just noise).
            # "Tiny" is defined as any box with 1/10th the area of the average box.
            # This reduces false positives on tiny "sparkles" noise.
            """
            Drawing bounding boxes on display_image
            """
            box_areas = []
            for box in bounding_box_list:
                box_width = box[RIGHT][0] - box[LEFT][0]
                box_height = box[BOTTOM][0] - box[TOP][0]
                box_areas.append( box_width * box_height )

                #cv.Rectangle( display_image, box[0], box[1], cv.CV_RGB(255,0,0), 1)

            average_box_area = 0.0
            if len(box_areas): average_box_area = float( sum(box_areas) ) / len(box_areas)

            trimmed_box_list = []
            for box in bounding_box_list:
                box_width = box[RIGHT][0] - box[LEFT][0]
                box_height = box[BOTTOM][0] - box[TOP][0]

                # Only keep the box if it's not a tiny noise box:
                if (box_width * box_height) > average_box_area*0.1 and average_box_area > 100: 
                    trimmed_box_list.append( box )

            # Draw the trimmed box list:
            #for box in trimmed_box_list:
            #   cv.Rectangle( display_image, box[0], box[1], cv.CV_RGB(0,255,0), 2 )

            bounding_box_list = util.merge_collided_bboxes( trimmed_box_list )

            # Draw the merged box list:
            for box in bounding_box_list:
                cv2.rectangle( display_image, box[0], box[1], cv.CV_RGB(0,255,0), 1 )


            # For obj counting
            print str(len(bounding_box_list)) + " boxes found."
            if (len(bounding_box_list) > last_frame_objs):
                obj_count += len(bounding_box_list) - last_frame_objs
                print str(last_frame_objs) + " new objs."
            last_frame_objs = len(bounding_box_list)
            print str(obj_count) + " total objs."


            """
            Estimated target
            """
            # Here are our estimate points to track, based on merged & trimmed boxes:
            estimated_target_count = len( bounding_box_list )

            # Don't allow target "jumps" from few to many or many to few.
            # Only change the number of targets up to one target per n seconds.
            # This fixes the "exploding number of targets" when something stops moving
            # and the motion erodes to disparate little puddles all over the place.

            if frame_t0 - last_target_change_t < .350:  # 1 change per 0.35 secs
                estimated_target_count = last_target_count
            else:
                if last_target_count - estimated_target_count > 1: estimated_target_count = last_target_count - 1
                if estimated_target_count - last_target_count > 1: estimated_target_count = last_target_count + 1
                last_target_change_t = frame_t0

            # Clip to the user-supplied maximum:
            estimated_target_count = min( estimated_target_count, max_targets )

            # The estimated_target_count at this point is the maximum number of targets
            # we want to look for.  If kmeans decides that one of our candidate
            # bboxes is not actually a target, we remove it from the target list below.

            # Using the numpy values directly (treating all pixels as points):
            points = np.array( non_black_coords_array, dtype='f' )
            center_points = []

            if len(points):

                # If we have all the "target_count" targets from last frame,
                # use the previously known targets (for greater accuracy).
                k_or_guess = max( estimated_target_count, 1 )  # Need at least one target to look for.
                if len(codebook) == estimated_target_count:
                    k_or_guess = codebook

                #points = vq.whiten(array( points ))  # Don't do this!  Ruins everything.
                codebook, distortion = vq.kmeans( array( points ), k_or_guess )

                # Convert to tuples (and draw it to screen)
                for center_point in codebook:
                    center_point = ( int(center_point[0]), int(center_point[1]) )
                    center_points.append( center_point )
                    #cv.Circle(display_image, center_point, 10, cv.CV_RGB(255, 0, 0), 2)
                    #cv.Circle(display_image, center_point, 5, cv.CV_RGB(255, 0, 0), 3)

            # Now we have targets that are NOT computed from bboxes -- just
            # movement weights (according to kmeans).  If any two targets are
            # within the same "bbox count", average them into a single target.
            #
            # (Any kmeans targets not within a bbox are also kept.)

            """
            Trimmed center points
            """
            trimmed_center_points = []
            removed_center_points = []

            for box in bounding_box_list:
                # Find the centers within this box:
                center_points_in_box = []

                for center_point in center_points:
                    if  center_point[0] < box[RIGHT][0] and center_point[0] > box[LEFT][0] and \
                        center_point[1] < box[BOTTOM][1] and center_point[1] > box[TOP][1] :

                        # This point is within the box.
                        center_points_in_box.append( center_point )

                # Now see if there are more than one.  If so, merge them.
                if len( center_points_in_box ) > 1:
                    # Merge them:
                    x_list = y_list = []
                    for point in center_points_in_box:
                        x_list.append(point[0])
                        y_list.append(point[1])

                    average_x = int( float(sum( x_list )) / len( x_list ) )
                    average_y = int( float(sum( y_list )) / len( y_list ) )

                    trimmed_center_points.append( (average_x, average_y) )

                    # Record that they were removed:
                    removed_center_points += center_points_in_box

                if len( center_points_in_box ) == 1:
                    trimmed_center_points.append( center_points_in_box[0] ) # Just use it.

            # If there are any center_points not within a bbox, just use them.
            # (It's probably a cluster comprised of a bunch of small bboxes.)
            for center_point in center_points:
                if (not center_point in trimmed_center_points) and (not center_point in removed_center_points):
                    trimmed_center_points.append( center_point )

            # Draw what we found: Test Testd
            #for center_point in trimmed_center_points:
            #   center_point = ( int(center_point[0]), int(center_point[1]) )
            #   cv.Circle(display_image, center_point, 20, cv.CV_RGB(255, 255,255), 1)
            #   cv.Circle(display_image, center_point, 15, cv.CV_RGB(100, 255, 255), 1)
            #   cv.Circle(display_image, center_point, 10, cv.CV_RGB(255, 255, 255), 2)
            #   cv.Circle(display_image, center_point, 5, cv.CV_RGB(100, 255, 255), 3)

            # Determine if there are any new (or lost) targets:
            actual_target_count = len( trimmed_center_points )
            last_target_count = actual_target_count

            # Now build the list of physical entities (objects)
            this_frame_entity_list = []

            # An entity is list: [ name, color, last_time_seen, last_known_coords ]

            for target in trimmed_center_points:

                # Is this a target near a prior entity (same physical entity)?
                entity_found = False
                entity_distance_dict = {}

                for entity in last_frame_entity_list:

                    entity_coords= entity[3]
                    delta_x = entity_coords[0] - target[0]
                    delta_y = entity_coords[1] - target[1]

                    distance = sqrt( pow(delta_x,2) + pow( delta_y,2) )
                    entity_distance_dict[ distance ] = entity

                # Did we find any non-claimed entities (nearest to furthest):
                distance_list = entity_distance_dict.keys()
                distance_list.sort()

                for distance in distance_list:

                    # Yes; see if we can claim the nearest one:
                    nearest_possible_entity = entity_distance_dict[ distance ]

                    # Don't consider entities that are already claimed:
                    if nearest_possible_entity in this_frame_entity_list:
                        #print "Target %s: Skipping the one iwth distance: %d at %s, C:%s" % (target, distance, nearest_possible_entity[3], nearest_possible_entity[1] )
                        continue

                    #print "Target %s: USING the one iwth distance: %d at %s, C:%s" % (target, distance, nearest_possible_entity[3] , nearest_possible_entity[1])
                    # Found the nearest entity to claim:
                    entity_found = True
                    nearest_possible_entity[2] = frame_t0  # Update last_time_seen
                    nearest_possible_entity[3] = target  # Update the new location
                    this_frame_entity_list.append( nearest_possible_entity )
                    #log_file.write( "%.3f MOVED %s %d %d\n" % ( frame_t0, nearest_possible_entity[0], nearest_possible_entity[3][0], nearest_possible_entity[3][1]  ) )
                    break

                if entity_found == False:
                    # It's a new entity.
                    color = ( random.randint(0,255), random.randint(0,255), random.randint(0,255) )
                    name = hashlib.md5( str(frame_t0) + str(color) ).hexdigest()[:6]
                    last_time_seen = frame_t0

                    new_entity = [ name, color, last_time_seen, target ]
                    this_frame_entity_list.append( new_entity )
                    #log_file.write( "%.3f FOUND %s %d %d\n" % ( frame_t0, new_entity[0], new_entity[3][0], new_entity[3][1]  ) )

            # Now "delete" any not-found entities which have expired:
            entity_ttl = 1.0  # 1 sec.

            for entity in last_frame_entity_list:
                last_time_seen = entity[2]
                if frame_t0 - last_time_seen > entity_ttl:
                    # It's gone.
                    #log_file.write( "%.3f STOPD %s %d %d\n" % ( frame_t0, entity[0], entity[3][0], entity[3][1]  ) )
                    pass
                else:
                    # Save it for next time... not expired yet:
                    this_frame_entity_list.append( entity )

            # For next frame:
            new_entity_num = len(this_frame_entity_list) - len(last_frame_entity_list)
            if not new_entity_num == 0:
                print "FOUND ", new_entity_num, "NEW ENTITIES!"
            last_frame_entity_list = this_frame_entity_list

            # Draw the found entities to screen:
            for entity in this_frame_entity_list:
                center_point = entity[3]
                c = entity[1]  # RGB color tuple
                cv2.circle(display_image, center_point, 20, cv.CV_RGB(c[0], c[1], c[2]), 1)
                cv2.circle(display_image, center_point, 15, cv.CV_RGB(c[0], c[1], c[2]), 1)
                cv2.circle(display_image, center_point, 10, cv.CV_RGB(c[0], c[1], c[2]), 2)
                cv2.circle(display_image, center_point,  5, cv.CV_RGB(c[0], c[1], c[2]), 3)


            """
            Handling control
            """
            #print "min_size is: " + str(min_size)
            # Listen for ESC or ENTER key
            c = cv.WaitKey(7) % 0x100
            if c == 27 or c == 10:
                break

            # Toggle which image to show
            if chr(c) == 'd':
                image_index = ( image_index + 1 ) % len( image_list )

            image_name = image_list[ image_index ]

            # Display frame to user
            if image_name == "camera":
                image = camera_image
                cv2.putText( image, "Camera (Normal)", text_coord, text_font, 1, text_color )
            elif image_name == "display":
                image = display_image
                cv2.putText( image, "Targets (w/AABBs and contours)", text_coord, text_font, 1, text_color )
            elif image_name == "faces":
                # Do face detection
                if last_scene_clear and time.time() - last_save_face_time > face_time_limit:
                    util.detect_capture_faces( camera_image, haar_cascade, True )
                    last_save_face_time = time.time()
                else:
                    detect_capture_faces( camera_image, haar_cascade, face_dict, False )
                image = camera_image  # Re-use camera image here
                cv2.putText( image, "Face Detection", text_coord, text_font, 1, text_color )

            """
            Image saving
            """
            # For image saving
            if len(bounding_box_list) > 0:
                if last_scene_clear and time.time() - last_save_time > time_limit:
                    cv2.imwrite(hashlib.md5( str(time.time()) ).hexdigest()[:6] + ".jpg", display_image)
                    last_save_time = time.time()

            if len(bounding_box_list) == 0:
                last_scene_clear = True
            else:
                last_scene_clear = False

            """
            Display
            """
            size = image.shape
            large = np.zeros( ( int(size[0] * display_ratio), int(size[1] * display_ratio), int(size[2] * display_ratio)), float32 )
            large = cv2.resize(image, (0,0), fx=display_ratio, fy=display_ratio, interpolation=cv2.INTER_CUBIC)
            cv2.imshow( "Target", large )

            frame_t1 = time.time()
            if self.writer:
                cv.WriteFrame( self.writer, image );
            else:
                # If reading from a file, put in a forced delay:
                delta_t = frame_t1 - frame_t0
                if delta_t < ( 1.0 / 15.0 ): time.sleep( ( 1.0 / 15.0 ) - delta_t )

            #log_file.flush()

            # If only using a camera, then there is no time.sleep() needed,
            # because the camera clips us to 15 fps.  But if reading from a file,
            # we need this to keep the time-based target clipping correct:

        t1 = time.time()
        time_delta = t1 - t0
        processed_fps = float( frame_count ) / time_delta
        print "Got %d frames. %.1f s. %f fps." % ( frame_count, time_delta, processed_fps )

if __name__=="__main__":
    t = Target()
    t.run()





