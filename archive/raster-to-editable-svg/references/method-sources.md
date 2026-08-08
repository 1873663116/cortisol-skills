# Method sources

The workflow was informed by the inspectable source-to-asset structure in [`jkc66/custom-icons-skill`](https://github.com/jkc66/custom-icons-skill): isolated intermediates, traced-vector branching, structural validation, and rendered visual inspection. No source code from that project is bundled here.

The mask, contour, curve-fitting, and pilot-gate process follows these primary references:

- Peter Selinger, [Potrace](https://potrace.sourceforge.net/potrace.pdf)
- Philip J. Schneider, [Automatically Fitting Digitized Curves](https://lhf.impa.br/cursos/tmg/Schneider-1990.pdf)
- [OpenCV structural analysis](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)
- [scikit-image marching-squares contours](https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.find_contours)
- [SciPy interpolation and smoothing splines](https://docs.scipy.org/doc/scipy/reference/interpolate.html)
- [Inkscape image tracing guidance](https://inkscape-manuals.readthedocs.io/en/latest/tracing-an-image.html)
