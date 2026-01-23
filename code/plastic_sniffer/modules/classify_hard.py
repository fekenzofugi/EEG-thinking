
#Bandas do satelite
AERO = 0
B = 1
G = 2
R = 3
REDE1 = 4
REDE2 = 5
REDE3 = 6
NIR = 7
REDE4 = 8
WATERVAPOR = 9
SWIR1 = 10
SWIR2 = 11
NDVI_band = 12
PMLI_band = 13
BSI_band = 14
scoreplus_band = 15
senseiv_band = 16
PGI_band = 140
BSPI_band = 150
NDWI_band = 160
NDMI_band = 170
APGI_band = 180

def points_5(obj: dict) -> tuple[list, list]:
    """
    This function returns the points_5 of the object
    """
    xs = [int(round(obj['bbox'][0] + 1*obj['bbox'][2]/4)), int(round(obj['bbox'][0] + 3*obj['bbox'][2]/4)),
            int(round(obj['bbox'][0] + 2*obj['bbox'][2]/4)),
            int(round(obj['bbox'][0] + 1*obj['bbox'][2]/4)), int(round(obj['bbox'][0] + 3*obj['bbox'][2]/4))]
    ys = [int(round(obj['bbox'][1] + 1*obj['bbox'][3]/4)), int(round(obj['bbox'][1] + 1*obj['bbox'][3]/4)),
            int(round(obj['bbox'][1] + 2*obj['bbox'][3]/4)),
            int(round(obj['bbox'][1] + 3*obj['bbox'][3]/4)), int(round(obj['bbox'][1] + 3*obj['bbox'][3]/4))]
    points = []
    for j in ys:
        for i in xs:
            if obj['segmentation'][j][i]:
                points.append((j, i))
    return points

def points_all(obj: dict) -> tuple[list, list]:
    """
    This function returns all the points of the object in the format (y, x)
    """
    xs = range(int(obj['bbox'][0]), int(obj['bbox'][0] + obj['bbox'][2]))
    ys = range(int(obj['bbox'][1]), int(obj['bbox'][1] + obj['bbox'][3]))
    points = []
    for j in ys:
        for i in xs:
            if obj['segmentation'][j][i]:
                points.append((j, i))
    return points

def PMLI(img, obj : dict) -> float:
    """
    This function calculates de PMLI index to a given object.
    The PMLI index is calculated by the following formula:
        (float(img[SWIR1][y][x]) - float(img[R][y][x])) / (float(img[SWIR1][y][x]) + float(img[R][y][x]))
    """
    points = points_all(obj)
    
    # Calculate the PMLI index
    pmlis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            pmlis.append(img[PMLI_band][j][i])
        except:
            pmlis.append((float(img[SWIR1][j][i]) - float(img[R][j][i])) / (float(img[SWIR1][j][i]) + float(img[R][j][i])))
    return sum(pmlis)/len(pmlis) if pmlis else 0

def NDVI(img, obj : dict) -> float:
    """
    This function calculates de NDVI index to a given object.
    The NDVI index is calculated by the following formula:
        (float(img[NIR][y][x]) - float(img[R][y][x])) / (float(img[NIR][y][x]) + float(img[R][y][x]))
    """
    points = points_all(obj)
    
    # Calculate the NDVI index
    ndvis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            ndvis.append(img[NDVI_band][j][i])
        except:
            ndvis.append((float(img[NIR][j][i]) - float(img[R][j][i])) / (float(img[NIR][j][i]) + float(img[R][j][i])))
    return sum(ndvis)/len(ndvis) if ndvis else 0


def PGI(img, obj : dict) -> float:
    pass

def APGI(img, obj : dict) -> float:
    """
    APGI = 100 * AERO * RED * ((2 * NIR - RED - SWIR2)/(2 * NIR + RED + SWIR2))
    """

    points = points_all(obj)
    
    # Calculate the APGI index
    apgis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            apgis.append(img[APGI_band][j][i])
        except:
            apgis.append(100 * float(img[AERO][j][i]) * float(img[R][j][i]) * (((2 * float(img[NIR][j][i])) - float(img[R][j][i]) - float(img[SWIR2][j][i])) / ((2 * float(img[NIR][j][i])) + float(img[R][j][i]) + float(img[SWIR2][j][i]))))
    return sum(apgis)/len(apgis)/(10**8) if apgis else 0


def RPGI(img, obj : dict) -> float:
    pass

def NDMI(img, obj : dict) -> float:
    """
    This function calculates de NDMI index to a given object.
    The NDMI index is calculated by the following formula:
    
    Sentinel-2 NDMI = (B08 - B11) / (B08 + B11)
    """

    points = points_all(obj)
    
    # Calculate the NDVI index
    ndmis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            ndmis.append(img[NDMI_band][j][i])
        except:
            ndmis.append((float(img[NIR][j][i]) - float(img[SWIR1][j][i])) / (float(img[NIR][j][i]) + float(img[SWIR1][j][i])))
    return sum(ndmis)/len(ndmis) if ndmis else 0

def NDWI(img, obj : dict) -> float:
    """
    This function calculates de NDWI index to a given object.
    The NDWI index is calculated by the following formula:
    
    Sentinel-2 NDWI = (B03 - B08) / (B03 + B08)
    """

    points = points_all(obj)
    
    # Calculate the NDVI index
    ndwis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            ndwis.append(img[NDWI_band][j][i])
        except:
            ndwis.append((float(img[G][j][i]) - float(img[NIR][j][i])) / (float(img[G][j][i]) + float(img[NIR][j][i])))
    return sum(ndwis)/len(ndwis) if ndwis else 0


def BSPI(img, obj : dict) -> float:
    """
    This function calculates de BSI index to a given object.
    The BSI index is calculated by the following formula:
    (img[SWIR1][y][x] - img[WATERVAPOR][y][x]) / (img[SWIR1][y][x] + img[WATERVAPOR][y][x])
    """
    points = points_all(obj)
    
    # Calculate the BSI index
    bspis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            bspis.append(img[BSPI_band][j][i])
        except:
            bspis.append((float(img[SWIR1][j][i]) - float(img[WATERVAPOR][j][i])) / (1610 - 1375))
    return (((sum(bspis)/len(bspis))+12)/24) if bspis else 0

def BSI(img, obj : dict) -> float:
    """
    This function calculates de BSI index to a given object.
    The BSI index is calculated by the following formula:
    
    """
    points = points_all(obj)
    
    # Calculate the BSI index
    bsis = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            bsis.append(img[BSI_band][j][i])
        except:
            bsis.append(((float(img[SWIR2][j][i]) + float(img[R][j][i])) - (float(img[NIR][j][i]) + float(img[B][j][i]))) / ((float(img[SWIR2][j][i]) + float(img[R][j][i])) + (float(img[NIR][j][i]) + float(img[B][j][i]))))
    return sum(bsis)/len(bsis) if bsis else 0

def scoreplus(img, obj : dict) -> float:
    """
    This function calculates the scoreplus of the object in the image.
    """
    points = points_all(obj)
    
    # Calculate the cloud and shadow percentage
    cloud = []
    shadow = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            value = img[scoreplus_band][j][i]
            if value == 1:
                cloud.append(1)
                shadow.append(0)
            elif value == 3:
                cloud.append(0)
                shadow.append(1)
            else:
                cloud.append(0)
                shadow.append(0)
        except:
            cloud.append(0)
            shadow.append(0)
    return (sum(cloud)/len(cloud) if cloud else 0, sum(shadow)/len(shadow) if shadow else 0)

def senseiv(img, obj : dict) -> float:
    """
    This function calculates the senseiv of the object in the image.
    """
    points = points_all(obj)
    
    # Calculate the BSI index
    cloud = []
    shadow = []
    for a in points:
        j = a[0]
        i = a[1]
        try:
            value = img[senseiv_band][j][i]
            if value == 1 or value == 2:
                cloud.append(1)
                shadow.append(0)
            elif value == 3:
                cloud.append(0)
                shadow.append(1)
            else:
                cloud.append(0)
                shadow.append(0)
        except:
            cloud.append(0)
            shadow.append(0)
    return (sum(cloud)/len(cloud) if cloud else 0, sum(shadow)/len(shadow) if shadow else 0)

def cloud(img, obj : dict) -> tuple[float, float]:
    """
    This function returns the percentage of cloud and shadow in the object.
    """

    cloud_1, shadow_1 = scoreplus(img, obj)
    cloud_2, shadow_2 = senseiv(img, obj)
    return (cloud_1 + cloud_2)/2, (shadow_1 + shadow_2)/2

def plastic(indices : list[float]) -> bool:
    """
    This function classifies the object as plastic or not.
    The classification is based on the PMLI, NDVI and BSI indexes.
    """

    #list_indices = [PMLI, NDVI, BSI, NBSPI]

    pmli = indices[0]
    ndvi = indices[1]
    bsi = indices[2]
    nbspi = indices[3]

    cond1 = pmli <= 0.4
    cond2 = ndvi <= 0.4
    cond3 = bsi <= 6
    cond4 =  0.5 < nbspi < 5 


    return cond1 and cond2 and cond3 and cond4 #TODO change the return to the correct classification

def plant(indices : list[float]) -> bool:
    """
    This function classifies the object as plastic or not.
    The classification is based on the PMLI, NDVI and BSI indexes.
    """
    #list_indices = [PMLI, NDVI, BSI, NBSPI]
    pmli = indices[0]
    ndvi = indices[1]
    bsi = indices[2]
    nbspi = indices[3]

    cond1 = pmli <= 0.4 or True
    cond2 = ndvi >= 0.3
    cond3 = bsi <= 6 or True
    cond4 = nbspi <= 0.5 

    return cond1 and cond2 and cond3 and cond4 #TODO change the return to the correct classification

def soil(indices : list[float]) -> bool:
    """
    This function classifies the object as soil or not.
    """

    #list_indices = [PMLI, NDVI, BSI, NBSPI]
    pmli = indices[0]
    ndvi = indices[1]
    bsi = indices[2]
    nbspi = indices[3]

    cond1 = pmli <= 0.4 or True
    cond2 = ndvi >= 0.3
    cond3 = bsi <= 6 or True
    cond4 = nbspi > 6 

    return False

def hard_classify(img, object : dict) -> int:
    """
    This function classifies the objects in the image.


    """
    _ , list_indices = indexes(img, object)
    list_class = ['soil', 'herb', 'plastic', 'grow', 'vegetation', 'cloud', 'florest', 'other']

    #list_indices = [PMLI, NDVI, BSI, NBSPI]
    if cloud(img, object)[0] > 0.1:
        return 5
    # elif plant(list_indices):
    #     return 4
    # elif plastic(list_indices):
    #     return 2
    else:
        return 0
    

def reflectance(img, obj : dict) -> tuple[list[float]]:
    """
    Calculate the reflectance media of the object in the image.

    Args:
        img (np.array): The image
        obj (dict): The object

    Returns:
        tuple[list[float]]: The wavelengths and the reflectances
    """    
    # List with the wavelengths of the Sentinel-2 bands (in nanometers)
    sentinel2_wavelengths = [
        443,  # Coastal Aerosol B1
        490,  # Blue B2
        560,  # Green B3
        665,  # Red B4
        705,  # Vegetation Red Edge 1 B5
        740,  # Vegetation Red Edge 2 B6
        783,  # Vegetation Red Edge 3 B7
        842,  # NIR (Near Infrared) B8
        865,  # Vegetation Red Edge 4 B8A
        945,  # Water Vapor B9
        1610, # SWIR 1
        2190  # SWIR 2
    ]

    # sentinel2_wavelengths = [i for i in range(img.shape[0])]
    points = points_all(obj)
    reflectances = [0 for _ in range(len(sentinel2_wavelengths))]
    for point in points:
        j = point[0]
        i = point[1]
        for band in range(len(sentinel2_wavelengths)):
            reflectances[band] += img[band][j][i]
    reflectances = [r/len(points) for r in reflectances]
    return sentinel2_wavelengths, reflectances

def indexes(img, obj : dict) -> tuple[list[str], list[float]]:
    """
    Calculate the indexes of the object in the image.

    Args:
        img (np.array): The image
        obj (dict): The object

    Returns:
        tuple[list[str], list[float]]: The names of the indexes and the values
    """    
    # List with the indexes
    indexes = [
        'PMLI',
        'NDVI',
        'BSI',
        'BSPI',
        'NDWI',
        'NDMI',
        'APGI',
        'CLOUD',
        'SHADOW'
    ]

    # normalized_bands = img.copy()
    # bandas_para_normalizar = [PMLI_band, NDVI_band, BSI_band]

    # # Aplicar normalização apenas nas bandas selecionadas
    # for i in bandas_para_normalizar:
    #     band = img[i]  # Índices do Rasterio começam em 1, do NumPy em 0
    #     min_val, max_val = band.min(), band.max()
    #     normalized_bands[i] = (band - min_val) / (max_val - min_val)
    CLOUD, SHADOW = cloud(img, obj)

    values = [
        PMLI(img, obj),
        NDVI(img, obj),
        BSI(img, obj),
        BSPI(img, obj),
        NDWI(img, obj),
        NDMI(img, obj),
        APGI(img, obj),
        CLOUD,
        SHADOW
    ]

    return indexes, values