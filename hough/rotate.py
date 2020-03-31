"""
Worker functions for a parallelizable deskewer.
"""
import logging
import os

import filetype
import fitz
from imageio import imread, imwrite
from scipy.ndimage import interpolation


def rotate(imagelist, out, generator=False):
    """Actually rotates a single file of 1+ images.
    Rotated file has the same name and is placed under the {out} subdirectory
    of the cwd.
    """
    logger = logging.getLogger("hough")
    guess = filetype.guess(imagelist[0][0])
    if guess and guess.mime == "application/pdf":
        newdoc = fitz.open()
    else:
        newdoc = None
    filename = imagelist[0][0]
    filen, ext = os.path.splitext(os.path.basename(filename))
    kind = filetype.guess(filename)
    for image in imagelist:
        page = int(image[1]) if image[1] else ""
        angle = float(image[2]) if image[2] else 0.0
        if not page:
            # single-image file, not a container
            logger.info(f"Rotating {filename}...")
            img = imread(image[0])
            fixed = interpolation.rotate(img, -angle, mode="nearest", reshape=False)
            imwrite(f"{out}/{filen}{ext}", fixed)
        else:
            if kind and kind.mime == "application/pdf":
                doc = fitz.open(image[0])
                imagelist = doc.getPageImageList(page - 1)
                # TODO: Correctly deal with multiple images on a page
                for item in imagelist:
                    xref = item[0]
                    smask = item[1]
                    if smask == 0:
                        imgdict = doc.extractImage(xref)
                        logger.info(
                            f"Rotating {filename} - page {page} - xref {xref}..."
                        )
                        try:
                            img = imread(imgdict["image"])
                            imgext = imgdict["ext"]
                            fixed = interpolation.rotate(
                                img, -angle, mode="nearest", reshape=False
                            )
                            imgbytes = imwrite("<bytes>", fixed, format=imgext)
                            imgdoc = fitz.open(stream=imgbytes, filetype=imgext)
                            rect = imgdoc[0].rect
                            pdfbytes = imgdoc.convertToPDF()
                            imgdoc.close()
                            imgPDF = fitz.open("pdf", pdfbytes)
                            page = newdoc.newPage(width=rect.width, height=rect.height)
                            page.showPDFpage(rect, imgPDF, 0)
                        except ValueError as e:
                            logger.error(
                                f"Skipping rotating {filename} - page {page} - xref {xref}: {e}"
                            )
                    else:
                        logger.error(
                            f"Skipping process {filename} - page {page} - image {xref} (smask=={smask})"
                        )
            # TODO: deal with other multi-image formats
            else:
                logger.error(
                    f"Skipping file {filename} - unknown multi-page file format"
                )
        yield 1
    if newdoc:
        newdoc.save(f"{out}/{filen}{ext}")
