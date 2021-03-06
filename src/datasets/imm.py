"""
.. module:: datasets
   :synopsis: Contains imm dataset abstraction layer


"""
import cv2
import numpy as np
import argparse
import os

import aam


class IMMPoints(aam.AAMPoints):
    SHAPE = (58, 2)

    """Accepts IMM datapoint file which can be shown or used"""
    def __init__(self, filename=None, points_list=None):
        """
        Args:
            filename: optional .asf file with the imm format
            points: optional list of x,y points
        """
        assert filename is not None or points_list is not None, 'filename or \
         a ndarray of points list should be given'

        self.filename = filename

        if filename:
            points_list = self.import_file(filename)

        aam.AAMPoints.__init__(
            self, normalized_flattened_points_list=points_list.flatten(),
            actual_shape=self.SHAPE
        )

    def get_points(self):
        """
        Get the flattened list of points

        Returns:
            ndarray. flattened array of points, see AAMPoints for more
            information.
        """
        return self.normalized_flattened_points_list

    def __get_image(self):
        """
        Get the image corresponding to the self.image_file

        Returns:
            ndarray image
        """
        assert hasattr(self, 'image_file'), 'image_file name should be set, \
                import file must be invoked first'
        self.image = cv2.imread(self.image_file)

    def get_image(self):
        """
        Get the image corresponding to the filename
        If filename == image_1.asf, then we read image_1.jpg from disk
        and return this to the user.

        Returns:
            ndarray image
        """
        return self.image

    def import_file(self, filename):
        """
        Import an .asf filename. Load the points into a list of points and
        store the relative path to image file.

        Returns:
            ndarray(float). Numpy array of landmark locations as stated in the
            .asf files.
        """
        points_list = []

        with open(filename, 'r') as f:
            lines = f.readlines()
            data = lines[16:74]
            dir_name = os.path.dirname(filename)
            self.image_file = "{}/{}".format(dir_name, lines[-1].strip())
            self.__get_image()

            for d in data:
                points_list.append(d.split()[2:4])

        return np.asarray(points_list, dtype='f')


    def show_on_image(self, image, window_name='image', multiply=True):
        self.draw_triangles(image, self.points_list, multiply=multiply)

    def show(self, window_name='image'):
        """show the image and datapoints on the image"""
        assert(len(self.points_list) > 0)
        assert(len(self.filename) > 0)

        image = self.get_image()

        self.draw_triangles(image, self.points_list)


# TODO: move this to a shared location such that all dataset implementation
# return an instance of themselves when this function is envoked.
def factory(**kwargs):
    """
    Returns an instance of the dataset aam extending class

    Note that all dataset implementations (in this folder) need to have this
    function to enable transparent use of different datasets throughout this
    project. The reason for this is that we don't want to worry different about
    amounts of landmarks or locations of those landmarks, we just want to use
    them.
    """
    return IMMPoints(**kwargs)


def get_points(files):
    """
    Args:
        files (array):  Array of .asf full or relative path to .asf files.

    Returns:
        ndarray. Array of landmarks.

    """
    points = []

    for f in files:
        imm = IMMPoints(filename=f)
        points.append(imm.get_points())

    return np.asarray(points)


def get_image_with_landmarks(filename):
    """
    Get Points with image and landmarks/points

    Args:
        filename(fullpath): .asf file

    Returns:
        image, points
    """
    imm = IMMPoints(filename=filename)
    return imm.get_image(), imm.get_points()
