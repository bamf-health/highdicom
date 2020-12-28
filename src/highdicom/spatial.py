from typing import Sequence, Tuple

import numpy as np


def create_rotation_matrix(
        image_orientation: Sequence[float],
    ) -> np.ndarray:
    """Builds a rotation matrix.

    Parameters
    ----------
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference

    Returns
    -------
    numpy.ndarray
        3 x 3 rotation matrix

    """
    row_cosines = np.array(image_orientation[:3])
    column_cosines = np.array(image_orientation[3:])
    n = np.cross(row_cosines.T, column_cosines.T)
    return np.column_stack([
        row_cosines,
        column_cosines,
        n
    ])


def compute_rotation(
        image_orientation: Sequence[float],
        in_degrees: bool = False
    ) -> float:
    """Computes the rotation of the image with respect to the frame of
    reference (patient or slide coordinate system).

    This is only valid if the two coordinate systems are related via a planar
    rotation. Otherwise, an exception is raised.

    Parameters
    ----------
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference
    in_degrees: bool, optional
        Whether angle should be returned in degrees rather than radians

    Returns
    -------
    float
        Angle (in radians or degrees, depending on whether `in_degrees`
        is ``False`` or ``True``, respectively)

    Raises
    ------
    ValueError
        If the provided image orientation is not related to the frame of
        reference coordinate system by a rotation within the image plane.

    """
    if (image_orientation[2] != 0.0) or (image_orientation[5] != 0.0):
        raise ValueError(
            "The provided image orientation is not related to the frame of "
            "reference coordinate system by a simple planar rotation"
        )
    rotation = create_rotation_matrix(image_orientation)
    if rotation[2, 2] < 0.0:
        raise ValueError(
            "The provided image orientation indicates that the image "
            "coordinate system is flipped relative to the frame of "
            "reference coordinate system"
        )
    angle = np.arctan2(-rotation[0, 1], rotation[0, 0])
    if in_degrees:
        return np.degrees(angle)
    else:
        return angle


def build_transform(
        image_position: Sequence[float],
        image_orientation: Sequence[float],
        pixel_spacing: Sequence[float],
    ) -> np.ndarray:
    """Builds an affine transformation matrix for mapping coordinates in the
    two dimensional pixel matrix into the three dimensional frame of reference.

    Parameters
    ----------
    image_position: Sequence[float]
        Position of the slice (image or frame) in the Frame of Reference, i.e.,
        the offset of the top left pixel in the pixel matrix from the
        origin of the reference coordinate system along the X, Y, and Z axis
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference
    pixel_spacing: Sequence[float]
        Spacing between pixels in millimeter unit along the column direction
        (first value: spacing between rows, vertical, top to bottom,
        increasing Row index) and the rows direction (second value: spacing
        between columns: horizontal, left to right, increasing Column index)

    Returns
    -------
    numpy.ndarray
        4 x 4 affine transformation matrix

    """
    x_offset = float(image_position[0])
    y_offset = float(image_position[1])
    z_offset = float(image_position[2])
    translation = np.array([x_offset, y_offset, z_offset])
    rotation = create_rotation_matrix(image_orientation)
    column_spacing = float(pixel_spacing[0])  # column direction (between rows)
    row_spacing = float(pixel_spacing[1])  # row direction (between columns)
    rotation[:, 0] *= row_spacing
    rotation[:, 1] *= column_spacing
    # 4x4 transformation matrix
    return np.row_stack(
        [
            np.column_stack([
                rotation,
                translation,
            ]),
            [0.0, 0.0, 0.0, 1.0]
        ]
    )


def build_inverse_transform(
        image_position: Sequence[float],
        image_orientation: Sequence[float],
        pixel_spacing: Sequence[float],
        spacing_between_slices: float = 1.0
    ) -> np.ndarray:
    """Builds an inverse of an affine transformation matrix for mapping
    coordinates from the three dimensional frame of reference into the two
    dimensional pixel matrix.

    Parameters
    ----------
    image_position: Sequence[float]
        Position of the slice (image or frame) in the Frame of Reference, i.e.,
        the offset of the top left pixel in the pixel matrix from the
        origin of the reference coordinate system along the X, Y, and Z axis
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference
    pixel_spacing: Sequence[float]
        Spacing between pixels in millimeter unit along the column direction
        (first value: spacing between rows, vertical, top to bottom,
        increasing Row index) and the rows direction (second value: spacing
        between columns: horizontal, left to right, increasing Column index)
    spacing_between_slices: float
        Distance (in the coordinate defined by the Frame of Reference) between
        neighboring slices. Default: 1

    Returns
    -------
    numpy.ndarray
        4 x 4 affine transformation matrix

    """
    x_offset = float(image_position[0])
    y_offset = float(image_position[1])
    z_offset = float(image_position[2])
    translation = np.array([x_offset, y_offset, z_offset])

    rotation = create_rotation_matrix(image_orientation)
    column_spacing = float(pixel_spacing[0])  # column direction (between rows)
    row_spacing = float(pixel_spacing[1])  # row direction (between columns)
    rotation[:, 0] *= row_spacing
    rotation[:, 1] *= column_spacing
    rotation[:, 2] *= spacing_between_slices
    inv_rotation = np.linalg.inv(rotation)
    # 4x4 transformation matrix
    return np.row_stack(
        [
            np.column_stack([
                inv_rotation,
                -np.dot(inv_rotation, translation)
            ]),
            [0.0, 0.0, 0.0, 1.0]
        ]
    )


def apply_transform(
        coordinate: Sequence[float],
        affine: np.ndarray
    ) -> Tuple[float, float, float]:
    """Applies an affine transformation matrix to a pixel matrix coordinate
    to obtain a coordinate in the three-dimensional frame of reference.

    Parameters
    ----------
    coordinate: Sequence[float]
        (Column, Row) coordinate in the Total Pixel Matrix in pixel unit at
        sub-pixel resolution.
    affine: numpy.ndarray
        4 x 4 affine transformation matrix

    Returns
    -------
    Tuple[float, float, float]
        (X, Y, Z) coordinate in the coordinate system defined by the
        Frame of Reference

    """
    column_offset = float(coordinate[0])
    row_offset = float(coordinate[1])
    pixel_matrix_coordinate = np.array([[column_offset, row_offset, 0.0, 1.0]])
    physical_coordinate = np.dot(affine, pixel_matrix_coordinate.T)
    return tuple(physical_coordinate[:3].flatten().tolist())


def apply_inverse_transform(
        coordinate: Sequence[float],
        affine: np.ndarray
    ) -> Tuple[float, float, float]:
    """Applies the inverse of an affine transformation matrix to a
    coordinate in the three-dimensional frame of reference to obtain a pixel
    matrix coordinate.

    Parameters
    ----------
    coordinate: Sequence[float]
        (X, Y, Z) coordinate in the coordinate system defined by the
        Frame of Reference
    affine: numpy.ndarray
        4 x 4 affine transformation matrix

    Returns
    -------
    Tuple[float, float, float]
        (Column, Row, Slice) coordinate, where the `Column` and `Row` values
        relate to the Total Pixel Matrix in pixel units at sub-pixel resolution
        and the `Slice` value represents the signed distance of the input
        coordinate in the direction normal to the plane of the Total Pixel
        Matrix represented in units of the given spacing between slices.
        The `Row` and `Column` values are constrained by the dimension of the
        Total Pixel Matrix. Note, however, that in general, the resulting
        coordinate may not lie within the imaging plane, and consequently the
        `Slice` value may be non-zero.

    """
    x = float(coordinate[0])
    y = float(coordinate[1])
    z = float(coordinate[2])
    physical_coordinate = np.array([[x, y, z, 1.0]])
    pixel_matrix_coordinate = np.dot(affine, physical_coordinate.T)
    return tuple(pixel_matrix_coordinate[:3].flatten().tolist())


def map_pixel_into_coordinate_system(
        coordinate: Sequence[float],
        image_position: Sequence[float],
        image_orientation: Sequence[float],
        pixel_spacing: Sequence[float],
    ) -> Tuple[float, float, float]:
    """Maps a coordinate in the pixel matrix into the physical coordinate
    system (e.g., Slide or Patient) defined by a frame of reference.

    Parameters
    ----------
    coordinate: Sequence[float]
        (Column, Row) coordinate in the Total Pixel Matrix in pixel unit at
        sub-pixel resolution.
    image_position: Sequence[float]
        Position of the slice (image or frame) in the Frame of Reference, i.e.,
        the offset of the top left pixel in the Total Pixel Matrix from the
        origin of the reference coordinate system along the X, Y, and Z axis
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference
    pixel_spacing: Sequence[float]
        Spacing between pixels in millimeter unit along the column direction
        (first value: spacing between rows, vertical, top to bottom,
        increasing Row index) and the row direction (second value: spacing
        between columns: horizontal, left to right, increasing Column index)

    Returns
    -------
    Tuple[float, float, float]
        (X, Y, Z) coordinate in the coordinate system defined by the
        Frame of Reference

    Note
    ----
    This function is a convenient wrapper around ``build_transform()`` and
    ``apply_transform()``. When mapping a large number of coordinates,
    consider using the underlying functions directly for speedup.

    """
    affine = build_transform(
        image_position=image_position,
        image_orientation=image_orientation,
        pixel_spacing=pixel_spacing
    )
    return apply_transform(coordinate, affine=affine)


def map_coordinate_into_pixel_matrix(
        coordinate: Sequence[float],
        image_position: Sequence[float],
        image_orientation: Sequence[float],
        pixel_spacing: Sequence[float],
        spacing_between_slices: float = 1.0,
    ) -> Tuple[float, float, float]:
    """Maps a coordinate in the physical coordinate system (e.g., Slide or
    Patient) into the pixel matrix.

    Parameters
    ----------
    coordinate: Sequence[float]
        (X, Y, Z) coordinate in the coordinate system in millimeter unit.
    image_position: Sequence[float]
        Position of the slice (image or frame) in the Frame of Reference, i.e.,
        the offset of the top left pixel in the Total Pixel matrix from the
        origin of the reference coordinate system along the X, Y, and Z axis
    image_orientation: Sequence[float]
        Cosines of the row direction (first triplet: horizontal, left to right,
        increasing Column index) and the column direction (second triplet:
        vertical, top to bottom, increasing Row index) direction expressed in
        the three-dimensional patient or slide coordinate system defined by the
        Frame of Reference
    pixel_spacing: Sequence[float]
        Spacing between pixels in millimeter unit along the column direction
        (first value: spacing between rows, vertical, top to bottom,
        increasing Row index) and the rows direction (second value: spacing
        between columns: horizontal, left to right, increasing Column index)
    spacing_between_slices: float, optional
        Distance (in the coordinate defined by the Frame of Reference) between
        neighboring slices. Default: ``1.0``

    Returns
    -------
    Tuple[float, float, float]
        (Column, Row, Slice) coordinate. ``Column`` and ``Row`` are pixel
        coordinates in the Total Pixel Matrix, ``Slice`` represents the signed
        distance of the input coordinate in the direction normal to the plane
        of the Total Pixel Matrix represented in units of the given spacing
        between slices. If the ``Slice`` coordinate is 0.0, then the input
        coordinate lies in the imaging plane, otherwise it lies off the plane
        of the Total Pixel Matrix and ``Column`` and ``Row`` may be interpreted
        as the projections of the input coordinate onto the imaging plane.

    Note
    ----
    This function is a convenient wrapper around ``build_inverse_transform()``
    and ``apply_inverse_transform()``. When mapping a large number of
    coordinates, consider using the underlying functions directly for speedup.

    """
    affine = build_inverse_transform(
        image_position=image_position,
        image_orientation=image_orientation,
        pixel_spacing=pixel_spacing,
        spacing_between_slices=spacing_between_slices
    )
    return apply_inverse_transform(coordinate, affine=affine)
