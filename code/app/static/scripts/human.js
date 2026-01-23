function bringToTop(targetElement){
    // put the element at the top of its parent, above all other elements
    let parent = targetElement.parentNode;
    parent.appendChild(targetElement);
}

function bringToBottom(targetElement){
    let parent = targetElement.parentNode.parentNode;
    parent.insertBefore(targetElement, parent.firstChild);
}

let images = document.querySelectorAll('[id^="image"]');
images.forEach(image => {
    bringToBottom(image);
});
images.forEach(image => {
    bringToTop(image);
});


// bring all elements with id starting with line2d_ to the top on hover
let lines = document.querySelectorAll('[id^="line2d_"]');
lines.forEach(line => {
    bringToTop(line);
});

let texts = document.querySelectorAll('[id^="text_"]');
texts.forEach(text => {
    bringToTop(text);
});

// bring all elements with id starting with line2d_ to the top on hover
let paths = document.querySelectorAll('[id^="line2d_"] path');
paths.forEach(element => {
    let originalFill = element.style.fill;
    let parent_id = element.parentNode.id;
    let text = document.getElementById('text_' + parent_id.split('_')[1]);
    let gid = text.childNodes[1].textContent.split(' ')[1];
    let id = text.childNodes[1].textContent.split(' ')[2];
    let object_class = id;
    element.addEventListener('mouseover', () => {
        element.style.cursor = 'pointer';
        element.style.fill = 'blue';
        document.getElementById('user_input').value = gid + ' ' + id;
        document.getElementById('context-label').innerText = "Image: " + gid;
        updateClassesContainer(object_class);
    });
    element.addEventListener('mouseout', () => {
        updateClassesContainer(object_class);
        element.style.fill = originalFill; // Revert to original fill color
    });
});



// Update the classes container based on the current selected class
classes = ['OTHER', 'BARE SOIL', 'HERB', 'MULCHING', 'GROW', 'VEGETATION', 'GREENHOUSE', 'FLOREST', 'UNKNOWN'];	
function updateClassesContainer(current_id) {
const classesContainer = document.getElementById('classes-container');
classesContainer.innerHTML = '';
classes.forEach(img_class => {
    const label = document.createElement('label');
    label.style.marginRight = '10px';
    label.style.marginBottom = '10px';
    label.style.display = 'flex';
    label.style.alignItems = 'start';
    label.style.fontSize = '0.8rem';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = img_class;
    checkbox.value = img_class;
    checkbox.style.marginRight = '5px';
    checkbox.style.cursor = 'pointer';
    if ((current_id == '0' && img_class == 'OTHER') ||
            (current_id == '1' && img_class == 'BARE SOIL') ||
            (current_id == '2' && img_class == 'HERB') ||
            (current_id == '3' && img_class == 'MULCHING') ||
            (current_id == '4' && img_class == 'GROW') ||
            (current_id == '5' && img_class == 'VEGETATION') ||
            (current_id == '6' && img_class == 'GREENHOUSE') ||
            (current_id == '7' && img_class == 'FLOREST') ||
            (current_id == '8' && img_class == 'UNKNOWN')) {
        checkbox.checked = true;
    }

    checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
            // Uncheck all other checkboxes
            const allCheckboxes = classesContainer.querySelectorAll('input[type="checkbox"]');
            allCheckboxes.forEach(cb => {
                if (cb !== checkbox) {
                    cb.checked = false;
                }
            });
        }
        const selectedClasses = Array.from(classesContainer.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);
        gid = document.getElementById('user_input').value.split(' ')[0];
        if (selectedClasses.join(' ') == 'OTHER') {
            document.getElementById('user_input').value = gid + ' 0';
        }
        if (selectedClasses.join(' ') == 'BARE SOIL') {
            document.getElementById('user_input').value = gid + ' 1';
        }
        if (selectedClasses.join(' ') == 'HERB') {
            document.getElementById('user_input').value = gid + ' 2';
        }
        if (selectedClasses.join(' ') == 'MULCHING') {
            document.getElementById('user_input').value = gid + ' 3';
        }
        if (selectedClasses.join(' ') == 'GROW') {
            document.getElementById('user_input').value = gid + ' 4';
        }
        if (selectedClasses.join(' ') == 'VEGETATION') {
            document.getElementById('user_input').value = gid + ' 5';
        }
        if (selectedClasses.join(' ') == 'GREENHOUSE') {
            document.getElementById('user_input').value = gid + ' 6';
        }
        if (selectedClasses.join(' ') == 'FLOREST') {
            document.getElementById('user_input').value = gid + ' 7';
        }
        if (selectedClasses.join(' ') == 'UNKNOWN') {
            document.getElementById('user_input').value = gid + ' 8';
        }
    });

    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(img_class));
    classesContainer.appendChild(label);
});
}

let nextButton = document.getElementById('next-button');
if (nextButton) {
    nextButton.addEventListener('click', function() {
        document.getElementById('user_input').value = 'next';
        document.getElementById('form').submit();
    });
}

let previousButton = document.getElementById('previous-button');
if (previousButton) {
    previousButton.addEventListener('click', function() {
        document.getElementById('user_input').value = 'previous';
        document.getElementById('form').submit();
    });
}

let endButton = document.getElementById('end-button');
if (endButton) {
    endButton.addEventListener('click', function() {
        document.getElementById('user_input').value = 'end';
        document.getElementById('form').submit();
    });
}


paths.forEach(element => {
    element.addEventListener('click', function(event) {
        event.preventDefault();
        var contextMenu = document.getElementById('context-menu');
        contextMenu.style.top = event.pageY + 'px';
        contextMenu.style.left = event.pageX + 'px';
        contextMenu.style.display = 'flex';
        contextMenu.style.flexDirection = 'column';
    });
});

let updateButton = document.getElementById('context-submit');
if (updateButton) {
    updateButton.addEventListener('click', function() {
        var contextMenu = document.getElementById('context-menu');
        contextMenu.style.display = 'none';
    });
}

let closeButton = document.getElementById('context-close');
if (closeButton) {
    closeButton.addEventListener('click', function(event) {
        event.preventDefault();
        var contextMenu = document.getElementById('context-menu');
        contextMenu.style.display = 'none';
    });
}