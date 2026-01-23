import plastic_sniffer.modules.classify_tree as ct
import os
from app.schemas import Classification, Dataset, Imagery, Project
from app import db


def evolution(BASE_PATH :str):
    model_path = BASE_PATH + '/models/'
    project_name = BASE_PATH.split('/')[-1]

    #get all models
    model_names = []
    for filename in os.listdir(model_path):
        if filename.endswith(".pkl"):
            model_names.append(filename)
    model_names.sort()

    #rename models
    for i in range(3,0,-1):
        if f'tree_old_{i}.pkl' in model_names:
            os.rename(model_path + f'tree_old_{i}.pkl', model_path + f'tree_old_{i+1}.pkl')
            print(f'Renamed tree_old_{i}.pkl to tree_old_{i+1}.pkl')
    # delete tree_old_4.pkl if it exists
    if 'tree_old_4.pkl' in model_names:
        os.remove(model_path + 'tree_old_4.pkl')
        print('Deleted tree_old_4.pkl')
    if 'tree_att.pkl' in model_names:
        os.rename(model_path + 'tree_att.pkl', model_path + 'tree_old_1.pkl')
        print('Renamed tree_att.pkl to tree_old_1.pkl')
    
    new_model, metrics = ct.train_tree_db(project_name)
    
    ct.save_tree(new_model, model_path + 'tree_att.pkl')
    
    print('The new model has the following metrics:')
    print(f'Accuracy: {metrics[0]}')
    print(f'F1: {metrics[1]}')
    print(f'Confusion Matrix: {metrics[2]}')

    ct.classify_tree_db(project_name, new_model)
    
    print('Evolution completed')


if __name__ == '__main__':
    DATA_NAME = 'Teste_1/'
    ORIGIN_PATH = '../../data/'

    evolution(ORIGIN_PATH + DATA_NAME)