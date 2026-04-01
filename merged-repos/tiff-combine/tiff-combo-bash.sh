#!/bin/bash

# IMPORTANT: This script combines TIFF files in the order they are returned by the filesystem, which might not be the order you expect (it's often, but not always, alphabetical). If the order of the pages is important, you may need to modify the script to ensure the files are combined in the desired order.

# Todo: define order of files (alpha by name)
# Todo: try this in cygwin

tiffcp /path_to_your_directory/*.tif combined_output.tif
