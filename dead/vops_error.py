#vops_error.py

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class BarcodeError(Error):
    """Exception raised when a barcode is not present or otherwise invalid.
    """

    def __init__(self):
        pass

class CornerNotFoundError(Error):
    """Exception raised when an upper left corner could not be found.
    """

    def __init__(self):
        pass

class ReconciliationError(Error):
    """Exception raised when a ballot image's vops array 
       cannot be aligned with the vops array of a reference ballot image.
    """

    def __init__(self):
        pass

class NoImageReadFromFileError(Error):
    """Exception raised when cv2 returns no image.
    """

    def __init__(self):
        pass

class InvalidBoxOffsetError(Error):
    """Exception raised from process boxes when offset unreasonable."""

    def __init__(self):
        pass
    
