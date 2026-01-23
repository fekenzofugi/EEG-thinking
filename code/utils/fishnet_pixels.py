import ee
import numpy as np

def fishnet_pixels(roi, overlap=10, BUFFER=1270): 

    print(f"Divinding ROI into fishnet rois with overlap: {overlap} and buffer: {BUFFER}")

    bounds = roi.bounds()
    coords = bounds.coordinates().getInfo()[0]

    points = []
    for i in range(len(coords) -1):
        coord = coords[i]
        point = ee.Geometry.Point(coord)
        points.append(point)

    min_lat = coords[0][0]
    max_lat = coords[1][0]
    min_lon = coords[0][1]
    max_lon = coords[3][1]

    geometries = []

    bl_point = points[0]
    roi = bl_point.buffer(BUFFER).bounds()
    bounds = roi.bounds()
    coords = bounds.coordinates().getInfo()[0]

    initial_coords = coords[2]
    initial_point = ee.Geometry.Point(initial_coords)   
    initial_roi = initial_point.buffer(BUFFER).bounds()
    initial_centroid = initial_roi.centroid(1).coordinates().getInfo()
    initial_bounds = initial_roi.bounds()
    initial_coords = initial_bounds.coordinates().getInfo()[0]

    col_coord = [initial_centroid[0], initial_coords[3][1]]
    i = 1
    col_flag = True
    flag = True
    # COLUMN
    counter = 0
    while col_coord[1] < max_lon or col_flag == True:
        row_coord = [initial_coords[2][0], initial_centroid[1]]
        j = 1
        row_list = [initial_roi]
        while row_coord[0] < max_lat or flag == True:
            point = ee.Geometry.Point(row_coord)
            if j % 2 == 0 :
                roi = point.buffer(BUFFER).bounds()
                bounds = roi.bounds()
                row_coords = bounds.coordinates().getInfo()[0]
                row_list.append(roi)
            else:
                roi = point.buffer(BUFFER - overlap).bounds()
                bounds = roi.bounds()
                row_coords = bounds.coordinates().getInfo()[0]

            row_coord = [row_coords[1][0], initial_centroid[1]]

            if j % 2 != 0 and row_coord[0] >= max_lat:
                flag = True
            else:
                flag = False
            j+=1
        geometries.append(row_list)

        if col_coord[1] >= max_lon and counter==1:
            col_flag = True
            break
        else:
            point = ee.Geometry.Point(col_coord)
            roi = point.buffer(BUFFER - overlap).bounds()
            bounds = roi.bounds()
            initial_centroid = roi.centroid(1).coordinates().getInfo()
            initial_coords = bounds.coordinates().getInfo()[0]
            col_coord = [initial_centroid[0], initial_coords[3][1]]

            point = ee.Geometry.Point(col_coord)
            roi = point.buffer(BUFFER).bounds()
            bounds = roi.bounds()
            initial_centroid = roi.centroid(1).coordinates().getInfo()
            initial_coords = bounds.coordinates().getInfo()[0]
            col_coord = [initial_centroid[0], initial_coords[3][1]]
            initial_roi = roi
            if col_coord[1] >= max_lon:
                col_flag = True
                counter += 1
            else:
                col_flag = False

            i+=1
    
    geometries = np.array(geometries)
    print("Fishnet Geometries: ", geometries.shape)
    print(f"Number of Rows: {geometries.shape[0]}")
    print(f"Number of Columns: {geometries.shape[1]}")

    return geometries