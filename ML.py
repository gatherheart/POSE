import numpy as np
import time
import pickle
import pandas as pd

CLASSIFICATION_RF = './ML_Model/randomforest_model.sav'

class Classifier:

    def Rf(data):
        data.dropna(inplace = True)
        print(data.shape)
        rf = pickle.load(open(CLASSIFICATION_RF, 'rb'))
        predicted = rf.predict(data)
        print(predicted)
        return predicted

