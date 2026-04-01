# TODO

## Features to add

- [ ] **Image straightening**: Add rotation correction to `crop-images.py`. Use Hough Line Transform to detect the dominant edge angle, then rotate/straighten the crop before saving. Consider filtering lines by orientation (near-horizontal only) and weighting by line length to avoid noise skewing the angle. Output suffix: `-cropped-straightened`.
- [ ] **Threshold tuning**: Currently hardcoded at `253`. Scanner backgrounds are always pure white (255), so the gap between background and near-white document content is very narrow. Lowering this risks cropping into content. Needs careful testing with real scans before making it configurable — wrong values will silently produce bad crops.
- [ ] Consider adding a simple test image + expected output to verify cropping behavior across changes.
