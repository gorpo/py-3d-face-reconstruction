import logging
import numpy as np
from matplotlib.tri import Triangulation
import cv2

# local imports
import pca
import utils.texture as tx
import utils.triangles as tu

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)


class AAMPoints():
    """
    Object to store AAM points / landmarks. Tries to keep the scaling of
    the shape parameters transparent.
    """
    def __init__(self, normalized_flattened_points_list=None, points_list=None, actual_shape=()):
        self.normalized_flattened_points_list = normalized_flattened_points_list
        self.points_list = points_list
        self.actual_shape = actual_shape
        self.bounding_box = None

    def get_bounding_box(self):
        if self.bounding_box is None:
            return self.calculate_bounding_box()
        return self.bounding_box

    def get_scaled_points(self, shape, rescale=True):
        if self.points_list is None:
            self.points_list = self.normalized_flattened_points_list

            if len(self.actual_shape):
                self.points_list = self.points_list.reshape(self.actual_shape)

            h = shape[0]
            w = shape[1]

            self.points_list[:, 0] = self.points_list[:, 0] * w
            self.points_list[:, 1] = self.points_list[:, 1] * h

        return self.points_list

    def calculate_bounding_box(self):
        """
        Calculate bounding box in the **scaled** points list
        The empasis on on scaled because the convexHull does not support
        small values, the normalized_flattened_points_list does not work.
        """
        assert self.points_list is not None, \
            'the list points already need to be scaled order to correctly work'

        hull = cv2.convexHull(self.points_list, returnPoints=True)
        return cv2.boundingRect(hull)

    def get_bounding_box_2(self):
        pass
        #hull = cv2.convexHull(self.points_list, returnPoints=True)
        #x, y, w_slice, h_slice = cv2.boundingRect(hull)

        #return cv2.boundingRect()

def get_mean(vector):
    """ construct a mean from a matrix of x,y values
    Args:
        imm_points(numpy array) that follows the following structure:

    Returns:
        mean_values (numpy array)

    Examples:
        Input observations:
            0. [[x_0_0, y_0_0], ... , [x_0_m, y_0_m]],
            1. [[x_1_0, y_1_0], ... , [x_1_m, y_1_m]],
            2. [[x_2_0, y_2_0], ... , [x_2_m, y_2_m]],
            3. [[x_3_0, y_3_0], ... , [x_3_m, y_3_m]]

                ....           ....       .....

            n. [[x_4_0, y_4_0], ... , [x_n_m, y_n_m]]

        This vector containts the mean values of the corresponding column, like so:
            0. [[x_0_0, y_0_0], ... , [x_0_k, y_0_k]],
            1. [[x_1_0, y_1_0], ... , [x_1_k, y_1_k]],
            2. [[x_2_0, y_2_0], ... , [x_2_k, y_2_k]],
            3. [[x_3_0, y_3_0], ... , [x_3_k, y_3_k]]

                ....           ....       .....

            n. [[x_4_0, y_4_0], ... , [x_n_k, y_n_k]]

            mean. [[x_mean_0, y_mean_0], ... [x_mean_n, y_mean_n]]
    """
    return np.mean(vector, axis=0)


def get_triangles(x_vector, y_vector):
    """ perform triangulation between two 2d vectors"""
    return Triangulation(x_vector, y_vector).triangles


def build_shape_feature_vectors(files, get_points, flattened=False):
    """
    Gets the aam points from the files and appends them seperately to one
    array.

    Args:
        files (list): list files

    return:
        list: list of feature vectors
    """
    points = get_points(files)

    if flattened:
        points = pca.flatten_feature_vectors(points, dim=0)

    return points


def sample_from_triangles(src, points2d_src, points2d_dst, triangles, dst):
    """
    Get pixels from within the  triangles [[p1, p2, p3]_0, .. [p1, p2, p3]_n].
    Args:
        src(ndarray, dtype=uint8): input image
        points2d_src(ndarray, dtype=np.int32): shape array [[x, y], ... [x, y]]
        points2d_dst(ndarray, dtype=np.int32): shape array [[x, y], ... [x, y]]
        triangles(ndarray, ndim=3, dtype=np.int32): shape array [[p1, p2, p3]_0, .. [p1, p2, p3]_n].

    """
    for tri in triangles:
        src_p1, src_p2, src_p3 = points2d_src[tri]
        dst_p1, dst_p2, dst_p3 = points2d_dst[tri]

        tx.fill_triangle_src_dst(
            src, dst,
            src_p1[0], src_p1[1],
            src_p2[0], src_p2[1],
            src_p3[0], src_p3[1],
            dst_p1[0], dst_p1[1],
            dst_p2[0], dst_p2[1],
            dst_p3[0], dst_p3[1]
        )


def build_texture_feature_vectors(files, get_image_with_points, MeanPoints, triangles):
    """
    Args:
        files (list): list files
        flattened (bool): Flatten the inner feature vectors, see
            flatten_feature_vectors.
        MeanPoints(AAMPoints): AAMPoints object

    Returns:
        list: list of feature vectors
    """
    mean_texture = []
    x, y, w_slice, h_slice = MeanPoints.get_bounding_box()

    for i, f in enumerate(files):
        image, points = get_image_with_points(f)

        Points = AAMPoints(
            normalized_flattened_points_list=points,
            actual_shape=(58, 2)
        )

        # empty colored image
        dst = np.full((image.shape[0], image.shape[1], 3), fill_value=0, dtype=np.uint8)

        sample_from_triangles(
            image,
            Points.get_scaled_points(image.shape),
            MeanPoints(image.shape),
            triangles,
            dst
        )

        dst_flattened = dst[y: y + h_slice, x: x + w_slice].flatten()
        mean_texture.append(dst_flattened)

        logger.info('processed file: {} {}/{}'.format(f, i, len(files)))

    return np.asarray(mean_texture)


def get_pixel_values(image, points):
    """ docstring """
    h, w, c = image.shape

    points[:, 0] = points[:, 0] * w
    points[:, 1] = points[:, 1] * h

    image = cv2.blur(image, (3, 3))

    hull = cv2.convexHull(points, returnPoints=True)
    rect = cv2.boundingRect(hull)

    x, y, w, h = rect

    # pixels = np.zeros((h, w, c), dtype=np.uint8)
    for i in np.linspace(0, 1, num=150):
        for j in np.linspace(0, 1, num=150):
            y_loc_g = int(i * h + y)
            x_loc_g = int(j * w + x)

            if cv2.pointPolygonTest(hull, (x_loc_g, y_loc_g), measureDist=False) >= 0:
                image[y_loc_g][x_loc_g][0] = 0
                image[y_loc_g][x_loc_g][1] = 0
                image[y_loc_g][x_loc_g][2] = 0

    # return np.asarray(pixels, dtype=np.uint8), hull
    return image, hull
