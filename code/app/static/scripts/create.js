function checkTitle() {
  const titleInput = document.getElementById('title');
  const submitButton = document.getElementById('submit-button');
  submitButton.disabled = titleInput.value.trim() === '';
}

// Initial check in case the form is pre-filled
document.addEventListener('DOMContentLoaded', checkTitle);


// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% DS_TYPE %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
const dsType = document.getElementById('ds_type');

function showNumTiles(value) {
    const numTiles = document.getElementById('num_sample_tiles_container');
    const overlap = document.getElementById('overlap_container');
    if (value.toUpperCase() === 'TRAINING') {
        numTiles.style.display = 'block';
        overlap.style.display = 'none'
    } else {
        numTiles.style.display = 'none';
        overlap.style.display = 'block';
    }
}

// Add event listener for the select element
dsType.addEventListener('change', function () {
    showNumTiles(this.value);
});

// Initial call to set the correct state
showNumTiles(dsType.value);

// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% BANDS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

let bands = []; 
const selectElement = document.getElementsByTagName('select')[1];

function setBandsBasedOnSelection(value) {
  if (value.toUpperCase() === 'SENTINEL-1') {
    bands = ['VH', 'VV'];
  } else if (value.toUpperCase() === 'SENTINEL-2') {
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12'];
  } else if (value.toUpperCase() === 'FUSED') {
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12', 'VV', 'VH'];
  }
}

selectElement.addEventListener('change', function() {
  setBandsBasedOnSelection(this.value);
  updateBandsContainer();
});

// Set default bands based on the initial selection
setBandsBasedOnSelection(selectElement.value);
updateBandsContainer();

function updateBandsContainer() {
  const bandsContainer = document.getElementById('bands-container');
  bandsContainer.innerHTML = '';
  bands.forEach(band => {
    const label = document.createElement('label');
    label.style.marginRight = '10px';
    label.style.marginBottom = '10px';
    label.style.display = 'flex';
    label.style.alignItems = 'start';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = band;
    checkbox.value = band;
    checkbox.style.marginRight = '5px';
    checkbox.style.cursor = 'pointer';
    if (selectElement.value.toUpperCase() === 'SENTINEL-1' || selectElement.value.toUpperCase() === 'FUSED') {
      checkbox.disabled = true;
      checkbox.checked = true;
    }

    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(band));
    bandsContainer.appendChild(label);
  });
}

function selectAllBands(state) {
  const bandsContainer = document.getElementById('bands-container');
  const checkboxes = bandsContainer.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(checkbox => {
    checkbox.checked = state;
  });
}

function updateSelectedBands() {
  const bandsContainer = document.getElementById('bands-container');
  const checkboxes = bandsContainer.querySelectorAll('input[type="checkbox"]:checked');
  const selectedBands = Array.from(checkboxes).map(checkbox => checkbox.value);
  document.getElementById('selected_bands').value = JSON.stringify(selectedBands);
}

// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% INDICES %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
let indices = []; 
const indicesWrapper = document.getElementById('indices-wrapper');

function setIndicesBasedOnSelection(value) {
  if (value.toUpperCase() === 'SENTINEL-1') {
    indices = [];
    indicesWrapper.style.display = 'none';
  } else if (value.toUpperCase() === 'SENTINEL-2') {
    indices = ['NDVI', 'PMLI', 'BSI'];
    indicesWrapper.style.display = 'block';
  } else if (value.toUpperCase() === 'FUSED') {
    indices = ['NDVI', 'PMLI', 'BSI'];
    indicesWrapper.style.display = 'block';
  }
}

selectElement.addEventListener('change', function() {
  setIndicesBasedOnSelection(this.value);
  updateIndicesContainer();
});

// Set default indices based on the initial selection
setIndicesBasedOnSelection(selectElement.value);
updateIndicesContainer();

function updateIndicesContainer() {
  const indicesContainer = document.getElementById('indices-container');

  indicesContainer.innerHTML = '';
  indices.forEach(indice => {
    const label = document.createElement('label');
    label.style.marginRight = '10px';
    label.style.marginBottom = '10px';
    label.style.display = 'flex';
    label.style.alignItems = 'start';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = indice;
    checkbox.value = indice;
    checkbox.style.marginRight = '5px';
    checkbox.style.cursor = 'pointer';
    if (selectElement.value.toUpperCase() === 'SENTINEL-1'){
      checkbox.disabled = true;
      checkbox.checked = true;
    }
    if (selectElement.value.toUpperCase() === 'FUSED') {
      checkbox.disabled = true;
      checkbox.checked = true;
    }

    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(indice));
    indicesContainer.appendChild(label);
  });
}

function selectAllIndices(state) {
  const indicesContainer = document.getElementById('indices-container');
  const checkboxes = indicesContainer.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(checkbox => {
    checkbox.checked = state;
  });
}

function updateSelectedIndices() {
  const indicesContainer = document.getElementById('indices-container');
  const checkboxes = indicesContainer.querySelectorAll('input[type="checkbox"]:checked');
  const selectedIndices = Array.from(checkboxes).map(checkbox => checkbox.value);
  document.getElementById('selected_indices').value = JSON.stringify(selectedIndices);
}

// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% MASKS %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
let masks = []; 
const masksWrapper = document.getElementById('masks-wrapper');  

function setMasksBasedOnSelection(value) {
  if (value.toUpperCase() === 'SENTINEL-1') {
    masks = [];
    masksWrapper.style.display = 'none';
  } else if (value.toUpperCase() === 'SENTINEL-2') {
    masks = ["Score+", "Senseiv"];
    masksWrapper.style.display = 'block';
  } else if (value.toUpperCase() === 'FUSED') {
    masks = ['Score+', 'Senseiv'];
    masksWrapper.style.display = 'block';
  }
}

selectElement.addEventListener('change', function() {
  setMasksBasedOnSelection(this.value);
  updateMasksContainer();
});

setMasksBasedOnSelection(selectElement.value);
updateMasksContainer();

function updateMasksContainer() {
  const masksContainer = document.getElementById('masks-container');
  masksContainer.innerHTML = '';
  masks.forEach(mask => {
    const label = document.createElement('label');
    label.style.marginRight = '10px';
    label.style.marginBottom = '10px';
    label.style.display = 'flex';
    label.style.alignItems = 'start';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = mask;
    checkbox.value = mask;
    checkbox.style.marginRight = '5px';
    checkbox.style.cursor = 'pointer';
    if (selectElement.value.toUpperCase() === 'SENTINEL-1' || selectElement.value.toUpperCase() === 'FUSED') {
      checkbox.disabled = true;
      checkbox.checked = true;
    }

    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(mask));
    masksContainer.appendChild(label);
  });
}

function selectAllMasks(state) {
  const masksContainer = document.getElementById('masks-container');
  const checkboxes = masksContainer.querySelectorAll('input[type="checkbox"]');
  checkboxes.forEach(checkbox => {
    checkbox.checked = state;
  });
}

function updateSelectedMasks() {
  const masksContainer = document.getElementById('masks-container');
  const checkboxes = masksContainer.querySelectorAll('input[type="checkbox"]:checked');
  const selectedMasks = Array.from(checkboxes).map(checkbox => checkbox.value);
  document.getElementById('selected_masks').value = JSON.stringify(selectedMasks);
}


// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% LOADING SPINNER %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function showLoadingSpinner() {
  document.getElementById('loading-overlay').style.display = 'flex';
}

document.querySelector('form').addEventListener('submit', function() {
  showLoadingSpinner();
});
