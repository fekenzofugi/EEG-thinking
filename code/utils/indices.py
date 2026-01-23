def calculate_pmli(img):
    '''
    Plastic-Mulched landcover index
    '''
    pmli = img.expression('((SWIR1 - R)/(SWIR1 + R))',
    { 
    'R': img.select('B4'),
    'SWIR1': img.select('B11'),
    'SWIR2': img.select('B12')
    }).rename('PMLI')
    return img.addBands(pmli)

def calculate_bsi(img):
    '''
    3. Bare Soil Index (BSI)

    Purpose: BSI is utilized to identify bare soil areas by leveraging spectral differences between soil and vegetation.

    Significance: Higher BSI values indicate areas with bare soil [4].
    '''
    bsi = img.expression(
        "((B12 + B4) - (B8 + B2)) / ((B12 + B4) + (B8 + B2))",
        {
            'B2': img.select('B2'),  
            'B4': img.select('B4'),  
            'B8': img.select('B8'),  
            'B12': img.select('B12') 
        }
    ).rename('BSI')
    return img.addBands(bsi)

def calculate_ndvi(img):
    ndvi = img.expression(
        "(B8 - B4) / (B8 + B4)",
        {  
            'B4': img.select('B4'),  
            'B8': img.select('B8'),  
        }
    ).rename('NDVI')
    return img.addBands(ndvi)

def calculate_indices(image, indices):
    if indices != []:
        for index in indices:
            if index == 'NDVI':
                image = calculate_ndvi(image)
            elif index == 'PMLI':
                image = calculate_pmli(image)
            elif index == 'BSI':
                image = calculate_bsi(image)
    return image