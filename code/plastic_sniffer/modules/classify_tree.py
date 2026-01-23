from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, r2_score
import joblib
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from app.schemas import Project, Dataset, Imagery, Classification
from app import db


def train_tree_csv(path_csv : str, test_size : float =0.2  , random_state : int =42) -> tuple[DecisionTreeClassifier, list]:
    """
    This function trains a Decision Tree model to classify the data in the csv file.
    
    Parameters:
    path_csv (str): The path to the csv file.
    test_size (float): The proportion of the data to include in the test split.
    random_state (int): The seed used by the random number generator.

    Returns:
    model (DecisionTreeClassifier): The trained Decision Tree model.
    metrics (list): A list of metrics [accuracy, f1, r2, confusion_matrix].
    """
    # Load the data
    data = pd.read_csv(path_csv)
    data = data[data['validated'] == 2]
    X = data.drop(['class', 'GID', 'validated'], axis=1)
    y = data['class']

    # Remove any additional columns that were not present during training
    if 'Unnamed: 0' in X.columns:
        X = X.drop(['Unnamed: 0'], axis=1)

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # Train the model
    model = DecisionTreeClassifier(random_state=random_state)
    model.fit(X_train, y_train)

    # Test the model to obtain metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    confusion = confusion_matrix(y_test, y_pred)

    return model, [accuracy, f1, confusion]

def train_tree_db(project_name : str, test_size : float =0.2  , random_state : int =42) -> tuple[DecisionTreeClassifier, list]:
    """
    This function trains a Decision Tree model to classify the data in the csv file.
    
    Parameters:
    path_csv (str): The path to the csv file.
    test_size (float): The proportion of the data to include in the test split.
    random_state (int): The seed used by the random number generator.

    Returns:
    model (DecisionTreeClassifier): The trained Decision Tree model.
    metrics (list): A list of metrics [accuracy, f1, r2, confusion_matrix].
    """
    # Load the data

    data = []
    datasets = Project.query.filter_by(project_name=project_name).first().get_all_datasets()
    for dataset in datasets:
        imageries = Dataset.query.filter_by(id=dataset.id).first().get_all_imageries()
        for imagery in imageries:
            classifications = Classification.query.filter_by(gid_prefix=imagery.gid_prefix).all()
            for classification in classifications:
                if classification.state == 2:
                    data.append({
                        'GID': classification.gid,
                        'PMLI': classification.pmli,
                        'NDVI': classification.ndvi,
                        'BSI': classification.bsi,
                        'BSPI': classification.bspi,
                        'NDWI': classification.ndwi,
                        'NDMI': classification.ndmi,
                        'APGI': classification.apgi,
                        'CLOUD': classification.cloud,
                        'SHADOW': classification.shadow,
                        'class': classification.field_class
                    })
    
    if data:
        data = pd.DataFrame(data)
        if not data.empty and 'GID' in data.columns:
            X = data.drop(['class', 'GID'], axis=1)
        else:
            raise KeyError("'GID' column not found or the provided data is empty.")
    else:
        raise KeyError("No data found to train the model.")

    y = data['class']

    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    # Train the model
    model = DecisionTreeClassifier(random_state=random_state)
    model.fit(X_train, y_train)

    # Test the model to obtain metrics
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    confusion = confusion_matrix(y_test, y_pred)

    return model, [accuracy, f1, confusion]

def save_tree(model, path_model):
    """
    This function saves the Decision Tree model to a file.
    
    Parameters:
    model (DecisionTreeClassifier): The Decision Tree model.
    path_model (str): The path to save the model.
    """
    joblib.dump(model, path_model)

def load_tree(path_model):
    """
    This function loads a Decision Tree model from a file.
    
    Parameters:
    path_model (str): The path to the model file.

    Returns:
    model (DecisionTreeClassifier): The loaded Decision Tree model.
    """
    return joblib.load(path_model)

def calc_metrics(path_csv : str, path_model : str) -> list:
    """
    This function calculates the metrics of a Decision Tree model.
    
    Parameters:
    path_csv (str): The path to the csv file.
    path_model (str): The path to the model file.

    Returns:
    metrics (list): A list of metrics [accuracy, f1, r2, confusion_matrix].
    """
    # Load the model
    model = load_tree(path_model)

    # Load the data
    data = pd.read_csv(path_csv)
    data = data[data['validated'] == 2]
    X = data.drop(['class', 'GID', 'validated'], axis=1)
    y = data['class']

    # Test the model to obtain metrics
    y_pred = model.predict(X)
    accuracy = accuracy_score(y, y_pred)
    f1 = f1_score(y, y_pred, average='weighted')
    confusion = confusion_matrix(y, y_pred)

    return [accuracy, f1, confusion]

def classify_tree_csv(path_csv, model):
    """
    This function classifies the data in the csv file using the Decision Tree model.
    
    Parameters:
    path_csv (str): The path to the csv file.
    model (DecisionTreeClassifier): The Decision Tree model.

    """
    # Load the data
    data = pd.read_csv(path_csv)
    data_to_classify = data[data['validated'] == 0]
    X = data_to_classify.drop(['class', 'GID', 'validated'], axis=1)

    # Remove any additional columns that were not present during training
    if 'Unnamed: 0' in X.columns:
        X = X.drop(['Unnamed: 0'], axis=1)

    # Classify the data
    y_pred = model.predict(X)
    data.loc[data['validated'] == 0, 'class'] = y_pred

    # Save the data on the csv file
    data.to_csv(path_csv, index=False)

def classify_tree_db(project_name : str, model):
    """
    This function classifies the data in the csv file using the Decision Tree model.
    
    Parameters:
    path_csv (str): The path to the csv file.
    model (DecisionTreeClassifier): The Decision Tree model.

    """
    time_start = time.time()
    data = []
    datasets = Project.query.filter_by(project_name=project_name).first().get_all_datasets()
    for dataset in datasets:
        imageries = Dataset.query.filter_by(id=dataset.id).first().get_all_imageries()
        for imagery in imageries:
            classifications = Classification.query.filter_by(gid_prefix=imagery.gid_prefix).all()
            for classification in classifications:
                if classification.state == 0:
                    data.append({
                        'GID': classification.gid,
                        'PMLI': classification.pmli,
                        'NDVI': classification.ndvi,
                        'BSI': classification.bsi,
                        'BSPI': classification.bspi,
                        'NDWI': classification.ndwi,
                        'NDMI': classification.ndmi,
                        'APGI': classification.apgi,
                        'CLOUD': classification.cloud,
                        'SHADOW': classification.shadow
                    })

    if data:
        full_data = pd.DataFrame(data)
        if not full_data.empty and 'GID' in full_data.columns:
            X = full_data.drop(['GID'], axis=1)
        else:
            raise KeyError("'GID' column not found or the provided data is empty.")
    y_pred = model.predict(X)
    time_end = time.time()
    elapsed_time = time_end - time_start
    elapsed_time = elapsed_time/len(y_pred)
    for idx in range(len(X)):
        classification = Classification.query.filter_by(gid=full_data.iloc[idx]['GID']).first()
        classification.set_prev_class(int(y_pred[idx]))  # Ensure the value is converted to a standard Python int
        classification.set_time_classification(elapsed_time)
    for dataset in datasets:
        dataset.att_classifications_time()
    db.session.commit()
    return 0


    