import os
import leafmap
import solara
import geopandas as gpd
import tempfile
import shutil
import json
from urllib.parse import unquote
import time


# Reactive variables
rois_count = solara.reactive(0)
rois_selected = solara.reactive(None)
success_message = solara.reactive("")  # To store the success message
redirect_flag = solara.reactive(False)  # To control redirection

def add_widgets(m):
    def handle_click(**kwargs):
        if kwargs.get("type") == "mousemove" or kwargs.get("type") == "mouseout" or kwargs.get("type") == "mouseover":
            setattr(m, "zoom_to_layer", False)
            
            rois = m.user_rois
            if not rois:
                rois_count.value = 0
            else:
                rois_count.value = len(rois['features'])
                rois_selected.value = rois

    m.on_interaction(handle_click)

zoom = solara.reactive(12)
center = solara.reactive((-5.18804, -37.3441))
rois = solara.reactive(None)

class Map(leafmap.Map):
    def __init__(self, **kwargs):
        kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        self.add_basemap("Esri.WorldImagery")
        self.add_layer_manager(opened=False)
        add_widgets(self)

def on_button_click(project_name, username):
    if not rois_selected.value:
        success_message.value = "No ROIs selected. Please select at least one ROI."
        return

    out_dir = os.path.abspath(f"/data/{project_name}/{username}/rois")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    else:
        shutil.rmtree(out_dir)
        os.makedirs(out_dir)
    
    for i, roi in enumerate(rois_selected.value['features']):
        roi_filename = os.path.join(out_dir, f"roi_{i}.json")
        with open(roi_filename, 'w') as f:
            json.dump(roi, f)
        print(f"Saved ROI {i} to {roi_filename}")
    
    # Set the success message and trigger redirection
    success_message.value = f"Successfully saved {rois_count.value} ROIs to {out_dir}!"
    redirect_flag.value = True

@solara.component
def RoisButton(project_name, username):
    solara.Button("SAVE ROIS", on_click=lambda: on_button_click(project_name, username), style={"display": "inline", "width": "200px"})

@solara.component
def Page():
    # Use the router to access the query parameters
    router = solara.use_router()
    query_params = router.search  # Retrieves the query string from the URL

    # Parse the query string into a dictionary
    params = {}
    if query_params:
        params = dict(param.partition('=')[::2] for param in query_params.split('&') if '=' in param)
    project_name = params.get("project_name", "default_project")
    project_name = unquote(project_name)
    username = params.get("username", "default_user")  # Get username from Flask or default

    # Handle the redirection
    if redirect_flag.value:
        # This will render a script tag that performs the redirect
        solara.HTML("script", unsafe_innerHTML=f"""
            setTimeout(function() {{
                window.location.href = '/projects/{project_name}/create';
            }}, 1000);  // 1 second delay
        """)
    
    solara.Text("Select the region of interest (ROI).", style={"margin-left": "10px"})
    solara.Text(f"Selected Rois: {rois_count.value}", style={"margin-left": "10px"})
    RoisButton(project_name=project_name, username=username)
    
    if success_message.value:
        solara.Text(success_message.value, style={"margin-left": "10px", "color": "green", "font-weight": "bold"})
        if redirect_flag.value:
            solara.Text("Redirecting to the main page...", style={"margin-left": "10px"})
    
    with solara.Column(style={"min-width": "500px"}):
        m = Map.element(  # type: ignore
            zoom=zoom.value,
            on_zoom=zoom.set,
            center=center.value,
            on_center=center.set,
            scroll_wheel_zoom=True,
            toolbar_ctrl=False,
            data_ctrl=False,    
            height="900px",
        )
        m