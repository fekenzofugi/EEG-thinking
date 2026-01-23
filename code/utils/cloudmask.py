import numpy as np
import rasterio
import os
import matplotlib.pyplot as plt
from utils.files_info import get_files_info, alphanum_key
from utils.senseiv2.inference import CloudMask
from utils.senseiv2.utils import get_model_files
from utils.senseiv2.constants import SENTINEL2_DESCRIPTORS
import matplotlib.pyplot as plt
import numpy as np


#    All the credits for this code go to the authors of the SEnSeIv2 model.
#    https://github.com/aliFrancis/SEnSeIv2
#    https://ieeexplore.ieee.org/document/10505181


def apply_cloudmask(path, user_choice, device="cpu"):
    print("Applying cloud mask...")

    num_files, ids = get_files_info(path)
    ids = sorted(ids, key=alphanum_key)

    for i in range(num_files):
        src = rasterio.open(
            os.path.join(path, f'{ids[i]}'),
            mode = 'r',
            driver = 'GTiff',
            crs = 'EPSG:4326',
        )

        scene = src.read()
        print(scene.shape)

        input = scene[:12] / 10000

        print(input.shape)

        print(len(SENTINEL2_DESCRIPTORS))

        # Pick pre-trained model from https://huggingface.co/aliFrancis/SEnSeIv2
        # model_name = 'SEnSeIv2-SegFormerB2-alldata-ambiguous'
        # model_name = 'SegFormerB2-S2-unambiguous'
        model_name = 'SEnSeIv2-DeepLabv3-S2-unambiguous'
        # model_name = 'SEnSeIv2-SegFormerB2-S2-ambiguous'
        config, weights = get_model_files(model_name)

        # Lots of options in the kwargs for different settings
        model = CloudMask(config, weights, verbose=True, categorise=True, device=device)

        senselv = model(input,descriptors=SENTINEL2_DESCRIPTORS, stride=357)

        scene = np.concatenate((scene, senselv[np.newaxis, :, :]), axis=0)

        id = ids[i]

        out_path = path + f"/{id}"

        # Check if the input is valid
        if input is None or input.shape[0] == 0:
            print(f"Input for fused_{i} is empty. Skipping...")
            continue

        bands = scene.shape[0]

        # Open a new dataset for writing
        new_dataset = rasterio.open(
            out_path,
            mode='w',
            driver='GTiff',
            height=input.shape[1],
            width=input.shape[2],
            count=bands,
            dtype=input.dtype,
            crs=src.crs,  # Use the CRS from the source dataset
            transform=src.transform  # Use the transform from the source dataset
        )

        try:
            for j in range(bands):
                new_dataset.write(scene[j], j + 1)
        finally:
            new_dataset.close()

#%%%%%%%%%%%%%%%%%%%%%%%%%%%%% Score + Mask%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
import ee

S2_CM_COLLECTION_ID = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"

# The threshold for masking; values between 0.50 and 0.65 generally work well.
# Higher values will remove thin clouds, haze & cirrus shadows.
CLEAR_THRESHOLD = 0.40
NIR_DRK_THRESH = 0.15
CLD_PRJ_DIST = 1
BUFFER = 50

# Use 'cs' or 'cs_cdf', depending on your use case; see docs for guidance.
QA_BAND = 'cs_cdf'

def get_s2_cld_col(aoi, start_date, end_date, S2_COLLECTION_ID, CLOUD_FILTER):
    # Import and filter S2 SR.
    s2_sr_col = (ee.ImageCollection(S2_COLLECTION_ID)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)))

    # Import and filter s2cloudless.
    # Cloud Score+ image collection. Note Cloud Score+ is produced from Sentinel-2
    # Level 1C data and can be applied to either L1C or L2A collections.
    csplus_col = (ee.ImageCollection(S2_CM_COLLECTION_ID)
        .filterBounds(aoi)
        .filterDate(start_date, end_date))

    # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
    return ee.ImageCollection(ee.Join.saveFirst('scoreplus').apply(**{
        'primary': s2_sr_col,
        'secondary': csplus_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))

def add_cloud_bands(img):
    # Get s2cloudless image, subset the cs_cdf band.
    score_plus = ee.Image(img.get('scoreplus')).select(QA_BAND)

    # Condition s2cloudless by the SCORE+ threshold value.
    is_cloud = score_plus.gt(CLEAR_THRESHOLD).Not().rename('clouds')

    # Add the cloud score+ layer and cloud mask as image bands.
    return img.addBands(ee.Image([score_plus, is_cloud]))

def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(NIR_DRK_THRESH*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')))

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, CLD_PRJ_DIST*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))


def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud as value 2 and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').multiply(10).subtract(9).add(img_cloud_shadow.select('shadows').multiply(12)).max(0).min(3)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 10})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    return img_cloud_shadow.addBands(is_cld_shdw)

def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select('cloudmask').Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select('B.*').updateMask(not_cld_shdw)