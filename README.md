# GeoHuman
A semi-automatic labeling tool for remote sensing imagery with a multimodal dataset generator.

## Features
- **Dataset Generator:** A web app that creates a dataset of multimodal remote sensing images.
- **Fast Downloading:** Downloads hundreds of images quickly. Based on [this article](https://gorelick.medium.com/fast-er-downloads-a2abd512aa26) by Noel Gorelick.
- **GIF Generator:** Each tile in the dataset includes a GIF over time.
- **Segmentation:** Utilizes the SAM model by META.
- **Hard Classification:** Classification based on spectral indices.
- **Semi-Automatic Labeling:** Assists in labeling images by combining automated processes with human input to improve accuracy and efficiency.

## Dependencies
```sh
pip install -r requirements.txt
```
Using Anaconda:
```sh
conda create -n <ENV_NAME>
conda activate <ENV_NAME>
conda install -c conda-forge python=3.12.3 geopandas=0.14.4 pandas=2.1.4 numpy=1.26.4 geemap=0.34.1 earthengine-api=1.4.2 rasterio=1.3.11 folium=0.17.0 matplotlib opencv pillow retry solara leafmap flask scikit-image python-dotenv h5py scikit-learn flask-SQLAlchemy -y
pip3 install solara==1.44.0 torch segmentation_models_pytorch transformers torchmetrics wandb pyOpenSSL==24.3.0 mlstac flask_migrate flask_sessions guinicorn
pip3 install torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Dataset Generator
A web application that allows users to create training (sample tiles) and validation (fishnet of ROIs) datasets. Downloads are made through Google Earth Engine, currently supporting Sentinel-1, Sentinel-2, and fused images. The app uses parallel programming to optimize time efficiency.

Users can select different regions of interest using an interactive map (running a `solara` app on a different process at `localhost:5001`), specify a time period, coordinate reference system, spectral indices, the number of tiles (for training) or overlap of pixels (for validation), and apply cloud masks. The application can also segment dataset images (using SAM by Meta) and label them using a semi-automatic method called `GeoHuman`.

To access the app on `dataset/code` & run:
```sh
python3 main.py
```
Access the web application at `localhost:5000`.

On the registration page, add your Google Earth Engine project ID. If you don't have one, watch this [tutorial](https://www.youtube.com/watch?v=fiqeSRzG_8k) on creating a GEE project.

## SAM Model
Click the links below to download the checkpoint for the corresponding model type:
- **`default` or `vit_h`: [ViT-H SAM model](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth)**
- `vit_l`: [ViT-L SAM model](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth)
- `vit_b`: [ViT-B SAM model](https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth)

Add the model to the `Checkpoints` directory.